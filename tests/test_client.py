import os
import socket
import threading
import time

import msgpack
import pytest

from pynats import NATSClient


@pytest.fixture
def nats_url():
    return os.environ.get("NATS_URL", "nats://127.0.0.1:4222")


def test_connect_and_close(nats_url):
    client = NATSClient(nats_url, socket_timeout=2)

    client.connect()
    client.ping()
    client.close()


def test_connect_and_close_using_context_manager(nats_url):
    with NATSClient(nats_url, socket_timeout=2) as client:
        client.ping()


def test_connect_timeout():
    client = NATSClient("nats://127.0.0.1:4223", socket_timeout=2)

    with pytest.raises(socket.error):
        client.connect()


def test_reconnect(nats_url):
    client = NATSClient(nats_url, socket_timeout=2)

    client.connect()
    client.ping()

    client.reconnect()
    client.ping()

    client.close()


def test_subscribe_unsubscribe(nats_url):
    with NATSClient(nats_url, socket_timeout=2) as client:
        sub = client.subscribe(
            "test-subject", callback=lambda x: x, queue="test-queue", max_messages=2
        )
        client.unsubscribe(sub)


def test_subscribe_timeout(nats_url):
    with NATSClient(nats_url, socket_timeout=2) as client:
        sub = client.subscribe(
            "test-subject", callback=lambda x: x, queue="test-queue", max_messages=1
        )

        with pytest.raises(socket.timeout):
            client.wait(count=1)

        client.unsubscribe(sub)


def test_publish(nats_url):
    received = []

    def worker():
        with NATSClient(nats_url, socket_timeout=2) as client:

            def callback(message):
                received.append(message)

            client.subscribe(
                "test-subject", callback=callback, queue="test-queue", max_messages=2
            )
            client.wait(count=2)

    t = threading.Thread(target=worker)
    t.start()

    time.sleep(1)

    with NATSClient(nats_url, socket_timeout=2) as client:
        # publish without payload
        client.publish("test-subject")
        # publish with payload
        client.publish("test-subject", payload=b"test-payload")

    t.join()

    assert len(received) == 2

    assert received[0].subject == "test-subject"
    assert received[0].reply == ""
    assert received[0].payload == b""

    assert received[1].subject == "test-subject"
    assert received[1].reply == ""
    assert received[1].payload == b"test-payload"


def test_request(nats_url):
    def worker():
        with NATSClient(nats_url, socket_timeout=2) as client:

            def callback(message):
                client.publish(message.reply, payload=b"test-callback-payload")

            client.subscribe(
                "test-subject", callback=callback, queue="test-queue", max_messages=2
            )
            client.wait(count=2)

    t = threading.Thread(target=worker)
    t.start()

    time.sleep(1)

    with NATSClient(nats_url, socket_timeout=2) as client:
        # request without payload
        resp = client.request("test-subject")
        assert resp.subject.startswith("_INBOX.")
        assert resp.reply == ""
        assert resp.payload == b"test-callback-payload"

        # request with payload
        resp = client.request("test-subject", payload=b"test-payload")
        assert resp.subject.startswith("_INBOX.")
        assert resp.reply == ""
        assert resp.payload == b"test-callback-payload"

    t.join()


def test_request_msgpack(nats_url):
    def worker():
        with NATSClient(nats_url, socket_timeout=2) as client:

            def callback(message):
                client.publish(
                    message.reply,
                    payload=msgpack.packb(
                        {b"v": 3338} if message.payload else {b"v": 32}
                    ),
                )

            client.subscribe(
                "test-subject", callback=callback, queue="test-queue", max_messages=2
            )
            client.wait(count=2)

    t = threading.Thread(target=worker)
    t.start()

    time.sleep(1)

    with NATSClient(nats_url, socket_timeout=2) as client:
        # request without payload
        resp = client.request("test-subject")
        assert resp.subject.startswith("_INBOX.")
        assert resp.reply == ""
        assert msgpack.unpackb(resp.payload) == {b"v": 32}

        # request with payload
        resp = client.request("test-subject", payload=msgpack.packb("test-payload"))
        assert resp.subject.startswith("_INBOX.")
        assert resp.reply == ""
        assert msgpack.unpackb(resp.payload) == {b"v": 3338}

    t.join()


def test_request_timeout(nats_url):
    with NATSClient(nats_url, socket_timeout=2) as client:
        with pytest.raises(socket.timeout):
            client.request("test-subject")


def test_exception_on_disconnect(nats_url):
    with NATSClient(nats_url, socket_timeout=2) as client:
        client.subscribe(
            "test-subject", callback=lambda x: x, queue="test-queue", max_messages=2
        )

        client._socket_file.readline = lambda: b""

        with pytest.raises(ConnectionResetError):
            client.wait()
