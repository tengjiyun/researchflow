import asyncio
from contextlib import contextmanager, suppress
import logging
import os
from pathlib import Path
import subprocess
import sys
import threading

from app.core.config import BACKEND_DIRECTORY
from app.services.documents import DocumentStore
from app.services.pdf_download import DocumentError, download_pdf
from app.services.pdf_parser import parse_pdf

logger = logging.getLogger(__name__)
JOB_SECONDS = 90


@contextmanager
def worker_lock(path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a+b") as handle:
        if handle.tell() == 0:
            handle.write(b"0")
            handle.flush()
        handle.seek(0)
        try:
            if os.name == "nt":
                import msvcrt
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except OSError as exc:
            raise RuntimeError("Another PDF worker is active. Run one backend process per database.") from exc
        try:
            yield
        finally:
            handle.seek(0)
            if os.name == "nt":
                msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


class DocumentRunner:
    def __init__(self, store: DocumentStore):
        self.store = store
        self.process = None

    async def run(self):
        while True:
            document_id = None
            try:
                document_id = await asyncio.to_thread(self.store.claim_next)
                if document_id is None:
                    await asyncio.sleep(0.5)
                    continue
                await self.execute(document_id)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Document processing failed.")
                if document_id is not None:
                    with suppress(Exception):
                        self.store.fail(document_id, "processing_failed", "Document processing failed. Retry later.")
                await asyncio.sleep(1)

    async def execute(self, document_id: int):
        try:
            self.process = await asyncio.create_subprocess_exec(
                sys.executable, "-m", "app.services.document_worker",
                str(self.store.database_path), str(self.store.cache_path), str(document_id),
                cwd=str(BACKEND_DIRECTORY),
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
            try:
                await asyncio.wait_for(self.process.wait(), timeout=JOB_SECONDS)
            except TimeoutError:
                self.process.kill()
                await self.process.wait()
                self.store.fail(document_id, "processing_timeout", "Document processing exceeded 90 seconds.")
            if self.store.get(document_id).parsing_status not in ("completed", "failed"):
                self.store.fail(document_id, "processing_failed", "Document processing stopped before it finished.")
        finally:
            if self.process is not None and self.process.returncode is None:
                self.process.kill()
                await self.process.wait()
                self.store.fail(document_id, "processing_interrupted", "Document processing stopped. Retry the document.")
            self.process = None


def process_document(store: DocumentStore, document_id: int):
    try:
        document = store.get(document_id)
        path = store.pdf_path(document_id)
        size, digest = download_pdf(document.source_url, path)
        store.downloaded(document_id, size, digest)
        store.complete(document_id, parse_pdf(path))
    except DocumentError as exc:
        store.fail(document_id, exc.code, exc.message)
    except Exception:
        store.fail(document_id, "processing_failed", "Document processing failed. Retry later.")


if __name__ == "__main__":
    database, cache, identifier = sys.argv[1:]
    watchdog = threading.Timer(JOB_SECONDS, lambda: os._exit(1))
    watchdog.daemon = True
    watchdog.start()
    try:
        with worker_lock(Path(database).with_suffix(".pdf-job.lock")):
            process_document(DocumentStore(Path(database), Path(cache)), int(identifier))
    finally:
        watchdog.cancel()
