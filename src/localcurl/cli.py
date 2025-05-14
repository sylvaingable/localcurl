from __future__ import annotations

import argparse
import shlex
import sys
from typing import Any, Callable, Protocol, TextIO
from urllib.parse import urlsplit, urlunsplit

import pyperclip
import requests
from requests.models import PreparedRequest, Response

from . import parsers


class ClipboardInterface(Protocol):
    def paste(self) -> str: ...


class SessionLike(Protocol):
    verify: bool | str | None

    def __enter__(self) -> SessionLike: ...
    def __exit__(self, *args: Any) -> None: ...
    def send(self, request: PreparedRequest) -> Response: ...


def main(
    cmd_line_args: list[str] = sys.argv,
    stdin: TextIO = sys.stdin,
    clipboard: ClipboardInterface = pyperclip,
    session_factory: Callable[[], SessionLike] = requests.Session,
) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "local_addr",
        metavar="addrport",
        help="The local address to send the request, e.g. http://localhost:8080",
    )
    parser.add_argument(
        "--no-verify",
        action="store_true",
        help="Disable SSL certificate verification",
    )
    parser.add_argument(
        "--keep-host-cookie-prefix",
        action="store_true",
        help="Prevent stripping __Host- prefix from cookies",
    )
    parser.add_argument(
        "curl_command",
        nargs=argparse.REMAINDER,
        help="The curl command to parse (reads from stdin if not provided)",
    )
    args = parser.parse_args(args=cmd_line_args[1:])

    if args.curl_command:
        curl_command = shlex.join(args.curl_command)
    else:
        # No curl command was provided as arguments, try to read from stdin or the
        # clipboard.
        curl_command = clipboard.paste() if stdin.isatty() else stdin.read()

    # If the curl command has was split across multiple lines (with trailing
    # backslashes) it ends having "\\\n" characters in it that would cause the curl
    # command parser to fail. We need to remove them.
    curl_command = curl_command.replace("\\\n", "")
    curl_command = curl_command.replace("\\\r\n", "")

    try:
        request = parsers.curl_to_request(curl_command)
    except ValueError as e:
        print(f"Error: {e}", f"{curl_command}", file=sys.stderr)
        return 1

    # Replace the original address with the local one.
    request.url = replace_address(request.url, args.local_addr)

    # Strip the __Host- prefix from cookies unless instructed otherwise.
    if args.keep_host_cookie_prefix is False:
        request.cookies = {
            k[len("__Host-") :] if k.startswith("__Host-") else k: v
            for k, v in request.cookies.items()
        }

    with session_factory() as session:
        session.verify = not args.no_verify
        response = session.send(request.prepare())
    print(response.text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())


def replace_address(url: str, local_addr: str) -> str:
    """
    Replace the scheme, host and port in the URL with the local address ones.
    """
    original_parts = urlsplit(url)
    replacement_parts = urlsplit(local_addr)
    new_parts = (
        replacement_parts.scheme,
        replacement_parts.netloc,
        original_parts.path,
        original_parts.query,
        original_parts.fragment,
    )

    return urlunsplit(new_parts)
