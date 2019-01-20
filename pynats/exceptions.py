__all__ = ("NATSError", "NATSUnexpectedResponse", "NATSInvalidResponse")


class NATSError(Exception):
    pass


class NATSUnexpectedResponse(NATSError):
    def __init__(self, line: bytes, *args, **kwargs) -> None:
        self.line = line
        super().__init__()


class NATSInvalidResponse(NATSError):
    def __init__(self, line: bytes, *args, **kwargs) -> None:
        self.line = line
        super().__init__()
