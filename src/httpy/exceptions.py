class BadRequestException(Exception):
    def __init__(self, message: str, *args: object) -> None:
        super().__init__(message, *args)
        self.message = message


class InternalServerErrorException(Exception):
    def __init__(self, message: str, *args: object) -> None:
        super().__init__(message, *args)
        self.message = message
