__all__ = (
    "NATSError",
    "NATSUnexpectedResponse",
    "NATSInvalidResponse",
    "NATSReadSocketError",
)


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


class NATSReadSocketError(NATSError):
    def __init__(self) -> None:
        super().__init__()
