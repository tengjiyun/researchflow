import hashlib
import http.client
import ipaddress
from pathlib import Path
import socket
import ssl
import time
from urllib.parse import urljoin, urlsplit

MAX_PDF_BYTES = 25 * 1024 * 1024
DOWNLOAD_SECONDS = 45


class DocumentError(Exception):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def validate_source_url(url: str):
    try:
        parsed = urlsplit(url)
        if (
            parsed.scheme not in ("http", "https") or not parsed.hostname
            or parsed.username is not None or parsed.password is not None
            or parsed.port not in (None, 80, 443) or parsed.fragment
            or "\\" in url or any(ord(c) <= 32 or ord(c) == 127 for c in url)
        ):
            raise ValueError
        host = parsed.hostname.encode("idna").decode("ascii")
        if host.lower().rstrip(".") == "localhost" or host.lower().endswith(".localhost"):
            raise ValueError
        try:
            address = ipaddress.ip_address(host)
        except ValueError:
            address = None
        if address is not None and not address.is_global:
            raise ValueError
    except (ValueError, UnicodeError) as exc:
        raise DocumentError("unsupported_source_url", "The PDF source URL is not supported.") from exc
    return parsed


def public_address(host: str, port: int) -> str:
    addresses = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise DocumentError("unsupported_source_url", "The PDF source must use a public address.")
    return addresses[0][4][0]


class PinnedConnection(http.client.HTTPConnection):
    def __init__(self, host: str, port: int, address: str, secure: bool, timeout: float):
        super().__init__(host, port, timeout=timeout)
        self.address = address
        self.secure = secure

    def connect(self):
        self.sock = socket.create_connection((self.address, self.port), self.timeout)
        if self.secure:
            try:
                self.sock = ssl.create_default_context().wrap_socket(self.sock, server_hostname=self.host)
            except Exception:
                self.sock.close()
                raise


def download_pdf(url: str, target: Path) -> tuple[int, str]:
    partial = target.with_suffix(".part")
    deadline = time.monotonic() + DOWNLOAD_SECONDS
    target.parent.mkdir(parents=True, exist_ok=True)
    try:
        for redirect in range(6):
            parsed = validate_source_url(url)
            host = parsed.hostname.encode("idna").decode("ascii")
            port = parsed.port or (443 if parsed.scheme == "https" else 80)
            address = public_address(host, port)
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError
            connection = PinnedConnection(host, port, address, parsed.scheme == "https", min(15, remaining))
            try:
                path = parsed.path or "/"
                if parsed.query:
                    path += "?" + parsed.query
                connection.request("GET", path, headers={
                    "User-Agent": "ResearchFlow/0.1",
                    "Accept": "application/pdf,application/octet-stream;q=0.9",
                    "Accept-Encoding": "identity",
                })
                response = connection.getresponse()
                if response.status in (301, 302, 303, 307, 308):
                    location = response.getheader("Location")
                    if not location or redirect == 5:
                        raise DocumentError("pdf_download_failed", "The PDF source has too many redirects.")
                    url = urljoin(url, location)
                    continue
                if response.status != 200:
                    raise DocumentError("pdf_download_failed", "The PDF source could not be downloaded.")
                declared = response.getheader("Content-Length")
                if declared and int(declared) > MAX_PDF_BYTES:
                    raise DocumentError("pdf_too_large", "The PDF exceeds the 25 MiB size limit.")
                digest = hashlib.sha256()
                size = 0
                header = b""
                with partial.open("wb") as output:
                    while True:
                        if time.monotonic() >= deadline:
                            raise TimeoutError
                        block = response.read1(65536)
                        if not block:
                            break
                        size += len(block)
                        if size > MAX_PDF_BYTES:
                            raise DocumentError("pdf_too_large", "The PDF exceeds the 25 MiB size limit.")
                        if len(header) < 5:
                            header += block[:5 - len(header)]
                        digest.update(block)
                        output.write(block)
                if header != b"%PDF-":
                    raise DocumentError("invalid_pdf", "The downloaded file is not a PDF.")
                if declared and size != int(declared):
                    raise DocumentError("pdf_download_failed", "The PDF download was incomplete.")
                partial.replace(target)
                return size, digest.hexdigest()
            finally:
                connection.close()
        raise DocumentError("pdf_download_failed", "The PDF source could not be downloaded.")
    except (OSError, ValueError, http.client.HTTPException) as exc:
        raise DocumentError("pdf_download_failed", "The PDF download failed or timed out.") from exc
    finally:
        partial.unlink(missing_ok=True)
