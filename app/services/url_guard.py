import ipaddress
import re
import socket
from urllib.parse import urlparse

from config import settings
from services.exceptions import OCRValidationError


def validate_url(url: str) -> None:
    if len(url) > settings.url_max_length:
        raise OCRValidationError("URL exceeds maximum length")

    parsed = urlparse(url)
    if not parsed.scheme:
        raise OCRValidationError("URL must have a scheme (http/https)")

    if parsed.scheme not in ("http", "https"):
        raise OCRValidationError(f"Only http/https URLs are allowed, got: {parsed.scheme}")

    hostname = parsed.hostname or ""
    if not hostname:
        raise OCRValidationError("URL must have a hostname")

    if hostname.endswith("."):
        hostname = hostname[:-1]

    blocked = set(settings.url_blocked_domain_list)
    if hostname in blocked:
        raise OCRValidationError("Domain is blocked")

    if settings.company_domains_only:
        allowlist = settings.url_allowed_domain_list
        if not allowlist:
            raise OCRValidationError("Company-domains-only mode enabled but no allowed domains configured")
        if not any(hostname == d or hostname.endswith("." + d) for d in allowlist):
            raise OCRValidationError("Domain not in company allowlist")

    _check_host(hostname)


_PRIVATE_PATTERNS = (
    (r"^127\.\d{1,3}\.\d{1,3}\.\d{1,3}$", "Loopback address"),
    (r"^0\.\d{1,3}\.\d{1,3}\.\d{1,3}$", "Invalid address (0.x.x.x)"),
    (r"^169\.254\.\d{1,3}\.\d{1,3}$", "Link-local address"),
    (r"^255\.255\.255\.255$", "Broadcast address"),
)

_BARE_HOST_BLOCK = {
    "localhost",
    "127.0.0.1",
    "0.0.0.0",
    "[::1]",
    "[::]",
    "::1",
    "::",
}


def _check_host(hostname: str) -> None:
    if hostname in _BARE_HOST_BLOCK:
        raise OCRValidationError("Local/private host not allowed")

    for pattern, msg in _PRIVATE_PATTERNS:
        if re.match(pattern, hostname):
            raise OCRValidationError(msg)

    ip_match = re.match(r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$", hostname)

    if ip_match:
        ip_str = hostname
    else:
        try:
            ip_str = socket.gethostbyname(hostname)
        except socket.gaierror:
            raise OCRValidationError("Could not resolve hostname")

    ip = ipaddress.ip_address(ip_str)
    if ip.is_private:
        raise OCRValidationError("Private IP not allowed")
    if ip.is_loopback:
        raise OCRValidationError("Loopback address not allowed")
    if ip.is_link_local:
        raise OCRValidationError("Link-local address not allowed")
    if ip.is_multicast:
        raise OCRValidationError("Multicast address not allowed")

    try:
        resolved = socket.gethostbyaddr(ip_str)[0] if not ip_match else hostname
        if resolved in _BARE_HOST_BLOCK:
            raise OCRValidationError("Resolved to local/private host")
    except (socket.herror, socket.gaierror):
        pass
