import asyncio
import json
from collections import Counter
from unittest import IsolatedAsyncioTestCase

import httpx

from config import settings
from core.models import ProviderOutcome
from main import app
from services.lookup import LookupService, Section


class SectionRetryTest(IsolatedAsyncioTestCase):
    async def test_retry_after_stream(self):
        async with (
            app.router.lifespan_context(app),
            httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app), base_url="http://test"
            ) as client,
        ):
            original_service = app.state.lookup
            calls = Counter()

            def provider(key):
                async def run(domain):
                    self.assertEqual(domain, "example.com")
                    calls[key] += 1
                    if key == "rdap" and calls[key] == 1:
                        raise TimeoutError
                    if key == "email_security":
                        return ProviderOutcome(
                            "mock",
                            {
                                "spf": {"status": "found"},
                                "errors": ["DMARC unavailable"],
                            },
                            partial=True,
                        )
                    return ProviderOutcome("mock", {})

                return run

            sections = {
                key: Section("mock", 1, provider(key), 0)
                for key in (
                    "dns",
                    "dnssec",
                    "rdap",
                    "subdomains",
                    "ip",
                    "exposure",
                    "email_security",
                )
            }
            service = LookupService(
                original_service._client,
                original_service._resolver,
                settings.max_concurrent_lookups,
                sections=sections,
            )
            app.state.lookup = service

            base = "/api/v1/domain/Example.com"
            stream = await client.get(base + "/stream")
            events = [
                json.loads(line[6:])
                for line in stream.text.splitlines()
                if line.startswith("data: ")
            ]
            self.assertEqual(events.pop(), {"domain": "example.com", "sections": 7})
            sections = {event["section"]: event for event in events}
            self.assertEqual(sections["rdap"]["status"], "timeout")
            self.assertTrue(sections["rdap"]["retryable"])
            self.assertTrue(sections["email_security"]["retryable"])
            self.assertEqual(
                sections["email_security"]["data"]["spf"]["status"], "found"
            )

            retry = await client.get(base + "/sections/rdap")
            self.assertEqual(retry.json()["status"], "ok")
            self.assertFalse(retry.json()["retryable"])
            self.assertEqual(retry.headers["cache-control"], "no-store")
            self.assertEqual(
                calls,
                Counter(
                    dns=1,
                    dnssec=1,
                    rdap=2,
                    subdomains=1,
                    ip=1,
                    email_security=1,
                    exposure=1,
                ),
            )
            self.assertEqual(
                (await client.get(base + "/sections/unknown")).status_code, 404
            )
            self.assertEqual(
                (await client.get("/api/v1/domain/invalid/sections/ip")).status_code,
                422,
            )
            self.assertEqual(len((await client.get(base)).json()["sections"]), 7)

            service.slots = asyncio.Semaphore(0)
            busy = await client.get(base + "/sections/dns")
            self.assertEqual(busy.status_code, 503)
            self.assertEqual(busy.headers["retry-after"], "2")

    async def test_only_complete_results_are_cached(self):
        calls = 0

        async def run(domain):
            nonlocal calls
            calls += 1
            return ProviderOutcome("mock", {"records": [calls]}, partial=calls == 1)

        lookup = LookupService(
            None, None, 1, sections={"dns": Section("mock", 1, run, 60)}
        )
        first, second, third = [
            await lookup.lookup_section("example.com", "dns") for _ in range(3)
        ]
        self.assertEqual(first.status, "ok")
        self.assertTrue(first.retryable)
        self.assertEqual(first.data, {"records": [1]})
        self.assertFalse(second.retryable)
        self.assertEqual(second.data, {"records": [2]})
        self.assertEqual(second, third)
        self.assertEqual(calls, 2)
