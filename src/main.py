import asyncio
import gzip
import re
import sys
from asyncio import StreamReader, StreamWriter
from http import HTTPMethod
from pathlib import Path
from typing import Callable

from httpy.connection import Connection
from httpy.exceptions import BadRequestException, InternalServerErrorException
from httpy.protocol import (
    HttpResponse,
    HttpStatusLine,
    HttpHeaders,
    HttpVersion,
    HttpStatus,
    HttpRequest,
)


def ok(
        body: str | bytes | None = None,
        *,
        content_type: str = "text/plain",
        encoding: str | None = None,
) -> HttpResponse:
    headers = HttpHeaders()
    return HttpResponse(HttpStatusLine(HttpVersion.V1_1, HttpStatus.OK), headers, body)


def created() -> HttpResponse:
    return HttpResponse(HttpStatusLine(HttpVersion.V1_1, HttpStatus.OK), HttpHeaders(), None)


def not_found() -> HttpResponse:
    return HttpResponse(
        HttpStatusLine(HttpVersion.V1_1, HttpStatus.NOT_FOUND),
        HttpHeaders(),
        None,
    )


def bad_request() -> HttpResponse:
    return HttpResponse(
        HttpStatusLine(HttpVersion.V1_1, HttpStatus.BAD_REQUEST),
        HttpHeaders(),
        None,
    )


def internal_server_error() -> HttpResponse:
    return HttpResponse(
        HttpStatusLine(HttpVersion.V1_1, HttpStatus.INTERNAL_SERVER_ERROR),
        HttpHeaders(),
        None,
    )


def index(request: HttpRequest) -> HttpResponse:
    return ok()


def echo(request: HttpRequest) -> HttpResponse:
    pattern = re.compile(r"^/echo/(?P<message>.+)$")
    matcher = re.match(pattern, request.path)
    if not matcher:
        raise InternalServerErrorException()
    message = matcher.groupdict()["message"]
    encoding = request.headers.get("accept-encoding")
    headers = HttpHeaders()
    if encoding and "gzip" in encoding:
        headers["content-encoding"] = ["gzip"]
        message = gzip.compress(message.encode())
    headers["content-type"] = ["text/plain"]
    headers["content-length"] = [str(len(message))]
    if isinstance(message, str):
        message = message.encode()
    return HttpResponse(
        HttpStatusLine(HttpVersion.V1_1, HttpStatus.OK),
        headers,
        message,
    )


def user_agent(request: HttpRequest) -> HttpResponse:
    if "user-agent" not in request.headers:
        raise BadRequestException()
    agent = request.headers["user-agent"]
    headers = HttpHeaders()
    headers["content-type"] = ["text/plain"]
    headers["content-length"] = [str(len(agent))]
    return HttpResponse(
        HttpStatusLine(HttpVersion.V1_1, HttpStatus.OK),
        headers,
        agent[0],
    )


FILES_DIR = "/tmp/"


def get_files(request: HttpRequest) -> HttpResponse:
    try:
        file = request.request_line.target.path[7:]
    except IndexError:
        raise BadRequestException()
    filepath = Path(Path(FILES_DIR) / file).resolve()
    if not filepath.is_relative_to(Path(FILES_DIR).resolve()):
        return not_found()
    if not filepath.exists():
        return not_found()
    with open(filepath, "rb") as f:
        data = f.read()
    headers = HttpHeaders()
    headers["content-type"] = ["application/octet-stream"]
    headers["content-length"] = [str(len(data))]
    return HttpResponse(HttpStatusLine(HttpVersion.V1_1, HttpStatus.OK), headers, data)


def post_files(request: HttpRequest) -> HttpResponse:
    try:
        filename = request.request_line.target.path[7:]
    except IndexError:
        raise BadRequestException()
    filepath = Path(Path(FILES_DIR) / filename).resolve()
    if not filepath.is_relative_to(Path(FILES_DIR).resolve()):
        raise BadRequestException()
    if request.body is None or not request.body:
        raise BadRequestException("body is required for this request")
    if isinstance(request.body, str):
        with open(filepath, "w") as f:
            f.write(request.body)
    if isinstance(request.body, bytes):
        with open(filepath, "wb") as f:
            f.write(request.body)
    return HttpResponse(
        HttpStatusLine(HttpVersion.V1_1, HttpStatus.CREATED),
        HttpHeaders(),
        None,
    )


async def handle_connection(reader: StreamReader, writer: StreamWriter):
    router: dict[re.Pattern, dict[HTTPMethod, Callable]] = {
        re.compile(r"^/$"): {HTTPMethod.GET: index},
        re.compile(r"^/echo/(?P<message>.+)$"): {HTTPMethod.GET: echo},
        re.compile(r"^/user-agent$"): {HTTPMethod.GET: user_agent},
        re.compile(r"^/files/(?P<filename>.+)$"): {
            HTTPMethod.POST: post_files,
            HTTPMethod.GET: get_files,
        },
    }
    parser = Connection(reader)
    while not reader.at_eof():
        request = await parser.get_request()
        for route in router.keys():
            if not re.match(route, request.path):
                continue
            subroute = router.get(route)
            handler = subroute.get(request.method)
            if handler is None:
                # Need method not allowed response
                not_found().serialize()
            handler(request)
        if "connection" in request.headers and request.headers["connection"] == "close":
            writer.close()
            await writer.wait_closed()
            break
    pass


async def main() -> None:
    global FILES_DIR
    print("Logs from your program will appear here!")

    args = sys.argv
    if "--directory" in args:
        dir_index = args.index("--directory")
        FILES_DIR = args[dir_index + 1]

    server = await asyncio.start_server(
        handle_connection,
        host="localhost",
        port=4221,
        reuse_port=True,
    )
    async with server:
        await server.serve_forever()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nserver shutting down...")
        print("have a good day :)")
