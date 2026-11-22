import json
from unittest import IsolatedAsyncioTestCase

import httpx

from providers.dnssec import lookup


class DNSSECTest(IsolatedAsyncioTestCase):
    async def _lookup(self, payload):
        def respond(request):
            self.assertEqual(request.url.host, "dns.google")
            self.assertEqual(request.url.params["type"], "DNSKEY")
            self.assertEqual(request.url.params["do"], "true")
            return httpx.Response(200, content=json.dumps(payload))

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            return await lookup("example.com", client)

    async def test_secure_dnskey_answer(self):
        source, data = await self._lookup(
            {
                "Status": 0,
                "AD": True,
                "Answer": [{"type": 48}, {"type": 48}, {"type": 46}],
            }
        )

        self.assertEqual(source, "Google Public DNS DNSSEC validation")
        self.assertEqual(data["status"], "secure")
        self.assertEqual(data["dnskey_count"], 2)

    async def test_unsigned_domain(self):
        _, data = await self._lookup({"Status": 0, "AD": True})

        self.assertEqual(data["status"], "unsigned")
        self.assertEqual(data["dnskey_count"], 0)

    async def test_dnssec_validation_failure(self):
        _, data = await self._lookup(
            {"Status": 2, "Comment": ["EDE: 6 (DNSSEC Bogus)"]}
        )

        self.assertEqual(data["status"], "bogus")

    async def test_nonexistent_domain(self):
        _, data = await self._lookup({"Status": 3})

        self.assertEqual(data["status"], "not_found")
