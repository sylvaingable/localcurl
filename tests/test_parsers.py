import pytest

from localcurl.parsers import CurlParsingError, curl_to_request


def test_simple_get():
    request = curl_to_request("curl http://example.com")
    assert request.method == "get"
    assert request.url == "http://example.com"
    assert not request.data


def test_post_with_data():
    request = curl_to_request('curl -d "name=test" http://example.com')
    assert request.method == "post"
    assert request.url == "http://example.com"
    assert request.data == "name=test"


def test_custom_method():
    request = curl_to_request('curl -X PUT -d "name=test" http://example.com')
    assert request.method == "put"
    assert request.url == "http://example.com"
    assert request.data == "name=test"


def test_headers():
    request = curl_to_request(
        'curl -H "Content-Type: application/json" -H "Authorization: Bearer token123" http://example.com'
    )
    assert request.headers["Content-Type"] == "application/json"
    assert request.headers["Authorization"] == "Bearer token123"


def test_cookie():
    request = curl_to_request('curl -b "session=abc123; user=john" http://example.com')
    assert request.cookies["session"] == "abc123"
    assert request.cookies["user"] == "john"


def test_cookie_header():
    request = curl_to_request(
        'curl -H "Cookie: session=abc123; user=john" http://example.com'
    )
    assert request.cookies["session"] == "abc123"
    assert request.cookies["user"] == "john"


def test_auth():
    request = curl_to_request("curl --user john:pass123 http://example.com")
    assert request.auth == ("john", "pass123")


def test_data_binary():
    request = curl_to_request('curl --data-binary "raw data" http://example.com')
    assert request.method == "post"
    assert request.data == "raw data"


def test_invalid_command():
    with pytest.raises(CurlParsingError):
        curl_to_request("curl --invalid-flag http://example.com")


def test_complex_request():
    cmd = """curl -X POST -H "Content-Type: application/json" -H "Authorization: Bearer token123" -b "session=abc" --data-raw '{"key":"value"}' http://example.com"""
    request = curl_to_request(cmd)

    assert request.method == "post"
    assert request.url == "http://example.com"
    assert request.data == '{"key":"value"}'
    assert request.headers["Content-Type"] == "application/json"
    assert request.headers["Authorization"] == "Bearer token123"
    assert request.cookies["session"] == "abc"


def test_multiple_cookies():
    request = curl_to_request(
        'curl -b "session=abc123" -b "user=john" -b "token=xyz789" http://example.com'
    )
    assert request.cookies["session"] == "abc123"
    assert request.cookies["user"] == "john"
    assert request.cookies["token"] == "xyz789"


def test_multiple_cookies_with_headers():
    request = curl_to_request(
        'curl -b "session=abc123" -H "Cookie: user=john" -b "token=xyz789" http://example.com'
    )
    assert request.cookies["session"] == "abc123"
    assert request.cookies["user"] == "john"
    assert request.cookies["token"] == "xyz789"
