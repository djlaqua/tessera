import importlib.util
import socket
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "scripts" / "sitl_relay.py"


def _load():
    spec = importlib.util.spec_from_file_location("sitl_relay", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_try_send_delivers_to_a_listener():
    relay = _load()
    with (
        socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as listener,
        socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender,
    ):
        listener.bind(("127.0.0.1", 0))
        assert relay.try_send(sender, b"x", listener.getsockname()) is True


def test_try_send_returns_false_when_name_does_not_resolve():
    relay = _load()
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender:
        assert relay.try_send(sender, b"x", ("no-such-host.invalid", 14550)) is False
