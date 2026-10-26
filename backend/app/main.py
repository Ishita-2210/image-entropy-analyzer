"""Local-first API. Run one process: memory sources/jobs are intentionally not shared."""

import json
import logging
import threading
import time
from collections import OrderedDict
from contextlib import asynccontextmanager
from pathlib import Path

import cv2
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException as StarletteHTTPException

from backend.app import ANALYSIS_VERSION, VERSION
from backend.app.core.config import Settings, configure_logging
from backend.app.schemas.models import (
    AnalysisResult,
    AnalyzeRequest,
    BatchRequest,
    CompareRequest,
    CompressionRequest,
    ErrorResponse,
    ImageInfo,
    JobStatus,
    TransformRequest,
)
from backend.app.services.analysis import analyse
from backend.app.services.comparison import compare
from backend.app.services.experiments import compress, transform
from backend.app.services.images import ImageStore, capabilities, decode, png_bytes, synthetic
from backend.app.storage.history import History
from backend.app.workers.jobs import BusyError, Jobs

logger = logging.getLogger("iea")


class BodyLimitMiddleware:
    """Bound received bytes including chunked bodies, before multipart parsing."""

    def __init__(self, app, maximum):
        self.app, self.maximum = app, maximum

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        size = 0
        headers = dict(scope.get("headers", []))
        try:
            if int(headers.get(b"content-length", b"0")) > self.maximum:
                response = JSONResponse(
                    {
                        "error": {
                            "code": "upload_limit",
                            "message": "Request exceeds upload size limit.",
                        }
                    },
                    status_code=413,
                )
                return await response(scope, receive, send)
        except ValueError:
            response = JSONResponse(
                {"error": {"code": "invalid_length", "message": "Invalid content length."}},
                status_code=400,
            )
            return await response(scope, receive, send)

        async def bounded_receive():
            nonlocal size
            message = await receive()
            size += len(message.get("body", b""))
            if size > self.maximum:
                raise HTTPException(413, "Request exceeds upload size limit.")
            return message

        await self.app(scope, bounded_receive, send)


