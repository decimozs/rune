"""SSRF protection layer for URL and HTML source endpoints.

Validates URLs before any network call reaches Gotenberg or external
hosts. Checks happen in three stages:

1. String-level checks (scheme, length, domain lists)
2. DNS resolution (domain -> IP, catch private IPs behind DNS)
3. Reverse DNS (catch domains that resolve to loopback)

All checks throw OCRValidationError which maps to HTTP 400.
"""

import ipaddress
import logging
import re
import socket
from urllib.parse import urlparse

from config import settings
from services.exceptions import OCRValidationError
from services.log_ctx import sanitize_url

logger = logging.getLogger(__name__)


def validate_url(url: str) -> None:
    """Verify a URL is safe to fetch.

    Rejects non-http/https schemes, private IPs (RFC 1918),
    loopback, link-local, multicast, broadcast, DNS-to-private,
    blocked domains, and URLs exceeding max length.

    Blocked URLs are logged with the reason for security auditing.
    """
    if len(url) > settings.url_max_length:
        logger.warning("Blocked URL (too long): len=%d", len(url))
        raise OCRValidationError("URL exceeds maximum length")

    parsed = urlparse(url)
    if not parsed.scheme:
        logger.warning("Blocked URL (no scheme): url=%s", sanitize_url(url))
        raise OCRValidationError("URL must have a scheme (http/https)")

    if parsed.scheme not in ("http", "https"):
        logger.warning("Blocked URL (bad scheme): scheme=%s", parsed.scheme)
        raise OCRValidationError(
            f"Only http/https URLs are allowed, got: {parsed.scheme}"
        )

    hostname = parsed.hostname or ""
    if not hostname:
        logger.warning("Blocked URL (no hostname): url=%s", sanitize_url(url))
        raise OCRValidationError("URL must have a hostname")

    if hostname.endswith("."):
        hostname = hostname[:-1]

    blocked = set(settings.url_blocked_domain_list)
    if hostname in blocked:
        logger.warning("Blocked URL (blocked domain): host=%s", hostname)
        raise OCRValidationError("Domain is blocked")

    if settings.company_domains_only:
        allowlist = settings.url_allowed_domain_list
        if not allowlist:
            logger.warning("Blocked URL (no allowlist): host=%s", hostname)
            raise OCRValidationError(
                "Company-domains-only mode enabled but no allowed domains configured"
            )
        if not any(hostname == d or hostname.endswith("." + d) for d in allowlist):
            logger.warning("Blocked URL (not in allowlist): host=%s", hostname)
            raise OCRValidationError("Domain not in company allowlist")

    _check_host(hostname)


# Quick string-level patterns for known-bad IPs. These catch the common
# cases before DNS resolution, which is an order of magnitude slower.
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
    """Two-stage host validation: string match then DNS resolution.

    Stage 1: Check hostname against bare-host blocklist and private IP
             patterns. Fast path — no network call.

    Stage 2: DNS-resolve the hostname and check the resolved IP against
             Python's ipaddress properties (private, loopback, etc.).

    Stage 3: Reverse-DNS the resolved IP to catch hosts that resolve to
             known-bad names. Failure is intentionally silent — a domain
             that can't be reverse-resolved is still allowed.
    """
    if hostname in _BARE_HOST_BLOCK:
        logger.warning("Blocked URL (bare host): host=%s", hostname)
        raise OCRValidationError("Local/private host not allowed")

    for pattern, msg in _PRIVATE_PATTERNS:
        if re.match(pattern, hostname):
            logger.warning(
                "Blocked URL (IP pattern): host=%s, reason=%s", hostname, msg
            )
            raise OCRValidationError(msg)

    ip_match = re.match(r"^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$", hostname)

    if ip_match:
        ip_str = hostname
    else:
        try:
            ip_str = socket.gethostbyname(hostname)
        except socket.gaierror:
            logger.warning("Blocked URL (DNS failure): host=%s", hostname)
            raise OCRValidationError("Could not resolve hostname") from None

    ip = ipaddress.ip_address(ip_str)
    if ip.is_private:
        logger.warning("Blocked URL (private IP): host=%s, ip=%s", hostname, ip_str)
        raise OCRValidationError("Private IP not allowed")
    if ip.is_loopback:
        logger.warning("Blocked URL (loopback): host=%s, ip=%s", hostname, ip_str)
        raise OCRValidationError("Loopback address not allowed")
    if ip.is_link_local:
        logger.warning("Blocked URL (link-local): host=%s, ip=%s", hostname, ip_str)
        raise OCRValidationError("Link-local address not allowed")
    if ip.is_multicast:
        logger.warning("Blocked URL (multicast): host=%s, ip=%s", hostname, ip_str)
        raise OCRValidationError("Multicast address not allowed")

    try:
        resolved = socket.gethostbyaddr(ip_str)[0] if not ip_match else hostname
        if resolved in _BARE_HOST_BLOCK:
            logger.warning(
                "Blocked URL (reverse DNS): host=%s, resolved=%s", hostname, resolved
            )
            raise OCRValidationError("Resolved to local/private host")
    except (socket.herror, socket.gaierror):
        pass
