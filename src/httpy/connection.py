from asyncio import StreamReader

from .exceptions import BadRequestException
from .protocol import (
    HttpRequest,
    HttpRequestLine,
    HttpVersion,
    HttpMethod,
    HttpTarget,
    HttpQuery,
    HttpHeaders,
)


class Connection:
    # TODO: Should these be configurable?
    _MAX_HEADER_LINES = 100
    _MAX_LINE_LENGTH = 8_192
    _MAX_BODY_BYTES = 1_024 * 1_024

    def __init__(self, reader: StreamReader):
        self.reader = reader

    async def get_request(self) -> HttpRequest:
        request_line = await self._parse_request_line()
        headers = await self._parse_headers()
        body = await self._read_body(headers)
        return HttpRequest(request_line, headers, body.decode() if body else None)

    async def _read_body(self, headers: HttpHeaders) -> bytes | None:
        body = None
        content_length = headers.get("content-length")
        transfer_encoding = headers.get("transfer-encoding")
        if content_length and transfer_encoding:
            raise BadRequestException(
                "cannot use both content-length and transfer-encoding"
            )
        if content_length:
            body = await self._read_body_fixed(int(content_length[0]))
        if transfer_encoding:
            raise NotImplementedError
        return body

    async def _read_body_fixed(self, length: int) -> bytes:
        if length < 0:
            raise BadRequestException("content-length cannot be negative")
        if length > self._MAX_BODY_BYTES:
            raise BadRequestException("content-length too large")
        return await self.reader.read(length)

    async def _read_request_line(self) -> bytes:
        request_line = await self.reader.readline()
        if len(request_line) > self._MAX_LINE_LENGTH:
            raise BadRequestException("request line too long")
        return request_line

    async def _parse_request_line(self) -> HttpRequestLine:
        raw_line = await self._read_request_line()
        parts = raw_line.strip().split()
        if len(parts) != 3:
            raise BadRequestException("malformed request line")
        raw_method, raw_target, raw_version = parts
        method = self._parse_method(raw_method)
        target = self._parse_target(raw_target)
        version = self._parse_version(raw_version)
        return HttpRequestLine(method, target, version)

    def _parse_header_line(self, raw_line: bytes) -> tuple[str, str]:
        key, _, value = raw_line.decode().partition(":")
        key = key.strip().lower()
        value = value.strip()
        return key, value

    async def _parse_headers(self) -> HttpHeaders:
        headers = HttpHeaders()
        for _ in range(self._MAX_HEADER_LINES):
            line = await self.reader.readline()
            if len(line) > self._MAX_LINE_LENGTH:
                raise BadRequestException("request header too long")
            if line in (b"\r\n\r\n", b"\r\n", b""):
                break
            key, value = self._parse_header_line(line)
            headers.setdefault(key, []).append(value)
        else:
            raise BadRequestException("request has too many headers")
        return headers

    def _parse_method(self, raw_method: bytes) -> HttpMethod:
        try:
            cleaned = raw_method.strip().decode()
            return HttpMethod(cleaned)
        except ValueError:
            raise BadRequestException("invalid request method")

    def _parse_queries(self, raw_queries: bytes) -> HttpQuery:
        cleaned = raw_queries.strip().decode()
        queries = HttpQuery()
        for query in cleaned.split(","):
            key, _, value = query.partition("=")
            queries.setdefault(key, []).append(value)
        return queries

    def _parse_target(self, raw_target: bytes) -> HttpTarget:
        raw_path, _, raw_queries = raw_target.partition(b"?")
        path = raw_path.strip().decode()
        queries = self._parse_queries(raw_queries)
        return HttpTarget(path, queries)

    def _parse_version(self, raw_version: bytes) -> HttpVersion:
        try:
            cleaned = raw_version.strip().decode()
            return HttpVersion(cleaned)
        except ValueError:
            raise BadRequestException("invalid request version")