def create_app(settings: Settings | None = None):
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app):
        configure_logging()
        cv2.setNumThreads(1)
        app.state.images = ImageStore(settings)
        app.state.jobs = Jobs(settings)
        app.state.history = History(settings)
        app.state.cache = OrderedDict()
        app.state.cache_lock = threading.RLock()
        logger.info(
            json.dumps({"event": "startup", "version": VERSION, "history": settings.history})
        )
        yield
        await run_in_threadpool(app.state.jobs.close)
        app.state.images.items.clear()
        app.state.cache.clear()

    app = FastAPI(
        title="Image Entropy Analyzer",
        version=VERSION,
        lifespan=lifespan,
        docs_url=None,
        redoc_url=None,
        openapi_url="/api/v1/openapi.json",
        responses={
            400: {"model": ErrorResponse},
            404: {"model": ErrorResponse},
            413: {"model": ErrorResponse},
            422: {"model": ErrorResponse},
            429: {"model": ErrorResponse},
        },
    )
    app.state.settings = settings
    app.add_middleware(BodyLimitMiddleware, maximum=settings.max_upload_mb * 1024**2 + 65536)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.origins,
        allow_methods=["GET", "POST", "DELETE"],
        allow_headers=["Content-Type"],
    )

    @app.middleware("http")
    async def log_requests(request: Request, call_next):
        started = time.perf_counter()
        origin = request.headers.get("origin")
        if request.url.hostname not in settings.hosts:
            response = JSONResponse(
                {"error": {"code": "invalid_host", "message": "Host is not allowed by IEA_HOSTS."}},
                status_code=400,
            )
        elif (
            request.method not in ("GET", "HEAD", "OPTIONS")
            and origin
            and origin not in [*settings.origins, str(request.base_url).rstrip("/")]
        ):
            response = JSONResponse(
                {"error": {"code": "invalid_origin", "message": "Browser origin is not allowed."}},
                status_code=403,
            )
        else:
            response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-store"
        response.headers["Referrer-Policy"] = "no-referrer"
        logger.info(
            json.dumps(
                {
                    "event": "request",
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "ms": round((time.perf_counter() - started) * 1000, 2),
                }
            )
        )
        return response

    @app.exception_handler(StarletteHTTPException)
    async def http_error(request, exc):
        return JSONResponse(
            {"error": {"code": f"http_{exc.status_code}", "message": str(exc.detail)}},
            status_code=exc.status_code,
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error(request, exc):
        # Do not echo arbitrary request bodies or embedded exception objects.
        messages = [
            ".".join(str(v) for v in error["loc"]) + ": " + error["msg"] for error in exc.errors()
        ]
        return JSONResponse(
            {"error": {"code": "validation_error", "message": "; ".join(messages)}}, status_code=422
        )

    @app.exception_handler(KeyError)
    async def missing_error(request, exc):
        return JSONResponse(
            {"error": {"code": "not_found", "message": str(exc).strip("'")}}, status_code=404
        )

    @app.exception_handler(ValueError)
    async def input_error(request, exc):
        return JSONResponse(
            {"error": {"code": "invalid_input", "message": str(exc)}},
            status_code=429 if isinstance(exc, BusyError) else 400,
        )

    @app.exception_handler(Exception)
    async def internal_error(request, exc):
        logger.exception("Unhandled processing error")
        return JSONResponse(
            {
                "error": {
                    "code": "internal_error",
                    "message": "Processing failed; inspect server logs.",
                }
            },
            status_code=500,
        )

    def compute(work, wait_seconds=0):
        if not app.state.jobs.compute.acquire(timeout=wait_seconds):
            raise BusyError("All processing workers are busy. Submit a background job or retry.")
        try:
            return work()
        finally:
            app.state.jobs.compute.release()

    def calculate(stored, options, progress=lambda p, s: None):
        cache_options = options.model_copy(update={"save_history": False})
        key = (
            ANALYSIS_VERSION,
            stored.info.sha256,
            stored.info.frame,
            cache_options.model_dump_json(),
        )
        progress(0, "Checking analysis cache")
        with app.state.cache_lock:
            result = app.state.cache.get(key)
            if result:
                app.state.cache.move_to_end(key)
        if result is None:
            result = analyse(stored, settings, options, progress)
            with app.state.cache_lock:
                app.state.cache[key] = result
                while len(app.state.cache) > 8:
                    app.state.cache.popitem(last=False)
        # Copy cached data so image identity and history requests cannot contaminate other callers.
        result = {
            **result,
            "image": stored.info.model_dump(),
            "configuration": options.model_dump(),
        }
        progress(0.99, "Finalizing analysis")
        if options.save_history:
            result = app.state.history.add(result)
        return result

    prefix = "/api/v1"

    @app.get(prefix + "/health")
    def health():
        return {
            "status": "ok",
            "version": VERSION,
            "analysis_version": ANALYSIS_VERSION,
            "history_enabled": settings.history,
            "limits": settings.model_dump(exclude={"history_path", "origins"}),
            "capabilities": capabilities(),
            "privacy": "Images in server memory; lazy expiry after one hour of inactivity, 48 entries, LRU byte bound. History opt-in; results only, no source pixels or EXIF.",
        }

    @app.post(prefix + "/images", response_model=ImageInfo, status_code=201)
    async def upload(file: UploadFile, frame: int = Query(default=0, ge=0, le=99)):
        try:
            data = await file.read(settings.max_upload_mb * 1024**2 + 1)
            if len(data) > settings.max_upload_mb * 1024**2:
                raise HTTPException(413, "Image exceeds upload size limit.")
            return await run_in_threadpool(
                compute, lambda: app.state.images.add(data, file.filename or "image", frame)
            )
        finally:
            await file.close()

    @app.post(prefix + "/demo", response_model=ImageInfo, status_code=201)
    def demo(
        kind: str = Query(
            default="landscape", pattern="^(landscape|noise|constant|gradient|checkerboard)$"
        ),
        seed: int = Query(default=42, ge=0, le=2**32 - 1),
    ):
        return compute(
            lambda: app.state.images.add(synthetic(kind, seed=seed), f"{kind}-seed-{seed}.png")
        )

    @app.get(prefix + "/images/{image_id}", response_model=ImageInfo)
    def metadata(image_id: str):
        return app.state.images.get(image_id).info

    @app.post(prefix + "/images/{image_id}/frame", response_model=ImageInfo, status_code=201)
    def select_frame(image_id: str, index: int = Query(ge=0, le=99)):
        source = app.state.images.get(image_id)
        return compute(lambda: app.state.images.add(source.data, source.info.filename, index))

    @app.get(prefix + "/images/{image_id}/preview")
    def preview(image_id: str, size: int = Query(default=1024, ge=32, le=4096)):
        stored = app.state.images.get(image_id)
        return compute(
            lambda: Response(
                png_bytes(decode(stored.data, settings, stored.info.frame).image, size),
                media_type="image/png",
            ),
            wait_seconds=5,
        )

    @app.get(prefix + "/images/{image_id}/download")
    def download(image_id: str):
        stored = app.state.images.get(image_id)
        return Response(
            stored.data,
            media_type="application/octet-stream",
            headers={
                "Content-Disposition": 'attachment; filename="image.'
                + {"PNG": "png", "JPEG": "jpg", "WEBP": "webp"}.get(stored.info.format, "bin")
                + '"'
            },
        )

    @app.get(prefix + "/images/{image_id}/pixel")
    def pixel(image_id: str, x: int = Query(ge=0), y: int = Query(ge=0)):
        stored = app.state.images.get(image_id)

        def inspect():
            source = decode(stored.data, settings, stored.info.frame)
            if x >= source.image.width or y >= source.image.height:
                raise ValueError("Pixel coordinates exceed image boundaries.")
            native = np.asarray(source.native[y, x]).tolist()
            rgb = source.image.convert("RGB").getpixel((x, y))
            return {
                "x": x,
                "y": y,
                "native": native,
                "bits": source.bits,
                "rgb8_preview": list(rgb),
                "hex": "#" + "".join(f"{v:02x}" for v in rgb),
            }

        return compute(inspect)

    @app.delete(prefix + "/images/{image_id}")
    def delete_image(image_id: str):
        app.state.images.remove(image_id)
        return {"deleted": image_id}

    @app.post(prefix + "/analysis", response_model=AnalysisResult)
    def analysis(request: AnalyzeRequest):
        stored = app.state.images.get(request.image_id)
        return compute(lambda: calculate(stored, request.options))

    @app.post(prefix + "/analysis/colour")
    def colour_analysis(request: AnalyzeRequest):
        result = analysis(request)
        return {
            "rgb": result["rgb"],
            "colour": result["colour"],
            "measurement": result["measurement"],
        }

    @app.post(prefix + "/analysis/spatial")
    def spatial_analysis(request: AnalyzeRequest):
        result = analysis(request)
        return {
            key: result[key]
            for key in ["spatial", "local", "multiscale", "frequency", "measurement"]
        }

    @app.post(prefix + "/jobs/analysis", response_model=JobStatus, status_code=202)
    def analysis_job(request: AnalyzeRequest):
        stored = app.state.images.get(request.image_id)
        if request.options.save_history and not settings.history:
            raise ValueError("History is disabled. Set IEA_HISTORY=true and restart.")
        return app.state.jobs.submit(lambda p: calculate(stored, request.options, p))

    @app.post(prefix + "/jobs/batch", response_model=JobStatus, status_code=202)
    def batch(request: BatchRequest):
        # Validate and pin references now; eviction cannot invalidate an accepted job.
        items = [app.state.images.get(i) for i in request.image_ids]

        def work(progress):
            results = []
            for index, item in enumerate(items):
                results.append(
                    calculate(
                        item,
                        request.options,
                        lambda value, stage, i=index: progress(
                            (i + value) / len(items), f"{i + 1}/{len(items)} · {stage}"
                        ),
                    )
                )
            return results

        return app.state.jobs.submit(work)

    @app.get(prefix + "/jobs/{job_id}", response_model=JobStatus)
    def job_status(job_id: str):
        return app.state.jobs.get(job_id)

    @app.get(prefix + "/jobs/{job_id}/results", response_model=JobStatus)
    def job_results(job_id: str):
        return app.state.jobs.get(job_id, result=True)

    @app.delete(prefix + "/jobs/{job_id}", response_model=JobStatus)
    def cancel_job(job_id: str):
        return app.state.jobs.cancel(job_id)

    @app.get(prefix + "/jobs/{job_id}/export")
    def export(job_id: str, format: str = Query(default="json", pattern="^(json|csv)$")):
        job = app.state.jobs.get(job_id, result=True)
        if job["status"] != "completed":
            raise HTTPException(409, "Job has no completed result.")
        result = job["result"]
        if format == "json":
            data, mime = json.dumps(result, allow_nan=False), "application/json"
        else:
            rows = result if isinstance(result, list) else [result]
            if rows and "entropy" in rows[0]:
                rows = [
                    {
                        "filename": r["image"]["filename"],
                        "sha256": r["image"]["sha256"],
                        "mode": r["configuration"]["mode"],
                        **r["entropy"],
                        "elapsed_ms": r["elapsed_ms"],
                    }
                    for r in rows
                ]
            data, mime = pd.json_normalize(rows).to_csv(index=False), "text/csv"
        return Response(
            data,
            media_type=mime,
            headers={"Content-Disposition": f'attachment; filename="analysis.{format}"'},
        )

    @app.post(prefix + "/compare")
    def compare_images(request: CompareRequest):
        items = [app.state.images.get(i) for i in request.image_ids]
        return compute(lambda: compare(items, settings, request))

    @app.post(prefix + "/jobs/compare", response_model=JobStatus, status_code=202)
    def compare_job(request: CompareRequest):
        items = [app.state.images.get(i) for i in request.image_ids]
        return app.state.jobs.submit(lambda p: compare(items, settings, request, p))

    def experiment_result(stored, result, encoded, difference, name):
        info = app.state.images.add(encoded, name)
        result["image"] = info.model_dump()
        result["original_image_id"] = stored.info.id
        if difference:
            result["difference_image"] = app.state.images.add(
                png_bytes(difference), "difference.png"
            ).model_dump()
        else:
            result["difference_image"] = None
        return result

    @app.post(prefix + "/compression")
    def compression(request: CompressionRequest):
        stored = app.state.images.get(request.image_id)

        def work():
            result, encoded, diff = compress(stored, settings, request)
            return experiment_result(
                stored, result, encoded, diff, "encoded." + request.codec.lower()
            )

        return compute(work)

    @app.post(prefix + "/transforms")
    def transformations(request: TransformRequest):
        stored = app.state.images.get(request.image_id)

        def work():
            result, encoded, diff = transform(stored, settings, request.steps)
            return experiment_result(stored, result, encoded, diff, "transformed.png")

        return compute(work)

    @app.get(prefix + "/history")
    def history():
        return {"enabled": settings.history, "records": app.state.history.list()}

    @app.get(prefix + "/history/{record_id}")
    def history_result(record_id: str):
        result = app.state.history.get(record_id)
        try:
            stored = app.state.images.get(result["image"]["id"])
            available = stored.info.sha256 == result["image"]["sha256"]
        except KeyError:
            available = False
        return {"result": result, "source_available": available}

    @app.delete(prefix + "/history/{record_id}")
    def delete_record(record_id: str):
        app.state.history.delete(record_id)
        return {"deleted": record_id}

    @app.delete(prefix + "/history")
    def clear_history():
        app.state.history.delete()
        return {"cleared": True}

    # Self-host the API reference: no CDN, fonts, validator service or external requests.
    frontend = Path(__file__).resolve().parents[2] / "frontend"
    dist = frontend / "dist"
    docs_assets = dist / "docs-assets"
    if not docs_assets.is_dir():
        docs_assets = frontend / "node_modules" / "swagger-ui-dist"
    if docs_assets.is_dir():
        app.mount(prefix + "/docs-assets", StaticFiles(directory=docs_assets), name="docs-assets")

    @app.get("/docs", include_in_schema=False)
    def docs_redirect():
        return RedirectResponse(prefix + "/docs")

    @app.get(prefix + "/docs", include_in_schema=False)
    def docs():
        if not docs_assets.is_dir():
            return HTMLResponse(
                '<h1>Image Entropy Analyzer API</h1><p>Install the frontend dependencies (npm ci --prefix frontend) for the offline interactive reference.</p><a href="/api/v1/openapi.json">Download OpenAPI schema</a>'
            )
        return get_swagger_ui_html(
            openapi_url=prefix + "/openapi.json",
            title="Image Entropy Analyzer API",
            swagger_js_url=prefix + "/docs-assets/swagger-ui-bundle.js",
            swagger_css_url=prefix + "/docs-assets/swagger-ui.css",
            swagger_favicon_url=prefix + "/docs-assets/favicon-32x32.png",
            swagger_ui_parameters={"validatorUrl": None, "persistAuthorization": False},
        )

    # Production build served by the same origin; API remains usable without it.
    if dist.is_dir():
        app.mount("/", StaticFiles(directory=dist, html=True), name="frontend")
    return app


app = create_app()
