# localcurl

A tool to replay remote curl requests locally for easier debugging and testing.

## Why use localcurl?

When debugging API issues or developing locally against a remote service, you often need to replay real requests from production or staging environments. `localcurl` makes it easy by automatically rewriting curl commands to point to your local service while preserving all headers, authentication, and other parameters.

## Installation

```bash
pip install localcurl
```
NB: supports Python 3.8+

## Usage

```bash
localcurl http://localhost:8080 curl https://api.example.com/endpoint
```
Or, as a shorthand:
```bash
lc http://localhost:8080 curl https://api.example.com/endpoint
```

The curl command can also be piped from stdin:
```bash
echo 'curl https://api.example.com/endpoint' | localcurl http://localhost:8080
```

Or read from the clipboard:
```bash
localcurl http://localhost:8080
```

## Options

- `addrport`: The local address to send the request to (e.g., `http://localhost:8080`)
- `--no-verify`: Disable server TLS certificate verification
- `--keep-host-cookie-prefix`: Prevent stripping `__Host-` prefix from cookies
- `curl_command`: The curl command to parse (reads from stdin/clipboard if not provided)

## Examples

Redirect an API request to your local service:
```bash
localcurl http://localhost:3000 'curl -H "Authorization: Bearer token123" https://api.example.com/users'
```

Keep host prefixes in cookies:
```bash
localcurl --keep-host-cookie-prefix http://localhost:8080 'curl --cookie "__Host-session=abc123" https://api.example.com/profile'
```

Ignore TLS verification for local development:
```bash
localcurl --no-verify https://localhost:8443 'curl https://api.example.com/secure-endpoint'
```