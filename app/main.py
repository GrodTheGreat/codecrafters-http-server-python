import socket


def main():
    # You can use print statements as follows for debugging, they'll be visible when running tests.
    print("Logs from your program will appear here!")

    server_socket = socket.create_server(("localhost", 4221), reuse_port=True)
    connection, address = server_socket.accept()  # wait for client
    request = connection.recv(4_096).decode()
    request_lines = request.split("\r\n")
    request_line = request_lines[0]
    request_line_parts = request_line.split()
    method, target, version = (
        request_line_parts[0],
        request_line_parts[1],
        request_line_parts[2],
    )
    if target == "/":
        connection.sendall(b"HTTP/1.1 200 OK\r\n\r\n")
    else:
        connection.sendall(b"HTTP1.1 404 Not Found\r\n\r\n")


if __name__ == "__main__":
    main()
