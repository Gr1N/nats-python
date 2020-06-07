import io
import json
import re
import socket
import ssl
from dataclasses import dataclass
from typing import BinaryIO, Callable, Dict, Match, Optional, Pattern, Tuple, Union
from urllib.parse import urlparse

import pkg_resources

from pynats.exceptions import (
    NATSInvalidResponse,
    NATSInvalidSchemeError,
    NATSReadSocketError,
    NATSTCPConnectionRequiredError,
    NATSTLSConnectionRequiredError,
    NATSUnexpectedResponse,
)
from pynats.nuid import NUID

__all__ = ("NATSSubscription", "NATSMessage", "NATSClient")


INFO_OP = b"INFO"
CONNECT_OP = b"CONNECT"
PING_OP = b"PING"
PONG_OP = b"PONG"
SUB_OP = b"SUB"
UNSUB_OP = b"UNSUB"
PUB_OP = b"PUB"
MSG_OP = b"MSG"
OK_OP = b"+OK"
ERR_OP = b"-ERR"

INFO_RE = re.compile(rb"^INFO\s+([^\r\n]+)\r\n")
PING_RE = re.compile(rb"^PING\r\n")
PONG_RE = re.compile(rb"^PONG\r\n")
MSG_RE = re.compile(
    rb"^MSG\s+(?P<subject>[^\s\r\n]+)\s+(?P<sid>[^\s\r\n]+)\s+(?P<reply>([^\s\r\n]+)[^\S\r\n]+)?(?P<size>\d+)\r\n"  # noqa
)
OK_RE = re.compile(rb"^\+OK\s*\r\n")
ERR_RE = re.compile(rb"^-ERR\s+('.+')?\r\n")

_CRLF_ = b"\r\n"
_SPC_ = b" "

COMMANDS = {
    INFO_OP: INFO_RE,
    PING_OP: PING_RE,
    PONG_OP: PONG_RE,
    MSG_OP: MSG_RE,
    OK_OP: OK_RE,
    ERR_OP: ERR_RE,
}

INBOX_PREFIX = bytearray(b"_INBOX.")


@dataclass
class NATSSubscription:
    sid: int
    subject: str
    queue: str
    callback: Callable
    max_messages: Optional[int] = None
    received_messages: int = 0

    def is_wasted(self):
        return (
            self.max_messages is not None
            and self.received_messages == self.max_messages
        )


@dataclass
class NATSMessage:
    sid: int
    subject: str
    reply: str
    payload: bytes


@dataclass
class NATSConnOptions:
    hostname: Optional[str]
    port: Optional[int]
    username: Optional[str]
    password: Optional[str]
    scheme: str
    name: str = "nats-python"
    lang: str = "python"
    protocol: int = 0
    tls_cacert: Optional[str] = None
    tls_client_cert: Optional[str] = None
    tls_client_key: Optional[str] = None
    tls_hostname: Optional[str] = None
    tls_verify: bool = False
    version: str = pkg_resources.get_distribution("nats-python").version
    verbose: bool = False
    pedantic: bool = False


