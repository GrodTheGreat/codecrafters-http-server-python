import gzip
import socket
import sys
import threading
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from socket import socket as Socket


class BadRequestException(Exception):
    pass


class HttpVersion(Enum):
    V1_1 = b"HTTP/1.1"


class HttpMethod(Enum):
    GET = b"GET"
    POST = b"POST"


class HttpStatus(Enum):
    OK = b"200 OK"
    CREATED = b"201 Created"
    BAD_REQUEST = b"400 Bad Request"
    NOT_FOUND = b"404 Not Found"
    INTERNAL_SERVER_ERROR = b"500 Internal Server Error"


class HttpRequestLine:
    def __init__(self, raw_line: bytes) -> None:
        try:
            raw_method, raw_target, raw_version = raw_line.split()
            self.method = HttpMethod(raw_method)
            self.target = raw_target
            self.version = HttpVersion(raw_version)
        except ValueError:
            raise BadRequestException()


HttpHeaders = dict[bytes, list[bytes]]


@dataclass
class HttpRequest:
    request_line: HttpRequestLine
    headers: HttpHeaders
    body: bytes | None = None


@dataclass
class HttpStatusLine:
    version: HttpVersion
    status: HttpStatus


@dataclass
class HttpResponse:
    status_line: HttpStatusLine
    headers: HttpHeaders
    body: bytes | None

    def serialize(self) -> bytes:
        message: list[bytes] = []
        message += [
            self.status_line.version.value,
            b" ",
            self.status_line.status.value,
            b"\r\n",
        ]
        for key in self.headers.keys():
            for value in self.headers[key]:
                message += [key, b": ", value, b"\r\n"]
        message.append(b"\r\n")
        if self.body is not None:
            message.append(self.body)
        return b"".join(message)


def parse_request(raw_data: bytes) -> HttpRequest:
    try:
        meta, body = raw_data.split(b"\r\n\r\n", maxsplit=1)
        body = body if body else None
    except ValueError:
        raise BadRequestException()
    lines = meta.split(b"\r\n")
    request_line = HttpRequestLine(lines[0])
    headers: HttpHeaders = {}
    for line in lines[1:]:
        try:
            name, value = line.split(b": ", maxsplit=1)
            name = name.lower()
            headers.setdefault(name, []).append(value)
        except ValueError:
            raise BadRequestException()
    return HttpRequest(request_line, headers, body)


def not_found() -> HttpResponse:
    return HttpResponse(
        HttpStatusLine(HttpVersion.V1_1, HttpStatus.NOT_FOUND),
        {},
        None,
    )


def bad_request() -> HttpResponse:
    return HttpResponse(
        HttpStatusLine(HttpVersion.V1_1, HttpStatus.BAD_REQUEST),
        {},
        None,
    )


def internal_server_error() -> HttpResponse:
    return HttpResponse(
        HttpStatusLine(HttpVersion.V1_1, HttpStatus.INTERNAL_SERVER_ERROR),
        {},
        None,
    )


def index() -> HttpResponse:
    return HttpResponse(HttpStatusLine(HttpVersion.V1_1, HttpStatus.OK), {}, None)


def echo(request: HttpRequest) -> HttpResponse:
    param = request.request_line.target[6:]
    encoding = request.headers.get(b"accept-encoding")
    headers = {}
    if encoding == b"gzip":
        headers[b"Content-Encoding"] = [b"gzip"]
        param = gzip.compress(param)
    headers[b"Content-Type"] = [b"text/plain"]
    headers[b"Content-Length"] = [str(len(param)).encode()]
    return HttpResponse(HttpStatusLine(HttpVersion.V1_1, HttpStatus.OK), headers, param)


def user_agent(request: HttpRequest) -> HttpResponse:
    if b"user-agent" not in request.headers:
        raise BadRequestException()
    agent = request.headers[b"user-agent"][0]
    headers = {
        b"Content-Type": [b"text/plain"],
        b"Content-Length": [str(len(agent)).encode()],
    }
    return HttpResponse(HttpStatusLine(HttpVersion.V1_1, HttpStatus.OK), headers, agent)


FILES_DIR = "/tmp/"


def get_files(request: HttpRequest) -> HttpResponse:
    try:
        file = request.request_line.target[7:]
    except IndexError:
        raise BadRequestException()
    filepath = Path(Path(FILES_DIR) / file.decode()).resolve()
    if not filepath.is_relative_to(Path(FILES_DIR).resolve()):
        return not_found()
    if not filepath.exists():
        return not_found()
    with open(filepath, "rb") as f:
        data = f.read()
    headers = {
        b"Content-Type": [b"application/octet-stream"],
        b"Content-Length": [str(len(data)).encode()],
    }
    return HttpResponse(HttpStatusLine(HttpVersion.V1_1, HttpStatus.OK), headers, data)


def post_files(request: HttpRequest) -> HttpResponse:
    try:
        filename = request.request_line.target[7:]
    except IndexError:
        raise BadRequestException()
    filepath = Path(Path(FILES_DIR) / filename.decode()).resolve()
    if not filepath.is_relative_to(Path(FILES_DIR).resolve()):
        raise BadRequestException()
    if request.body is None or not request.body:
        raise BadRequestException()
    with open(filepath, "wb") as f:
        f.write(request.body)
    return HttpResponse(HttpStatusLine(HttpVersion.V1_1, HttpStatus.CREATED), {}, None)


def handle_connection(connection: Socket):
    with connection as con:
        try:
            raw_request = con.recv(4_096)
            request = parse_request(raw_request)
            match (request.request_line.method, request.request_line.target):
                case (HttpMethod.GET, b"/"):
                    response = index()
                case (HttpMethod.GET, target) if target.startswith(b"/echo/"):
                    response = echo(request)
                case (HttpMethod.GET, b"/user-agent"):
                    response = user_agent(request)
                case (HttpMethod.GET, target) if target.startswith(b"/files/"):
                    response = get_files(request)
                case (HttpMethod.POST, target) if target.startswith(b"/files/"):
                    response = post_files(request)
                case _:
                    response = not_found()
        except BadRequestException:
            response = bad_request()
        except Exception:
            response = internal_server_error()
        con.sendall(response.serialize())


def main():
    global FILES_DIR
    # You can use print statements as follows for debugging, they'll be visible when running tests.
    print("Logs from your program will appear here!")

    args = sys.argv
    if "--directory" in args:
        root = args.index("--directory")
        FILES_DIR = args[root + 1]

    server_socket = socket.create_server(("localhost", 4221), reuse_port=True)
    while True:
        connection, _ = server_socket.accept()  # wait for client
        thread = threading.Thread(target=handle_connection, args=(connection,))
        thread.start()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nserver shutting down...")
        print("have a good day :)")
