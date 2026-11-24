import json
from unittest import IsolatedAsyncioTestCase

import httpx

from providers.dnssec import lookup


class DNSSECTest(IsolatedAsyncioTestCase):
    async def _lookup(self, payload):
        def respond(request):
            self.assertEqual(request.url.host, "cloudflare-dns.com")
            self.assertEqual(request.url.params["type"], "DNSKEY")
            self.assertEqual(request.url.params["do"], "true")
            return httpx.Response(200, content=json.dumps(payload))

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            return await lookup("example.com", client)

    async def test_secure_dnskey_answer(self):
        outcome = await self._lookup(
            {
                "Status": 0,
                "AD": True,
                "Answer": [{"type": 48}, {"type": 48}, {"type": 46}],
            }
        )
        data = outcome.data
        source = outcome.source

        self.assertEqual(source, "Cloudflare DNSSEC validation")
        self.assertEqual(data["status"], "secure")
        self.assertEqual(data["dnskey_count"], 2)

    async def test_unsigned_domain(self):
        outcome = await self._lookup({"Status": 0, "AD": True})
        data = outcome.data

        self.assertEqual(data["status"], "unsigned")
        self.assertEqual(data["dnskey_count"], 0)

    async def test_dnssec_validation_failure(self):
        outcome = await self._lookup(
            {"Status": 2, "Comment": ["EDE: 6 (DNSSEC Bogus)"]}
        )
        data = outcome.data

        self.assertEqual(data["status"], "bogus")

    async def test_nonexistent_domain(self):
        outcome = await self._lookup({"Status": 3})
        data = outcome.data

        self.assertEqual(data["status"], "not_found")
