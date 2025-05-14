import io
import shlex

import pytest
import requests

from localcurl.cli import main, replace_address


@pytest.mark.parametrize(
    "original_url, local_addr, expected",
    [
        # Basic case
        (
            "https://api.github.com/repos/user/repo",
            "http://localhost:8080",
            "http://localhost:8080/repos/user/repo",
        ),
        # URL with query parameters
        (
            "https://api.github.com/search?q=test",
            "http://localhost:8080",
            "http://localhost:8080/search?q=test",
        ),
        # URL with fragment
        (
            "https://api.github.com/docs#section1",
            "http://localhost:8080",
            "http://localhost:8080/docs#section1",
        ),
        # URL with port
        (
            "https://api.github.com:443/v1/data",
            "http://localhost:8080",
            "http://localhost:8080/v1/data",
        ),
    ],
)
def test_replace_address(original_url, local_addr, expected):
    """Check only the address part is replaced in the URL."""
    assert replace_address(original_url, local_addr) == expected


def generate_test_parameters(
    localaddr: str, curl_command: str, optional_args: list[str] | None = None
):
    """
    Generate test parameters for the main function, accounting for the 3 different ways
    the curl command can be passed to the program:
    - From the command line
    - From stdin
    - From the clipboard
    """
    if optional_args is None:
        optional_args = []

    return (
        pytest.param(
            ["localcurl", *optional_args, localaddr, *shlex.split(curl_command)],
            "",
            True,
            "",
            id="curl_from_command_line",
        ),
        pytest.param(
            ["localcurl", *optional_args, localaddr],
            curl_command,
            False,
            "",
            id="curl_from_stdin",
        ),
        pytest.param(
            ["localcurl", *optional_args, localaddr],
            "",
            True,
            curl_command,
            id="curl_from_clipboard",
        ),
    )


@pytest.mark.parametrize(
    ["cmd_line_args", "stdin_value", "is_stdin_a_tty", "clipboard_value"],
    generate_test_parameters(
        localaddr="http://localhost:8080/", curl_command="curl https://example.com"
    ),
)
def test_get_url(
    cmd_line_args,
    stdin_value,
    is_stdin_a_tty,
    clipboard_value,
    make_fake_stdin,
    make_fake_clipboard,
    fake_session,
):
    """Test the CLI interface for a simple GET request."""
    exit_code = main(
        cmd_line_args=cmd_line_args,
        stdin=make_fake_stdin(isatty=is_stdin_a_tty, initial_value=stdin_value),
        clipboard=make_fake_clipboard(clipboard_value),
        session_factory=lambda: fake_session,
    )

    assert exit_code == 0
    assert fake_session.sent_request.url == "http://localhost:8080/"
    assert fake_session.sent_request.method == "GET"


@pytest.mark.parametrize(
    ["cmd_line_args", "stdin_value", "is_stdin_a_tty", "clipboard_value"],
    generate_test_parameters(
        localaddr="http://localhost:8080/",
        curl_command="curl -b '__Host-foo=abc123' -H 'Cookie: __Host-bar=def456' https://example.com",
    ),
)
def test_strip_host_cookie_prefix_by_default(
    cmd_line_args,
    stdin_value,
    is_stdin_a_tty,
    clipboard_value,
    make_fake_stdin,
    make_fake_clipboard,
    fake_session,
):
    """Test that __Host- prefix is kept when --keep-host-cookie-prefix is passed."""
    print(f"{cmd_line_args=}")
    exit_code = main(
        cmd_line_args=cmd_line_args,
        stdin=make_fake_stdin(isatty=is_stdin_a_tty, initial_value=stdin_value),
        clipboard=make_fake_clipboard(clipboard_value),
        session_factory=lambda: fake_session,
    )

    assert exit_code == 0
    assert fake_session.sent_request.url == "http://localhost:8080/"
    assert "foo" in fake_session.sent_request._cookies
    assert "bar" in fake_session.sent_request._cookies


