import argparse
import contextlib
import io
import shlex
import sys
from urllib.parse import urlsplit, urlunsplit

import pyperclip
import requests

from . import parsers


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


def main() -> int:
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
    args = parser.parse_args()

    if args.curl_command:
        curl_command = shlex.join(args.curl_command)
    else:
        # No curl command was provided as arguments, try to read from stdin or the
        # clipboard.
        curl_command = pyperclip.paste() if sys.stdin.isatty() else sys.stdin.read()

    try:
        request = parsers.curl_to_request(curl_command)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    # Replace the original address with the local one.
    request.url = replace_address(request.url, args.local_addr)

    # Strip the __Host- prefix from cookies unless instructed otherwise.
    if args.keep_host_cookie_prefix is False:
        request.cookies = {
            k[len("__Host-") :] if k.startswith("__Host-") else k: v
            for k, v in request.cookies.items()
        }

    with requests.Session() as session:
        session.verify = not args.no_verify
        response = session.send(request.prepare())
    print(response.text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
