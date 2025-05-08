import argparse
import shlex
import sys
from urllib.parse import urlsplit, urlunsplit

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
    parsed_context = uncurl.parse_context(curl_command)._asdict()
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

    if not args.curl_command:
        # Read curl command from stdin if no command arguments provided
        curl_command = sys.stdin.read().strip()
    else:
        curl_command = shlex.join(args.curl_command)

    request = curl_to_request(curl_command=curl_command, local_addr=args.local_addr)

    with requests.Session() as session:
        session.verify = not args.no_verify
        response = session.send(request.prepare())
    print(response.text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
