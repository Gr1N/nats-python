import os
import socket
import threading
import time

import msgpack
import pytest

from pynats import NATSClient
from pynats.exceptions import NATSInvalidSchemeError, NATSReadSocketError


@pytest.fixture
def nats_plain_url():
    return os.environ.get("NATS_PLAIN_URL", "nats://127.0.0.1:4222")


@pytest.fixture
def nats_tls_url():
    return os.environ.get("NATS_TLS_URL", "tls://127.0.0.1:4224")


def test_connect_and_close(nats_plain_url):
    client = NATSClient(nats_plain_url, socket_timeout=2)

    client.connect()
    client.ping()
    client.close()


def test_connect_and_close_using_context_manager(nats_plain_url):
    with NATSClient(nats_plain_url, socket_timeout=2) as client:
        client.ping()


def test_connect_timeout():
    client = NATSClient("nats://127.0.0.1:4223", socket_timeout=2)

    with pytest.raises(socket.error):
        client.connect()


def test_reconnect(nats_plain_url):
    client = NATSClient(nats_plain_url, socket_timeout=2)

    client.connect()
    client.ping()

    client.reconnect()
    client.ping()

    client.close()


def test_tls_connect(nats_tls_url):
    client = NATSClient(nats_tls_url, socket_timeout=2)

    client.connect()
    client.ping()
    client.close()


def test_invalid_scheme():
    client = NATSClient("http://127.0.0.1:4224")

    with pytest.raises(NATSInvalidSchemeError):
        client.connect()


def test_subscribe_unsubscribe(nats_plain_url):
    with NATSClient(nats_plain_url, socket_timeout=2) as client:
        sub = client.subscribe(
            "test-subject", callback=lambda x: x, queue="test-queue", max_messages=2
        )
        client.unsubscribe(sub)


def test_subscribe_timeout(nats_plain_url):
    with NATSClient(nats_plain_url, socket_timeout=2) as client:
        sub = client.subscribe(
            "test-subject", callback=lambda x: x, queue="test-queue", max_messages=1
        )

        with pytest.raises(socket.timeout):
            client.wait(count=1)

        client.unsubscribe(sub)


def test_publish(nats_plain_url):
    received = []

    def worker():
        with NATSClient(nats_plain_url, socket_timeout=2) as client:

            def callback(message):
                received.append(message)

            client.subscribe(
                "test-subject", callback=callback, queue="test-queue", max_messages=2
            )
            client.wait(count=2)

    t = threading.Thread(target=worker)
    t.start()

    time.sleep(1)

    with NATSClient(nats_plain_url, socket_timeout=2) as client:
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


def test_request(nats_plain_url):
    def worker():
        with NATSClient(nats_plain_url, socket_timeout=2) as client:

            def callback(message):
                client.publish(message.reply, payload=b"test-callback-payload")

            client.subscribe(
                "test-subject", callback=callback, queue="test-queue", max_messages=2
            )
            client.wait(count=2)

    t = threading.Thread(target=worker)
    t.start()

    time.sleep(1)

    with NATSClient(nats_plain_url, socket_timeout=2) as client:
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


def test_request_msgpack(nats_plain_url):
    def worker():
        with NATSClient(nats_plain_url, socket_timeout=2) as client:

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

    with NATSClient(nats_plain_url, socket_timeout=2) as client:
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


def test_request_timeout(nats_plain_url):
    with NATSClient(nats_plain_url, socket_timeout=2) as client:
        with pytest.raises(socket.timeout):
            client.request("test-subject")


def test_graceful_shutdown(nats_plain_url):
    def worker(client, connected_event):
        client.connect()
        connected_event.set()
        try:
            client.wait()
        except NATSReadSocketError:
            assert True
        except Exception:
            raise AssertionError("unexpected Exception raised")

    client = NATSClient(nats_plain_url)
    connected_event = threading.Event()
    thread = threading.Thread(target=worker, args=[client, connected_event])
    thread.start()
    assert connected_event.wait(5), "unable to connect"
    client.close()
    thread.join(5)
    assert not thread.is_alive(), "thread did not finish"
