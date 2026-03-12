import socket
import threading
from socket import socket as Socket


def status_ok() -> str:
    return "HTTP/1.1 200 OK\r\n"


def status_not_found() -> str:
    return "HTTP/1.1 404 Not Found\r\n\r\n"


def with_body(body: str) -> str:
    return f"Content-Type: text/plain\r\nContent-Length: {len(body)}\r\n\r\n{body}"


def handle_connection(connection: Socket):
    try:
        request = connection.recv(4_096).decode()
        request_lines_and_body = request.split("\r\n\r\n")
        body = None
        if len(request_lines_and_body) == 2:
            body = request_lines_and_body[1]
        request_lines = request_lines_and_body[0].split("\r\n")
        request_line, headers = request_lines[0], request_lines[1:]
        user_agent = None
        for header in headers:
            key, value = header.split()
            if key.lower() == "user-agent:":
                user_agent = value
        request_line_parts = request_line.split()
        method, target, version = (
            request_line_parts[0],
            request_line_parts[1],
            request_line_parts[2],
        )
        message = ""
        if target == "/":
            message += status_ok() + "\r\n"
        elif target.startswith("/echo/"):
            echo = target[6:]
            message += status_ok() + with_body(echo)
        elif target.startswith("/user-agent") and user_agent:
            message += status_ok() + with_body(user_agent)
        else:
            message += status_not_found()
        connection.sendall(message.encode())
    finally:
        connection.close()


def main():
    # You can use print statements as follows for debugging, they'll be visible when running tests.
    print("Logs from your program will appear here!")

    server_socket = socket.create_server(("localhost", 4221), reuse_port=True)
    while True:
        connection, address = server_socket.accept()  # wait for client
        thread = threading.Thread(target=handle_connection, args=(connection,))
        thread.start()


if __name__ == "__main__":
    main()
