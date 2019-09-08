__all__ = (
    "NATSConnectionError",
    "NATSError",
    "NATSInvalidResponse",
    "NATSInvalidSchemeError",
    "NATSReadSocketError",
    "NATSTCPConnectionRequiredError",
    "NATSTLSConnectionRequiredError",
    "NATSUnexpectedResponse",
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


class NATSConnectionError(NATSError):
    def __init__(self, line: str, *args, **kwargs) -> None:
        self.line = line
        super().__init__()


class NATSTCPConnectionRequiredError(NATSConnectionError):
    def __init__(self, line: str, *args, **kwargs) -> None:
        self.line = line
        super().__init__(line, *args, **kwargs)


class NATSTLSConnectionRequiredError(NATSConnectionError):
    def __init__(self, line: str, *args, **kwargs) -> None:
        self.line = line
        super().__init__(line, *args, **kwargs)


class NATSInvalidSchemeError(NATSConnectionError):
    def __init__(self, line: str, *args, **kwargs) -> None:
        self.line = line
        super().__init__(line, *args, **kwargs)


class NATSReadSocketError(NATSError):
    def __init__(self) -> None:
        super().__init__()
