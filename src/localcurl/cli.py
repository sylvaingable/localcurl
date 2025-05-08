import argparse
import contextlib
import io
import shlex
import sys
from urllib.parse import urlsplit, urlunsplit

import pyperclip
import requests
import uncurl


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


def curl_to_request(curl_command: str, local_addr: str) -> requests.Request:
    """Convert a curl command to a requests.Request object."""
    # uncurl uses argparse to parse the curl command, which prints an error message and
    # calls sys.exit() on failure. We need to catch SystemExit exceptions to detect
    # parsing errors and must capture the output to avoid printing it to stdout.
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
        io.StringIO()
    ):
        try:
            parsed_context = uncurl.parse_context(curl_command)._asdict()
        except SystemExit:
            raise ValueError("Failed to parse curl command. Please verify the syntax.")

    parsed_context["url"] = replace_address(parsed_context["url"], local_addr)
    # Remove the 'verify' key if it exists as it's not handled at the request level but
    # at the session's one.
    parsed_context.pop("verify", None)
    return requests.Request(**parsed_context)


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
        request = curl_to_request(curl_command=curl_command, local_addr=args.local_addr)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1

    with requests.Session() as session:
        session.verify = not args.no_verify
        response = session.send(request.prepare())
    print(response.text)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
