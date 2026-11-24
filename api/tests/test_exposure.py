import json
from unittest import IsolatedAsyncioTestCase

import httpx

from providers.dns_resolver import DNSResolverPool
from providers.exposure import lookup


class _Record:
    def __init__(self, value):
        self.value = value

    def to_text(self):
        return self.value


class _Answer(list):
    rrset = object()


class _Resolver:
    """Minimal stand-in for DNSResolverPool with fixed A/AAAA answers."""

    is_failure = staticmethod(DNSResolverPool.is_failure)

    def __init__(self, a=(), aaaa=()):
        self.answers = {"A": list(a), "AAAA": list(aaaa)}

    async def resolve(self, name, record_type, *, lifetime=4.0):
        return [_Answer(_Record(v) for v in self.answers[record_type])]


class ExposureTest(IsolatedAsyncioTestCase):
    async def _lookup(self, resolver, handler):
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            return await lookup("example.com", resolver, client)

    async def test_returns_ports_cpes_and_valid_cves_only(self):
        def respond(request):
            self.assertEqual(request.url.host, "internetdb.shodan.io")
            self.assertEqual(request.url.path, "/93.184.216.34")
            return httpx.Response(
                200,
                content=json.dumps(
                    {
                        "ip": "93.184.216.34",
                        "ports": [443, 80, True, 70000],
                        "cpes": ["cpe:/a:nginx:nginx:1.18.0", 5],
                        "hostnames": ["example.com"],
                        "tags": ["cdn", "<script>"],
                        "vulns": ["CVE-2021-23017", "not-a-cve"],
                    }
                ),
            )

        outcome = await self._lookup(_Resolver(a=["93.184.216.34"]), respond)
        data = outcome.data
        source = outcome.source

        self.assertEqual(source, "Shodan InternetDB")
        host = data["hosts"][0]
        self.assertTrue(host["found"])
        self.assertEqual(host["ports"], [80, 443])
        self.assertEqual(host["cpes"], ["cpe:/a:nginx:nginx:1.18.0"])
        self.assertEqual(host["tags"], ["cdn"])
        self.assertEqual(host["vulns"], ["CVE-2021-23017"])
        self.assertEqual(data["errors"], [])

    async def test_404_means_no_data_not_an_error(self):
        outcome = await self._lookup(
            _Resolver(a=["93.184.216.34"]), lambda request: httpx.Response(404)
        )
        data = outcome.data

        self.assertFalse(data["hosts"][0]["found"])
        self.assertEqual(data["errors"], [])

    async def test_private_addresses_are_never_sent(self):
        def respond(request):
            self.fail("private address must not be queried")

        outcome = await self._lookup(_Resolver(a=["10.0.0.1", "127.0.0.1"]), respond)
        data = outcome.data

        self.assertEqual(data["hosts"], [])

    async def test_partial_failure_is_reported(self):
        def respond(request):
            if request.url.path.endswith("93.184.216.34"):
                return httpx.Response(200, content=json.dumps({"ports": [443]}))
            return httpx.Response(500)

        outcome = await self._lookup(_Resolver(a=["93.184.216.34", "8.8.8.8"]), respond)
        data = outcome.data

        self.assertEqual(len(data["hosts"]), 2)
        self.assertEqual(len(data["errors"]), 1)

    async def test_all_failures_raise(self):
        with self.assertRaises(httpx.TransportError):
            await self._lookup(
                _Resolver(a=["93.184.216.34"]), lambda request: httpx.Response(500)
            )

    async def test_host_count_is_capped(self):
        addresses = [f"8.8.{i}.8" for i in range(15)]

        outcome = await self._lookup(
            _Resolver(a=addresses), lambda request: httpx.Response(404)
        )
        data = outcome.data

        self.assertEqual(len(data["hosts"]), 10)
        self.assertTrue(data["truncated"])
