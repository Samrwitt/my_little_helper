"""SSRF protection and URL validation for scrapers."""

from __future__ import annotations

import ipaddress
import socket
from urllib.parse import urlparse

BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "metadata",
}

BLOCKED_NETWORKS = [
    ipaddress.ip_network("0.0.0.0/8"),
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]


class UnsafeURLError(ValueError):
    pass


def normalize_url(url: str) -> str:
    parsed = urlparse(url.strip())
    if not parsed.scheme:
        url = "https://" + url
        parsed = urlparse(url)
    # Drop fragment and normalize trailing slash lightly
    netloc = parsed.netloc.lower()
    path = parsed.path.rstrip("/") or ""
    query = f"?{parsed.query}" if parsed.query else ""
    return f"{parsed.scheme.lower()}://{netloc}{path}{query}"


def validate_public_url(url: str) -> str:
    """Validate URL is http(s) and does not target private/metadata hosts."""
    parsed = urlparse(url.strip())
    if parsed.scheme not in {"http", "https"}:
        raise UnsafeURLError("Only http and https URLs are allowed")
    hostname = parsed.hostname
    if not hostname:
        raise UnsafeURLError("URL missing hostname")
    host_lower = hostname.lower().rstrip(".")
    if host_lower in BLOCKED_HOSTNAMES or host_lower.endswith(".local"):
        raise UnsafeURLError(f"Blocked hostname: {hostname}")
    # Literal IP
    try:
        ip = ipaddress.ip_address(hostname)
        for net in BLOCKED_NETWORKS:
            if ip in net:
                raise UnsafeURLError(f"Blocked private IP: {hostname}")
        return url
    except ValueError:
        pass

    # Resolve DNS and check all addresses
    try:
        infos = socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        raise UnsafeURLError(f"Cannot resolve hostname: {hostname}") from exc
    for info in infos:
        ip = ipaddress.ip_address(info[4][0])
        for net in BLOCKED_NETWORKS:
            if ip in net:
                raise UnsafeURLError(f"Hostname resolves to private IP: {hostname}")
    return url
