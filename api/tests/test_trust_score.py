from unittest import IsolatedAsyncioTestCase

import httpx

from providers.trust_score import LOOKUP_URL, lookup


class TrustScoreTest(IsolatedAsyncioTestCase):
    async def run_lookup(self, payload):
        def respond(request):
            self.assertEqual(request.method, "GET")
            self.assertEqual(str(request.url), LOOKUP_URL + "?domain=example.org")
            return httpx.Response(200, json=payload)

        async with httpx.AsyncClient(transport=httpx.MockTransport(respond)) as client:
            _, data = await lookup("example.org", client)
        return data

    async def test_unscored(self):
        self.assertEqual(await self.run_lookup({"scored": False}), {"scored": False})

    async def test_score_and_partial_signal(self):
        data = await self.run_lookup(
            {"score": 0, "signals": [{"label": "Security", "value": 0}]}
        )
        self.assertEqual(data["score"], 0)
        self.assertEqual(
            data["signals"], [{"label": "Security", "value": 0, "confidence": None}]
        )

    async def test_malformed_is_not_unscored(self):
        with self.assertRaises(KeyError):
            await self.run_lookup({})
