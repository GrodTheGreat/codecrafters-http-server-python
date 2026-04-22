from collections import UserDict
from dataclasses import dataclass
from enum import Enum


class HttpVersion(Enum):
    V0_9 = "HTTP/0.9"
    V1_0 = "HTTP/1.0"
    V1_1 = "HTTP/1.1"
    V2_0 = "HTTP/2.0"
    V3_0 = "HTTP/3.0"


class HttpMethod(Enum):
    HEAD = "HEAD"
    OPTIONS = "OPTIONS"
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    PATCH = "PATCH"
    DELETE = "DELETE"


class HttpQuery(UserDict[str, list[str]]): ...


@dataclass(frozen=True)
class HttpTarget:
    path: str
    queries: HttpQuery


class HttpStatus(Enum):
    OK = "200 OK"
    CREATED = "201 Created"
    NO_CONTENT = "204 No Content"
    BAD_REQUEST = "400 Bad Request"
    UNAUTHORIZED = "401 Unauthorized"
    FORBIDDEN = "403 Forbidden"
    NOT_FOUND = "404 Not Found"
    METHOD_NOT_ALLOWED = "405 Method Not Allowed"
    CONFLICT = "409 Conflict"
    INTERNAL_SERVER_ERROR = "500 Internal Server Error"


@dataclass(frozen=True)
class HttpRequestLine:
    method: HttpMethod
    target: HttpTarget
    version: HttpVersion


class HttpHeaders(UserDict[str, list[str]]):
    def __getitem__(self, key: str) -> list[str]:
        return self.data[key.lower()]

    def __setitem__(self, key: str, value: list[str]) -> None:
        self.data[key.lower()] = value


@dataclass(frozen=True)
class HttpRequest:
    request_line: HttpRequestLine
    headers: HttpHeaders
    body: str | bytes | None = None

    @property
    def method(self) -> HttpMethod:
        return self.request_line.method

    @property
    def path(self) -> str:
        return self.request_line.target.path

    @property
    def query(self) -> HttpQuery:
        return self.request_line.target.queries

    @property
    def version(self) -> HttpVersion:
        return self.request_line.version


@dataclass(frozen=True)
class HttpStatusLine:
    version: HttpVersion
    status: HttpStatus


@dataclass(frozen=True)
class HttpResponse:
    status_line: HttpStatusLine
    headers: HttpHeaders
    body: str | bytes | None = None

    def serialize(self) -> bytes:
        message: list[bytes] = []
        message += [
            self.status_line.version.value.encode(),
            b" ",
            self.status_line.status.value.encode(),
            b"\r\n",
        ]
        for key in self.headers.keys():
            for value in self.headers[key]:
                message += [key, b": ", value, b"\r\n"]
        message.append(b"\r\n")
        if isinstance(self.body, bytes):
            message.append(self.body)
        elif isinstance(self.body, str):
            message.append(self.body.encode())
        return b"".join(message)
