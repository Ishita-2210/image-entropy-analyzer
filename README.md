# Image Entropy Analyzer

A local **Image Intelligence Workbench** with a React/TypeScript frontend, FastAPI API, and one shared Python numerical engine for the browser and CLI. No paid APIs, keys, model downloads, or external processing services. Works offline after dependencies are installed.

## Run locally

Use Python **3.12+** (verified with 3.13.3) and Node **24 LTS**. From the repository root:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-lock.txt
python -m pip install -e . --no-deps
npm ci --prefix frontend
python scripts/dev.py
```

On macOS/Linux, activate with `source .venv/bin/activate` instead. Open **http://127.0.0.1:5173**. Click **Explore a synthetic landscape**, or import/drop images. API reference: **http://127.0.0.1:8000/docs**. Ctrl+C stops the combined launcher.

Separate terminals, with the virtual environment activated:

```sh
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
npm run dev --prefix frontend
```

`requirements-lock.txt` pins the tested Python environment, including development tools. `requirements.txt` and `requirements-dev.txt` provide compatible dependency ranges for updates. `frontend/package-lock.json` pins JavaScript dependencies. No runtime assets are fetched from a CDN.

## What works

- **Information theory:** Shannon, Hartley, configurable Renyi (including orders 0 and 1), collision and min-entropy; theoretical bounds, normalized entropy, effective states and observed support. Equal-width quantization curves at 2–256 levels.
- **Colour information:** sparse exact observed RGB tuple entropy and native channel marginals, explicitly quantized pairwise mutual/conditional information and total correlation. No dense 256³ tensor.
- **Spatial analysis:** compiled sliding-window local entropy, non-overlapping blocks, configurable windows/strides, clipped edge handling, interactive coordinate heatmaps and source-region analysis. Multiscale local-entropy profiles; horizontal, vertical, diagonal and lagged neighbour information; symmetric GLCM metrics.
- **Frequency:** mean-subtracted FFT, log power map, radial energy, spectral entropy and frequency bands. The DC component is explicitly zeroed; constant inputs have undefined spectral entropy, returned as null.
- **Colour science:** RGB/HSV/CIELAB histograms, approximate deterministic Lab k-means palette, alpha statistics, channel correlations, linear relative luminance and colourfulness. Distribution accumulation is chunked; palette sampling is labelled.
- **Diagnostics:** brightness, range, clipping, contrast, Laplacian variance, Canny edge density, Sobel gradients and a Haar-detail MAD noise estimate. These are defined heuristics, not a fabricated quality score.
- **Compression laboratory:** actual PNG, JPEG and installed WebP encode/decode experiments; encoded downloads, actual byte ratios, encode/decode timings, decoded equality, MAE, MSE, PSNR, SSIM and mean Delta E76; reconstruction and normalized difference previews. A notebook compares runs.
- **Transformation pipelines:** grayscale, resize/resampling, crop, blur, sharpen, seeded noise, median denoise, brightness/contrast/saturation/gamma, equalization, quantization, seeded pixel shuffle, rotation/flips and labelled HSV/Lab component views. Adjustable/removable steps, undo/reset, original preservation and measured before/after statistics.
- **Collection workspace:** multiple uploads, metadata search/filter/sort, background batch analysis, measured CSV/JSON exports, distribution comparisons across different dimensions, ranked pairs and a distance matrix. SHA-256 byte duplicates, pHash/dHash distances and candidate grouping stay separate from entropy.
- **Viewer:** zoom, pan, fit, source coordinates, worker-based preview sampling, native pixel lookup, pointer region selection and linked original/reconstruction zoom. Previews are capped at 1024 px and explicitly labelled; a full-resolution original remains downloadable. This is not a tiled gigapixel viewer.
- **History:** optional SQLite results, configuration persistence, reopen/export, individual deletion and clear-all. Saved plots work without source images; pixel inspection requires an available source.

The original `app.py`, `entropy.py`, `image_utils.py` and academic assets are preserved. To run the legacy interface, install `requirements-legacy.txt`, then `python -m streamlit run app.py`. The new application uses `backend/app/core/` and `backend/app/services/`; legacy formulas have not been repurposed for the new engine.

## Measurement conventions

Shannon entropy is `-sum(p * log2(p))` over positive bins. Hartley is `log2(observed support)`. Renyi uses log-sum-exp and the exact definitions at alpha=0, alpha=1 and infinity (infinity is available in the Python engine; HTTP controls accept finite 0–100). Near alpha=1, expm1/log1p avoid cancellation. The maximum is `log2(K)` for the specified alphabet, independent of observed support. Effective states are `2^H`.

Grayscale integer measurements use **bits per intensity symbol** (one intensity symbol per grayscale pixel). Channel marginals use **bits per channel value**; joint colour entropy uses **bits per RGB tuple**. Mutual information is in bits, normalized entropy is dimensionless. Their axes are kept separate. Entropy deficit is not a compression estimate. Pixel entropy does not measure spatial order or perceptual quality.

Quantization is `floor(value * levels / 2^bits)`, clipped to the last bin. Pairwise and spatial measurements use the requested number of levels. Changing bins changes the measurement. Exact mode never silently samples global measurements. Preview mode reports its dimensions: native symbols use nearest-grid subsampling; spatial/colour/diagnostics use a Lanczos-resized standardized image. Only the perceptual palette always uses a deterministic sample of at most 12,000 pixels (seed 42).

Native integer grayscale is retained at 1, 8, 16 or supported unsigned 32-bit depth. PNG/TIFF RGB16 uses OpenCV recovery, with native tuple/channel entropy and a separately labelled 8-bit colour/spatial preview. Supported source frames are selectable in the image toolbar and through the API (first 100 GIF/TIFF frames); sequence-wide aggregation is not implemented. Floating-point/signed inputs and unsupported native colour-frame combinations fail explicitly. Encoders depend on the installed Pillow build; capabilities are reported at runtime, including optional AVIF/HEIF availability. No HEIF plugin is required.

Colour assumes **sRGB, D65, 2-degree observer**. Embedded ICC profiles are reported but not applied; CMYK conversion is uncalibrated. CIELAB and relative luminance use the sRGB transfer function. Pillow grayscale is an encoded-luma proxy, not linear light. Transparent RGB is analysed without compositing. Experiments use explicitly standardized **8-bit** data; JPEG drops alpha, and several transformations may discard alpha. Lossless encoding refers to this evaluation representation, not necessarily the original high-depth source.

KL is directed and can be infinite: JSON `null` for KL is explicitly labelled `+infinity`. JS divergence uses base-2 logs (bits), JS distance is its square root, Hellinger/TV are dimensionless, and Wasserstein uses intensity-bin steps. RGB tuples have no scalar ordering, so their Wasserstein distance is rejected. PSNR `null` with MSE=0 means infinity; unaligned pixel metrics and undefined constant-channel correlations are null. SSIM uses RGB8, data range 255 and an odd window up to 7. For definitions of the library primitives, see [scikit-image rank entropy](https://scikit-image.org/docs/stable/api/skimage.filters.rank.html) and [GLCM metrics](https://scikit-image.org/docs/stable/api/skimage.feature.html).

## HTTP API

All computational endpoints are versioned under `/api/v1`. `/docs` contains request schemas and an interactive client. Uploads are decoder-validated, not trusted by extension.

```sh
curl -F "file=@example.png" http://127.0.0.1:8000/api/v1/images
# Copy the returned id into image_id below.
curl -H "Content-Type: application/json" -d '{"image_id":"IMAGE_ID","options":{"mode":"exact","alpha":2,"levels":16}}' http://127.0.0.1:8000/api/v1/analysis
curl -H "Content-Type: application/json" -d '{"image_id":"IMAGE_ID","codec":"JPEG","quality":70}' http://127.0.0.1:8000/api/v1/compression
```

On Windows use `curl.exe`; PowerShell users can use `Invoke-RestMethod -ContentType application/json -Method Post -Body ...`. Generate reproducible inputs with `POST /demo?kind=gradient&seed=42` (also landscape, constant, checkerboard, noise).

| Endpoint | Purpose |
| --- | --- |
| `GET /health` | Version, resource limits and installed codecs |
| `POST /images?frame=0` | Multipart `file` upload; returns image metadata and ID |
| `GET /images/{id}` | Safe metadata, without EXIF/GPS |
| `POST /images/{id}/frame?index=0` | Select a source frame (first 100) |
| `GET /images/{id}/preview?size=1024` | Standardized PNG preview |
| `GET /images/{id}/pixel?x=0&y=0` | Native sample and 8-bit preview colour |
| `GET /images/{id}/download` | Original/experiment encoded bytes |
| `DELETE /images/{id}` | Remove source from memory |
| `POST /analysis` | Full analysis; `{image_id, options}` |
| `POST /analysis/colour`, `/analysis/spatial` | Focused response subsets |
| `POST /jobs/analysis` | Background single-image analysis |
| `POST /jobs/batch` | `{image_ids, options}`; up to 24 sources |
| `POST /compare`, `/jobs/compare` | `{image_ids, distribution, metric, levels, near_threshold}` |
| `GET /jobs/{id}`, `/jobs/{id}/results` | Progress and completed results |
| `DELETE /jobs/{id}` | Request cooperative cancellation |
| `GET /jobs/{id}/export?format=csv` | Actual measured results; also JSON |
| `POST /transforms` | `{image_id, steps:[{kind:"shuffle",seed:42}]}` |
| `POST /compression` | Actual encoding experiment and output image IDs |
| `GET /history`, `/history/{id}` | Opt-in result browsing and source availability |
| `DELETE /history/{id}`, `/history` | Delete individual/all records |

Errors use `{ "error": { "code": "...", "message": "..." } }`. Invalid input is 400, unknown/expired IDs 404, request/schema violations 422, oversized requests 413, unavailable exports 409 and resource saturation 429. Jobs transition queued → running → completed/failed/cancelled. Cancellation and deadlines are checked between computational stages; they do **not** interrupt an in-flight native decoder/FFT call. Synchronous experiments have pixel bounds but no hard process-level timeout.

## CLI

With the same virtual environment:

```sh
python -m backend.app.cli example.png --alpha 2 --levels 16 --window 9
python -m backend.app.cli first.png second.tif --mode preview --output results.json
image-entropy example.png --frame 0 --output result.json
```

Stdout/output files contain strict JSON from the same engine as the API; errors go to stderr with nonzero exit status. No database history is written by the CLI.

## Limits, privacy and retention

Defaults: **24 MiB/file**, **16 million decoded pixels**, **4 million working pixels**, **2 CPU workers**, **10 queued/running jobs**, **120 seconds cooperative job deadline**. Exact analyses above the working budget are rejected with a preview/region suggestion. Large compression sources must be resized first. Local rank work also has a window-operation budget; block output is limited to 25,000 blocks. Chart maps are explicitly display-decimated to at most 160 cells per side. These bounds are protection for an ordinary CPU laptop, not a guarantee against every malicious codec bug.

Sources and experiment images are held only in **server memory**, with an LRU byte budget of **192 MiB**, at most 48 entries and lazy expiry after one hour of inactivity. Restarting loses them. Queued jobs pin accepted source references until work finishes. Cached analyses retain up to 8 results; completed jobs retain a bounded number of results. Removing a source prevents further lookups but an accepted job can finish using its pinned reference. Clear browser state/restart the server to release the session; choose file removal to evict specific sources. Upload spooling is managed and closed by the request parser. No archive upload or unsafe deserialization is implemented.

History is disabled by default. In PowerShell, before starting the backend:

```powershell
$env:IEA_HISTORY = 'true'
python scripts/dev.py
```

On macOS/Linux: `IEA_HISTORY=true python scripts/dev.py`. Then select **Save subsequent analyses to local history** in Settings. The default database is `.runtime/history.sqlite3`; it stores sanitized filename, hash, timestamp, configuration and **derived results including plots/maps**. This can reveal image characteristics even without source pixels. No source image, EXIF or GPS is stored. Delete records in History, or stop the application and remove the database to remove all retained records. A hash cannot restore an image. The browser stores analysis options only; refreshing loses its in-memory collection.

Environment variables are validated on startup (see `.env.example`): `IEA_MAX_UPLOAD_MB`, `IEA_MAX_PIXELS`, `IEA_MAX_ANALYSIS_PIXELS`, `IEA_STORE_MB`, `IEA_WORKERS`, `IEA_MAX_JOBS`, `IEA_JOB_SECONDS`, `IEA_HISTORY`, `IEA_HISTORY_PATH`, `IEA_ORIGINS` (comma-separated allowed browser origins), `IEA_HOSTS` (comma-separated allowed Host values). The `.env` file is not loaded automatically.

The default launcher binds to loopback. **Browser uploads go to the running server**; remote hosting sends them off the device. CORS allows only local development origins by default. State-changing browser requests reject unknown Origin values, and Host values are checked to resist DNS rebinding. Configure IEA_HOSTS for any deliberate remote hostname. EPS/PostScript and formats requiring external interpreters are rejected before decoding. This is a trusted local workspace, with no multi-user authentication or tenancy boundary. Do not expose it publicly without authentication, TLS, request limits and process/container isolation. Run **one API process** because source IDs, cache and job state are memory-local. Internal numerical threads are limited for OpenCV; job concurrency is bounded. No application telemetry is emitted to an external endpoint. Server request logs contain paths/status/timings, not image bodies.

## Verify

```sh
python -m pytest
python -m ruff check backend scripts
python -m ruff format --check backend scripts
npm run lint --prefix frontend
npm run format:check --prefix frontend
npm run build --prefix frontend
npm run test --prefix frontend
# One-time browser dependency install; Linux may require --with-deps.
npx --prefix frontend playwright install chromium
npm run test:e2e --prefix frontend
python scripts/benchmark.py
```

Playwright starts an isolated backend with a temporary history database and the Vite server when ports are unused. Stop other servers on ports 8000/5173 before running the browser suite; local reuse is supported only if that backend has test history enabled. CI always creates its own servers. Tests use generated images and run without API keys or proprietary datasets. The benchmark prints actual single-run timings, conditions and equality checks; no performance report is generated. Python-tracked memory is not total process RSS. Baseline and optimized timings may favour different methods at different strides; no universal speedup is claimed.

## Production

Build and serve the frontend from FastAPI on one origin:

```sh
npm run build --prefix frontend
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --workers 1
```

Open **http://127.0.0.1:8000**. Build before starting the backend so the static mount is registered. Client navigation preserves state in the current browser session; no server-rendered routes are required.

A non-root multistage `Dockerfile` and `compose.yaml` are provided:

```sh
docker compose up --build
```

Compose binds port 8000 to loopback and gives the process a 2 GiB container memory limit. History remains disabled unless enabled in Compose; its volume keeps the database when enabled. Docker was unavailable in the implementation environment, so the container recipe has not been executed there. There is no cloud deployment requirement.

## Source layout

`backend/app/core/` contains the formulas; `services/` coordinates analysis, validated image storage, comparison and experiments. `schemas/` contains Pydantic request/result contracts, `workers/` bounded jobs, and `storage/` SQLite history. `main.py` wires HTTP endpoints and lifecycle. `frontend/src/` separates components, feature views, hooks, types, chart/API helpers and the pixel worker. `scripts/` contains the combined launcher, browser-test server and reproducible benchmark. CI checks backend tests/lint/format and frontend build/typecheck/lint/format/tests/browser workflows.

The existing `documentation/` presentation, experiment source and measured snapshot are retained as historical project assets. They describe the original Streamlit version, not the new workbench.
