import io
from unittest.mock import Mock

import pytest

from pynats import NATSClient


@pytest.mark.parametrize("unrelated_count", [0, 1, 3])
@pytest.mark.parametrize("with_ping", [False, True])
def test_request_waits_for_its_reply(unrelated_count, with_ping):
    client = NATSClient()
    client._socket = Mock()
    received = []
    sub = client.subscribe("events", callback=received.append)

    # request() allocates the next subscription id for its temporary inbox.
    reply_sid = client._ssid
    data = b""
    for index in range(unrelated_count):
        payload = str(index).encode()
        data += b"MSG events %d %d\r\n" % (sub.sid, len(payload))
        data += payload + b"\r\n"
    if with_ping:
        data += b"PING\r\n"
    data += b"MSG _INBOX.reply %d 5\r\nreply\r\n" % reply_sid
    client._socket_file = io.BytesIO(data)

    response = client.request("service", payload=b"question")

    assert response.sid == reply_sid
    assert response.payload == b"reply"
    assert [message.payload for message in received] == [
        str(index).encode() for index in range(unrelated_count)
    ]
    assert sub.received_messages == unrelated_count
    assert sub.sid in client._subs
    assert reply_sid not in client._subs
    if with_ping:
        assert any(
            call[0] == (b"PONG\r\n",) for call in client._socket.sendall.call_args_list
        )
