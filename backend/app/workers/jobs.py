"""Bounded CPU dispatch, cooperative cancellation and stage-boundary deadlines."""

import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field


class Cancelled(Exception):
    pass


class BusyError(ValueError):
    pass


@dataclass
class Job:
    id: str
    status: str = "queued"
    progress: float = 0
    stage: str = "Waiting for worker"
    result: dict | list | None = None
    error: str | None = None
    cancel: threading.Event = field(default_factory=threading.Event)
    touched: float = field(default_factory=time.monotonic)

    def public(self, result=False):
        return {
            "id": self.id,
            "status": self.status,
            "progress": self.progress,
            "stage": self.stage,
            "error": self.error,
            "result": self.result if result else None,
        }


class Jobs:
    def __init__(self, settings):
        self.settings = settings
        self.executor = ThreadPoolExecutor(max_workers=settings.workers, thread_name_prefix="iea")
        self.capacity = threading.BoundedSemaphore(settings.max_jobs)
        self.compute = threading.BoundedSemaphore(settings.workers)
        self.jobs = {}
        self.lock = threading.RLock()

    def submit(self, work):
        if not self.capacity.acquire(blocking=False):
            raise BusyError("Job queue is full; retry after current jobs finish.")
        job = Job(uuid.uuid4().hex)
        with self.lock:
            # Bound retained results as well as queued work.
            done = [
                j for j in self.jobs.values() if j.status in ("completed", "failed", "cancelled")
            ]
            for old in done[:-15]:
                self.jobs.pop(old.id, None)
            self.jobs[job.id] = job

        def run():
            start = time.monotonic()

            def progress(value, stage):
                with self.lock:
                    if job.cancel.is_set():
                        raise Cancelled()
                    if time.monotonic() - start > self.settings.job_seconds:
                        raise TimeoutError("Processing deadline exceeded at a stage boundary.")
                    job.progress, job.stage = value, stage

            try:
                progress(0, "Starting")
                job.status = "running"
                with self.compute:
                    progress(0, "Processing")
                    result = work(progress)
                progress(1, "Complete")
                with self.lock:
                    job.result, job.status = result, "completed"
            except Cancelled:
                job.status, job.stage = "cancelled", "Cancelled; partial results discarded"
            except (ValueError, KeyError, TimeoutError) as exc:
                job.status, job.error = "failed", str(exc).strip("'")
            except Exception:
                logging.getLogger("iea").exception("Background processing failed")
                job.status, job.error = "failed", "Processing failed; inspect server logs."
            finally:
                job.touched = time.monotonic()
                self.capacity.release()

        self.executor.submit(run)
        return job.public()

    def get(self, job_id, result=False):
        with self.lock:
            job = self.jobs.get(job_id)
            if not job or time.monotonic() - job.touched > 3600:
                raise KeyError("Job expired or unavailable.")
            return job.public(result)

    def cancel(self, job_id):
        with self.lock:
            job = self.jobs.get(job_id)
            if not job:
                raise KeyError("Job unavailable.")
            if job.status in ("queued", "running"):
                job.cancel.set()
                job.stage = "Cancellation requested; waiting for stage boundary"
            return job.public()

    def close(self):
        for job in self.jobs.values():
            job.cancel.set()
        self.executor.shutdown(wait=True, cancel_futures=False)
