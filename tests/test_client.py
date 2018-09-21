import socket
import threading
import time

import msgpack
import pytest

from pynats import NATSClient


def test_connect_and_close():
    client = NATSClient(socket_timeout=2)

    client.connect()
    client.ping()
    client.close()


def test_connect_and_close_using_context_manager():
    with NATSClient(socket_timeout=2) as client:
        client.ping()


def test_connect_timeout():
    client = NATSClient("nats://127.0.0.1:4223", socket_timeout=2)

    with pytest.raises(socket.error):
        client.connect()


def test_reconnect():
    client = NATSClient(socket_timeout=2)

    client.connect()
    client.ping()

    client.reconnect()
    client.ping()

    client.close()


def test_subscribe_unsubscribe():
    with NATSClient(socket_timeout=2) as client:
        sub = client.subscribe(
            "test-subject", callback=lambda x: x, queue="test-queue", max_messages=2
        )
        client.unsubscribe(sub)


def test_subscribe_timeout():
    with NATSClient(socket_timeout=2) as client:
        sub = client.subscribe(
            "test-subject", callback=lambda x: x, queue="test-queue", max_messages=1
        )

        with pytest.raises(socket.timeout):
            client.wait(count=1)

        client.unsubscribe(sub)


def test_publish():
    received = []

    def worker():
        with NATSClient(socket_timeout=2) as client:

            def callback(message):
                received.append(message)

            client.subscribe(
                "test-subject", callback=callback, queue="test-queue", max_messages=2
            )
            client.wait(count=2)

    t = threading.Thread(target=worker)
    t.start()

    time.sleep(1)

    with NATSClient(socket_timeout=2) as client:
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


def test_request():
    def worker():
        with NATSClient(socket_timeout=2) as client:

            def callback(message):
                client.publish(message.reply, payload=b"test-callback-payload")

            client.subscribe(
                "test-subject", callback=callback, queue="test-queue", max_messages=2
            )
            client.wait(count=2)

    t = threading.Thread(target=worker)
    t.start()

    time.sleep(1)

    with NATSClient(socket_timeout=2) as client:
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


def test_request_msgpack():
    def worker():
        with NATSClient(socket_timeout=2) as client:

            def callback(message):
                client.publish(message.reply, payload=msgpack.packb(32))

            client.subscribe(
                "test-subject", callback=callback, queue="test-queue", max_messages=2
            )
            client.wait(count=2)

    t = threading.Thread(target=worker)
    t.start()

    time.sleep(1)

    with NATSClient(socket_timeout=2) as client:
        # request without payload
        resp = client.request("test-subject")
        assert resp.subject.startswith("_INBOX.")
        assert resp.reply == ""
        assert msgpack.unpackb(resp.payload) == 32

        # request with payload
        resp = client.request("test-subject", payload=msgpack.packb("test-payload"))
        assert resp.subject.startswith("_INBOX.")
        assert resp.reply == ""
        assert msgpack.unpackb(resp.payload) == 32

    t.join()


def test_request_timeout():
    with NATSClient(socket_timeout=2) as client:
        with pytest.raises(socket.timeout):
            client.request("test-subject")
