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
    pass


class NATSTCPConnectionRequiredError(NATSConnectionError):
    pass


class NATSTLSConnectionRequiredError(NATSConnectionError):
    pass


class NATSInvalidSchemeError(NATSConnectionError):
    pass


class NATSReadSocketError(NATSError):
    pass
