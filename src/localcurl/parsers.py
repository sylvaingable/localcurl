import argparse
import contextlib
import io
import re
import shlex
from http import cookies

import requests

parser = argparse.ArgumentParser()
parser.add_argument("command")  # placeholder for the curl command itself
parser.add_argument("url")
parser.add_argument("-d", "--data")
parser.add_argument("--data-binary", "--data-raw", default=None)
parser.add_argument("-X", "--request", default="")
parser.add_argument("-b", "--cookie", action="append", default=[])
parser.add_argument("-H", "--header", action="append", default=[])
parser.add_argument("--user", "-u", default=())
# Common optional curl arguments that will be ignored
parser.add_argument("-i", "--show-headers", "--include", action="store_true")
parser.add_argument("-k", "--insecure", action="store_true")
parser.add_argument("-s", "--silent", action="store_true")
parser.add_argument("--compressed", action="store_true")


def curl_to_request(curl_command: str) -> requests.Request:
    method = "get"
    tokens = shlex.split(curl_command)

    # argparse prints an error message and calls sys.exit() on failure. We need to catch
    # SystemExit exceptions to detect parsing errors and must capture the output to
    # avoid printing it to stdout.
    with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(
        io.StringIO()
    ):
        try:
            parsed_args = parser.parse_args(tokens)
        except SystemExit:
            raise ValueError("Failed to parse curl command. Please verify the syntax.")

    post_data = parsed_args.data or parsed_args.data_binary
    if post_data:
        method = "post"

    if parsed_args.request:
        method = parsed_args.request.lower()

    cookies_dict = {}
    quoted_headers = {}

    for cookie_str in parsed_args.cookie:
        cookie = cookies.SimpleCookie(cookie_str)
        for key in cookie:
            cookies_dict[key] = cookie[key].value

    for curl_header in parsed_args.header:
        if curl_header.startswith(":"):
            occurrence = [m.start() for m in re.finditer(":", curl_header)]
            header_key, header_value = (
                curl_header[: occurrence[1]],
                curl_header[occurrence[1] + 1 :],
            )
        else:
            header_key, header_value = curl_header.split(":", 1)

        # Cookies can also be passed as headers
        if header_key.lower().strip("$") == "cookie":
            cookie = cookies.SimpleCookie(header_value)
            for key in cookie:
                cookies_dict[key] = cookie[key].value
        else:
            quoted_headers[header_key] = header_value.strip()

    user = parsed_args.user
    if parsed_args.user:
        user = tuple(user.split(":"))

    return requests.Request(
        method=method,
        url=parsed_args.url,
        data=post_data,
        headers=quoted_headers,
        cookies=cookies_dict,
        auth=user,
    )
