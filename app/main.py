import socket
import sys
import threading
from pathlib import Path
from socket import socket as Socket


def new_line() -> str:
    return "\r\n"


def status_ok() -> str:
    return "HTTP/1.1 200 OK"


def status_not_found() -> str:
    return "HTTP/1.1 404 Not Found"


def index() -> str:
    return status_ok() + new_line() + new_line()


def echo(param: str) -> str:
    message = ""
    message += status_ok() + new_line()
    message += "Content-Type: text/plain" + new_line()
    message += f"Content-Length: {len(param)}" + new_line()
    message += new_line()
    message += param
    return message


def user_agent(header: str) -> str:
    message = ""
    message += status_ok() + new_line()
    message += "Content-Type: text/plain" + new_line()
    message += f"Content-Length: {len(header)}" + new_line()
    message += new_line()
    message += header
    return message


def not_found() -> str:
    return status_not_found() + new_line() + new_line()


FILES_DIR = "/tmp/"


def files(file: str) -> str:
    filepath = Path(Path(FILES_DIR) / file.lstrip("/")).resolve()
    if not filepath.is_relative_to(Path(FILES_DIR).resolve()):
        return not_found()
    if not filepath.exists():
        return not_found()
    with open(filepath, "rb") as f:
        data = f.read()
    message = ""
    message += status_ok() + new_line()
    message += "Content-Type: application/octet-stream" + new_line()
    message += f"Content-Length: {len(data)}" + new_line()
    message += new_line()
    message += data.decode()
    return message


def handle_connection(connection: Socket):
    with connection as con:
        request = con.recv(4_096).decode()
        request_lines_and_body = request.split("\r\n\r\n")
        body = None
        if len(request_lines_and_body) == 2:
            body = request_lines_and_body[1]
        request_lines = request_lines_and_body[0].split("\r\n")
        request_line, headers = request_lines[0], request_lines[1:]
        agent = None
        for header in headers:
            key, value = header.split()
            if key.lower() == "user-agent:":
                agent = value
        request_line_parts = request_line.split()
        method, target, version = (
            request_line_parts[0],
            request_line_parts[1],
            request_line_parts[2],
        )
        response = ""
        if target == "/":
            response = index()
        elif target.startswith("/echo/"):
            param = target[6:]
            response = echo(param)
        elif target.startswith("/files"):
            file = target[6:]
            response = files(file)
        elif target.startswith("/user-agent") and agent:
            response = user_agent(agent)
        else:
            response += not_found()
        con.sendall(response.encode())


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
        connection, address = server_socket.accept()  # wait for client
        thread = threading.Thread(target=handle_connection, args=(connection,))
        thread.start()


if __name__ == "__main__":
    main()