class NATSClient:
    __slots__ = (
        "_conn_options",
        "_socket",
        "_socket_file",
        "_socket_options",
        "_ssid",
        "_subs",
        "_nuid",
    )

    def __init__(
        self,
        url: str = "nats://127.0.0.1:4222",
        *,
        name: str = "nats-python",
        verbose: bool = False,
        pedantic: bool = False,
        tls_cacert: Optional[str] = None,
        tls_client_cert: Optional[str] = None,
        tls_client_key: Optional[str] = None,
        tls_hostname: Optional[str] = None,
        tls_verify: bool = False,
        socket_timeout: float = None,
        socket_keepalive: bool = False,
    ) -> None:
        parsed = urlparse(url)
        self._conn_options = NATSConnOptions(
            hostname=parsed.hostname,
            port=parsed.port,
            username=parsed.username,
            password=parsed.password,
            scheme=parsed.scheme,
            name=name,
            tls_cacert=tls_cacert,
            tls_client_cert=tls_client_cert,
            tls_client_key=tls_client_key,
            tls_hostname=tls_hostname,
            tls_verify=tls_verify,
            verbose=verbose,
            pedantic=pedantic,
        )

        self._socket: socket.socket
        self._socket_file: BinaryIO
        self._socket_options = {
            "timeout": socket_timeout,
            "keepalive": socket_keepalive,
        }

        self._ssid = 0
        self._subs: Dict[int, NATSSubscription] = {}
        self._nuid = NUID()

    def __enter__(self) -> "NATSClient":
        self.connect()
        return self

    def __exit__(self, type_, value, traceback) -> None:
        self.close()

    def connect(self) -> None:
        sock = socket.socket(family=socket.AF_INET, type=socket.SOCK_STREAM)

        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        if self._socket_options["keepalive"]:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)

        sock.settimeout(self._socket_options["timeout"])
        sock.connect((self._conn_options.hostname, self._conn_options.port))

        self._socket_file = sock.makefile("rb")
        self._socket = sock

        scheme = self._conn_options.scheme

        if scheme == "nats":
            self._try_connection(tls_required=False)
        elif scheme == "tls":
            self._try_connection(tls_required=True)
            self._connect_tls()
        else:
            raise NATSInvalidSchemeError(f"got unsupported URI scheme: {scheme}")

        self._send_connect_command()
        if self._conn_options.verbose:
            self._recv(OK_RE)

    def _try_connection(self, *, tls_required: bool) -> None:
        _, result = self._recv(INFO_RE)
        server_info = json.loads(result.group(1))
        server_tls_required = server_info.get("tls_required", False)

        if not tls_required and server_tls_required:
            raise NATSTLSConnectionRequiredError()
        elif tls_required and not server_tls_required:
            raise NATSTCPConnectionRequiredError()

    def _connect_tls(self) -> None:
        ctx = ssl.create_default_context(purpose=ssl.Purpose.SERVER_AUTH)
        if not self._conn_options.tls_verify:
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

        if self._conn_options.tls_cacert is not None:
            ctx.load_verify_locations(cafile=self._conn_options.tls_cacert)

        if (
            self._conn_options.tls_client_cert is not None
            and self._conn_options.tls_client_key is not None
        ):
            ctx.load_cert_chain(
                certfile=self._conn_options.tls_client_cert,
                keyfile=self._conn_options.tls_client_key,
            )

        hostname = self._conn_options.hostname
        if self._conn_options.tls_hostname is not None:
            hostname = self._conn_options.tls_hostname

        self._socket = ctx.wrap_socket(self._socket, server_hostname=hostname)
        self._socket_file = self._socket.makefile("rb")

    def close(self) -> None:
        self._socket.shutdown(socket.SHUT_RDWR)
        self._socket_file.close()
        self._socket.close()

    def reconnect(self) -> None:
        self.close()
        self.connect()

    def ping(self) -> None:
        self._send(PING_OP)
        self._recv(PONG_RE)

    def subscribe(
        self,
        subject: str,
        *,
        callback: Callable,
        queue: str = "",
        max_messages: Optional[int] = None,
    ) -> NATSSubscription:
        sub = NATSSubscription(
            sid=self._ssid,
            subject=subject,
            queue=queue,
            callback=callback,
            max_messages=max_messages,
        )

        self._ssid += 1
        self._subs[sub.sid] = sub
        self._send(SUB_OP, sub.subject, sub.queue, sub.sid)

        return sub

    def unsubscribe(self, sub: NATSSubscription) -> None:
        self._send(UNSUB_OP, sub.sid)
        self._subs.pop(sub.sid)

    def auto_unsubscribe(self, sub: NATSSubscription) -> None:
        if sub.max_messages is None:
            return

        self._send(UNSUB_OP, sub.sid, sub.max_messages)

    def publish(self, subject: str, *, payload: bytes = b"", reply: str = "") -> None:
        self._send(PUB_OP, subject, reply, len(payload))
        self._send(payload)

    def request(self, subject: str, *, payload: bytes = b"") -> NATSMessage:
        next_inbox = INBOX_PREFIX[:]
        next_inbox.extend(self._nuid.next_())

        reply_subject = next_inbox.decode()
        reply_messages: Dict[int, NATSMessage] = {}

        def callback(message: NATSMessage) -> None:
            reply_messages[message.sid] = message

        sub = self.subscribe(reply_subject, callback=callback, max_messages=1)
        self.auto_unsubscribe(sub)
        self.publish(subject, payload=payload, reply=reply_subject)
        self.wait(count=1)

        return reply_messages[sub.sid]

    def wait(self, *, count=None) -> None:
        total = 0
        while True:
            command, result = self._recv(MSG_RE, PING_RE, OK_RE)
            if command is MSG_RE:
                self._handle_message(result)

                total += 1
                if count is not None and total >= count:
                    break
            elif command is PING_RE:
                self._send(PONG_OP)

    def _send_connect_command(self) -> None:
        options = {
            "name": self._conn_options.name,
            "lang": self._conn_options.lang,
            "protocol": self._conn_options.protocol,
            "version": self._conn_options.version,
            "verbose": self._conn_options.verbose,
            "pedantic": self._conn_options.pedantic,
        }

        if self._conn_options.username and self._conn_options.password:
            options["user"] = self._conn_options.username
            options["pass"] = self._conn_options.password
        elif self._conn_options.username:
            options["auth_token"] = self._conn_options.username

        self._send(CONNECT_OP, json.dumps(options))

    def _send(self, *parts: Union[bytes, str, int]) -> None:
        self._socket.sendall(_SPC_.join(self._encode(p) for p in parts) + _CRLF_)

    def _encode(self, value: Union[bytes, str, int]) -> bytes:
        if isinstance(value, bytes):
            return value
        elif isinstance(value, str):
            return value.encode()
        elif isinstance(value, int):  # pragma: no branch
            return f"{value:d}".encode()

        raise RuntimeError(f"got unsupported type for encoding: type={type(value)}")

    def _recv(self, *commands: Pattern[bytes]) -> Tuple[Pattern[bytes], Match[bytes]]:
        line = self._readline()

        command = self._get_command(line)
        if command not in commands:
            raise NATSUnexpectedResponse(line)

        result = command.match(line)
        if result is None:
            raise NATSInvalidResponse(line)

        return command, result

    def _readline(self, *, size: int = None) -> bytes:
        read = io.BytesIO()

        while True:
            line = self._socket_file.readline()
            if not line:
                raise NATSReadSocketError()

            read.write(line)

            if size is not None:
                if read.tell() == size + len(_CRLF_):
                    break
            elif line.endswith(_CRLF_):  # pragma: no branch
                break

        return read.getvalue()

    def _strip(self, line: bytes) -> bytes:
        return line[: -len(_CRLF_)]

    def _get_command(self, line: bytes) -> Optional[Pattern[bytes]]:
        values = self._strip(line).split(b" ", 1)

        return COMMANDS.get(values[0])

    def _handle_message(self, result: Match[bytes]) -> None:
        message_data = result.groupdict()

        message_payload_size = int(message_data["size"])
        message_payload = self._readline(size=message_payload_size)
        message_payload = self._strip(message_payload)

        message = NATSMessage(
            sid=int(message_data["sid"].decode()),
            subject=message_data["subject"].decode(),
            reply=message_data["reply"].decode() if message_data["reply"] else "",
            payload=message_payload,
        )

        sub = self._subs[message.sid]
        sub.received_messages += 1

        if sub.is_wasted():
            self._subs.pop(sub.sid)

        sub.callback(message)
