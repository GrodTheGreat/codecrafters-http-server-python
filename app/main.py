import socket


def main():
    # You can use print statements as follows for debugging, they'll be visible when running tests.
    print("Logs from your program will appear here!")

    server_socket = socket.create_server(("localhost", 4221), reuse_port=True)
    connection, address = server_socket.accept()  # wait for client
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
    if target == "/":
        connection.sendall(b"HTTP/1.1 200 OK\r\n\r\n")
    elif target.startswith("/echo/"):
        echo = target[6:]
        message = f"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: {len(echo)}\r\n\r\n{echo}"
        connection.sendall(message.encode())
    elif target.startswith("/user-agent") and user_agent:
        message = f"HTTP/1.1 200 OK\r\nContent-Type: text/plain\r\nContent-Length: {len(user_agent)}\r\n\r\n{user_agent}"
        connection.sendall(message.encode())
    else:
        connection.sendall(b"HTTP/1.1 404 Not Found\r\n\r\n")


if __name__ == "__main__":
    main()
