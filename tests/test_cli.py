import sys
from unittest.mock import patch

import pytest
import requests

from localcurl.cli import main, replace_address


def test_replace_address():
    original_url = "https://api.github.com/repos/user/repo"
    local_addr = "http://localhost:8080"
    expected = "http://localhost:8080/repos/user/repo"
    assert replace_address(original_url, local_addr) == expected


@pytest.mark.parametrize(
    "patcher_name", ["sysargv_patcher", "stdin_patcher", "clipboard_patcher"]
)
def test_main(patcher_name, fake_session, request):
    input_command_patcher = request.getfixturevalue(patcher_name)
    with input_command_patcher("curl", "http://example.com"):
        exit_code = main(session_factory=lambda: fake_session)

    assert exit_code == 0
    assert fake_session.sent_request.url == "http://localhost:8080/"
    assert fake_session.sent_request.method == "GET"


@pytest.fixture
def sysargv_patcher(*args: str):
    """Fixture to patch sys.argv for testing"""
    yield lambda *args: patch.object(
        sys, "argv", ["localcurl", "http://localhost:8080/", *args]
    )


@pytest.fixture
def stdin_patcher():
    """Fixture to patch sys.stdin for testing"""
    with patch.object(
        sys, "argv", ["localcurl", "http://localhost:8080/"]
    ), patch.object(sys.stdin, "isatty", return_value=False):
        yield lambda *args: patch.object(sys.stdin, "read", return_value=" ".join(args))


@pytest.fixture
def clipboard_patcher():
    """Fixture to patch pyperclip.paste for testing"""
    with patch.object(
        sys, "argv", ["localcurl", "http://localhost:8080/"]
    ), patch.object(sys.stdin, "isatty", return_value=True):
        yield lambda *args: patch("pyperclip.paste", return_value=" ".join(args))


class FakeSessionFactory:
    """Mimics the requests.Session class for testing purposes, it stores the last
    request sent through it.
    """

    def __init__(self):
        self.sent_request: requests.Request = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def send(self, request: requests.Request):
        self.sent_request = request
        return requests.Response()


@pytest.fixture
def fake_session():
    return FakeSessionFactory()
