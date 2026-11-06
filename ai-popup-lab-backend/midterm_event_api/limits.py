"""
Identifies the visitor for the persona chat's user limiting.

The limiting itself (one request at a time, daily limit per visitor, daily limit across
all visitors) lives in chat_guard.py. This file only works out who the visitor is.
"""

from fastapi import Request


def client_key(request: Request) -> str:
    # Azure App Service puts the visitor's IP first in X-Forwarded-For, sometimes with a port
    # ("1.2.3.4:56789") that changes per connection, so the port is dropped
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        ip = forwarded_for.split(",")[0].strip()
        if ip.startswith("["):
            return ip[1:].split("]")[0]
        if ip.count(":") == 1:
            return ip.split(":")[0]
        return ip
    return request.client.host if request.client else "unknown"
