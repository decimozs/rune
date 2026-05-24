import pytest
from unittest.mock import patch

from services.exceptions import OCRValidationError


class TestValidateUrl:
    def _call(self, url):
        from services.url_guard import validate_url
        validate_url(url)

    @patch("services.url_guard.socket.gethostbyname")
    def test_valid_https_passes(self, mock_dns):
        mock_dns.return_value = "93.184.216.34"
        self._call("https://example.com/page")

    @patch("services.url_guard.socket.gethostbyname")
    def test_valid_http_passes(self, mock_dns):
        mock_dns.return_value = "93.184.216.34"
        self._call("http://example.com")

    @patch("services.url_guard.socket.gethostbyaddr")
    def test_valid_public_ip_passes(self, mock_rdns):
        mock_rdns.return_value = ("example.com", [], [])
        self._call("http://93.184.216.34/path")

    @pytest.mark.parametrize("url", [
        "file:///etc/passwd",
        "ftp://files.example.com",
        "data:text/plain,hello",
    ])
    def test_bad_scheme_fails(self, url):
        with pytest.raises(OCRValidationError, match="Only http/https"):
            self._call(url)

    def test_no_scheme_fails(self):
        with pytest.raises(OCRValidationError, match="must have a scheme"):
            self._call("example.com")

    def test_empty_url_fails(self):
        with pytest.raises(OCRValidationError):
            self._call("")

    @pytest.mark.parametrize("url,msg", [
        ("http://localhost:8080/admin", "Local/private host not allowed"),
        ("http://127.0.0.1:3000",  "Local/private host not allowed"),
        ("http://127.0.0.1",       "Local/private host not allowed"),
        ("http://0.0.0.0",         "Local/private host not allowed"),
        ("http://[::1]",           "Local/private host not allowed"),
    ])
    def test_loopback_and_zero_fails(self, url, msg):
        with pytest.raises(OCRValidationError, match=msg):
            self._call(url)

    @pytest.mark.parametrize("url", [
        "http://10.0.0.1",
        "http://10.255.255.255",
        "http://192.168.1.1/dashboard",
        "http://172.16.0.1",
        "http://172.31.255.255",
    ])
    def test_private_ip_fails(self, url):
        with pytest.raises(OCRValidationError, match="Private IP"):
            self._call(url)

    @pytest.mark.parametrize("url", [
        "http://169.254.1.1",
        "http://169.254.255.255",
    ])
    def test_link_local_fails(self, url):
        with pytest.raises(OCRValidationError, match="Link-local"):
            self._call(url)

    def test_broadcast_fails(self):
        with pytest.raises(OCRValidationError, match="Broadcast"):
            self._call("http://255.255.255.255")

    def test_zero_prefix_fails(self):
        with pytest.raises(OCRValidationError, match="Invalid address"):
            self._call("http://0.1.2.3")

    @patch("services.url_guard.socket.gethostbyname")
    def test_dns_to_private_fails(self, mock_dns):
        mock_dns.return_value = "10.0.0.5"
        with pytest.raises(OCRValidationError, match="Private IP"):
            self._call("http://internal.corp")

    @patch("services.url_guard.socket.gethostbyname")
    def test_dns_to_public_passes(self, mock_dns):
        mock_dns.return_value = "93.184.216.34"
        self._call("http://example.com")

    @patch("services.url_guard.socket.gethostbyname")
    def test_dns_to_localhost_fails(self, mock_dns):
        mock_dns.return_value = "127.0.0.1"
        with pytest.raises(OCRValidationError, match="Private IP"):
            self._call("http://malicious.com")

    def test_exceeds_max_length(self):
        long = "http://a.b/" + "x" * 3000
        with pytest.raises(OCRValidationError, match="exceeds maximum length"):
            self._call(long)

    @patch("services.url_guard.settings.url_blocked_domains", "bad-site.com")
    def test_blocked_domain_fails(self):
        with pytest.raises(OCRValidationError, match="Domain is blocked"):
            self._call("http://bad-site.com")

    @patch("services.url_guard.settings.url_blocked_domains", "bad-site.com")
    @patch("services.url_guard.socket.gethostbyname")
    def test_subdomain_of_blocked_not_blocked(self, mock_dns):
        mock_dns.return_value = "93.184.216.34"
        self._call("http://sub.bad-site.com")

    @patch("services.url_guard.settings.company_domains_only", True)
    @patch("services.url_guard.settings.url_allowed_domains", "exist.com")
    def test_not_in_allowlist_fails(self):
        with pytest.raises(OCRValidationError, match="not in company allowlist"):
            self._call("http://evil.com")

    @patch("services.url_guard.settings.company_domains_only", True)
    @patch("services.url_guard.settings.url_allowed_domains", "exist.com")
    @patch("services.url_guard.socket.gethostbyname")
    def test_in_allowlist_passes(self, mock_dns):
        mock_dns.return_value = "93.184.216.34"
        self._call("http://docs.exist.com")

    @patch("services.url_guard.settings.company_domains_only", True)
    @patch("services.url_guard.settings.url_allowed_domains", "exist.com")
    @patch("services.url_guard.socket.gethostbyname")
    def test_allowlist_with_dns_to_public_passes(self, mock_dns, *_):
        mock_dns.return_value = "93.184.216.34"
        self._call("http://exist.com")

    @patch("services.url_guard.socket.gethostbyname")
    def test_url_with_trailing_dot_hostname(self, mock_dns):
        mock_dns.return_value = "93.184.216.34"
        self._call("http://example.com./path")


class TestAuth:
    async def _call(self, key=None):
        from services.auth import verify_api_key
        return await verify_api_key(key)

    @patch("services.auth.settings.api_keys", "#")
    async def test_auth_disabled_returns_none(self):
        assert await self._call(None) is None
        assert await self._call("some-key") is None

    @patch("services.auth.settings.api_keys", "sk-prod-abc")
    async def test_missing_key_returns_401(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await self._call(None)
        assert exc.value.status_code == 401

    @patch("services.auth.settings.api_keys", "sk-prod-abc")
    async def test_wrong_key_returns_401(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await self._call("sk-prod-wrong")
        assert exc.value.status_code == 401

    @patch("services.auth.settings.api_keys", "sk-prod-abc")
    async def test_valid_key_returns_key_name(self):
        name = await self._call("sk-prod-abc")
        assert name == "unknown"

    @patch("services.auth.settings.api_keys", "sk-abc=alice,sk-def=bob")
    async def test_valid_key_with_name_returns_name(self):
        assert await self._call("sk-abc") == "alice"
        assert await self._call("sk-def") == "bob"

    @patch("services.auth.settings.api_keys", "sk-abc=alice,sk-def=bob")
    async def test_valid_key_from_multi_returns_name(self):
        assert await self._call("sk-def") == "bob"

    @patch("services.auth.settings.api_keys", "sk-abc=alice,sk-def=bob")
    async def test_key_not_in_list_returns_401(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc:
            await self._call("sk-nonexistent")
        assert exc.value.status_code == 401

    @patch("services.auth.settings.api_keys", "sk-abc=alice,sk-def=bob")
    async def test_empty_key_returns_401(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            await self._call("")