@pytest.mark.parametrize(
    ["cmd_line_args", "stdin_value", "is_stdin_a_tty", "clipboard_value"],
    generate_test_parameters(
        localaddr="http://localhost:8080/",
        curl_command="curl -b '__Host-foo=abc123' -H 'Cookie: __Host-bar=def456' https://example.com",
        optional_args=["--keep-host-cookie-prefix"],
    ),
)
def test_keep_host_cookie_prefix(
    cmd_line_args,
    stdin_value,
    is_stdin_a_tty,
    clipboard_value,
    make_fake_stdin,
    make_fake_clipboard,
    fake_session,
):
    """Test that __Host- prefix is kept when --keep-host-cookie-prefix is passed."""
    exit_code = main(
        cmd_line_args=cmd_line_args,
        stdin=make_fake_stdin(isatty=is_stdin_a_tty, initial_value=stdin_value),
        clipboard=make_fake_clipboard(clipboard_value),
        session_factory=lambda: fake_session,
    )

    assert exit_code == 0
    assert fake_session.sent_request.url == "http://localhost:8080/"
    assert "__Host-foo" in fake_session.sent_request._cookies
    assert "__Host-bar" in fake_session.sent_request._cookies


def test_handle_lines_curl_args_line_breaks_from_stdin(
    make_fake_stdin,
    make_fake_clipboard,
    fake_session,
):
    """Test that line breaks in curl command are handled correctly."""
    curl_command = (
        "curl 'https://example.com' \\\n -H 'Accept: application/json, text/plain, */*'"
    )
    stdin = make_fake_stdin(isatty=False, initial_value=curl_command)
    clipboard = make_fake_clipboard()

    exit_code = main(
        cmd_line_args=["localcurl", "http://localhost:8080/"],
        stdin=stdin,
        clipboard=clipboard,
        session_factory=lambda: fake_session,
    )

    assert exit_code == 0


def test_handle_lines_curl_args_line_breaks_from_clipboard(
    make_fake_stdin,
    make_fake_clipboard,
    fake_session,
):
    """Test that line breaks in curl command are handled correctly."""
    curl_command = (
        "curl 'https://example.com' \\\n -H 'Accept: application/json, text/plain, */*'"
    )
    stdin = make_fake_stdin()
    clipboard = make_fake_clipboard(initial_value=curl_command)

    exit_code = main(
        cmd_line_args=["localcurl", "http://localhost:8080/"],
        stdin=stdin,
        clipboard=clipboard,
        session_factory=lambda: fake_session,
    )

    assert exit_code == 0


class FakeStdin(io.StringIO):
    """Mimics sys.stdin for testing purposes."""

    def __init__(
        self,
        isatty: bool = True,
        initial_value: str | None = "",
        newline: str | None = "\n",
    ):
        super().__init__(initial_value, newline)
        self._isatty = isatty

    def isatty(self):
        return self._isatty


@pytest.fixture
def make_fake_stdin():
    def _make_fake_stdin(isatty: bool = True, initial_value: str = ""):
        return FakeStdin(isatty=isatty, initial_value=initial_value)

    return _make_fake_stdin


class FakeClipboard:
    """Mimics the pyperclip.paste function for testing purposes."""

    def __init__(self, initial_value: str = ""):
        self._value = initial_value

    def paste(self):
        return self._value


@pytest.fixture
def make_fake_clipboard():
    def _make_fake_clipboard(initial_value: str = ""):
        return FakeClipboard(initial_value)

    return _make_fake_clipboard


class FakeSessionFactory:
    """Mimics the minimal required portion of the  requests.Session interface for
    testing purposes (and it stores the last request sent through it).
    """

    def __init__(self):
        self.sent_request: requests.Request = requests.Request()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def send(self, request: requests.Request) -> requests.Response:
        self.sent_request = request
        return requests.Response()


@pytest.fixture
def fake_session():
    return FakeSessionFactory()
