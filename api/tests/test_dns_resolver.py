import asyncio
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock

from providers.dns_resolver import DNSResolverPool


class DNSResolverPoolTest(IsolatedAsyncioTestCase):
    def setUp(self):
        self.pool = DNSResolverPool()
        self.release = asyncio.Event()
        self.started = asyncio.Event()
        self.stopped = asyncio.Event()

        async def query(*args, **kwargs):
            self.started.set()
            try:
                await self.release.wait()
                return "answer"
            finally:
                self.stopped.set()

        self.upstream = AsyncMock(side_effect=query)
        self.pool.resolvers[0][1].resolve = self.upstream

    async def test_shared_query_survives_one_cancel_and_is_not_cached(self):
        first = asyncio.create_task(self.pool.resolve("example.com", "A"))
        await self.started.wait()
        second = asyncio.create_task(self.pool.resolve("example.com", "A"))
        await asyncio.sleep(0)
        first.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await first
        self.assertFalse(self.stopped.is_set())
        self.release.set()
        self.assertEqual(await second, ["answer"])
        self.assertEqual(self.upstream.await_count, 1)
        await self.pool.resolve("example.com", "A")
        self.assertEqual(self.upstream.await_count, 2)

    async def test_final_waiter_cancels_upstream_and_next_call_starts_fresh(self):
        waiter = asyncio.create_task(self.pool.resolve("example.com", "A"))
        await self.started.wait()
        waiter.cancel()
        with self.assertRaises(asyncio.CancelledError):
            await waiter
        await asyncio.wait_for(self.stopped.wait(), 1)
        self.release.set()
        self.assertEqual(await self.pool.resolve("example.com", "A"), ["answer"])
        self.assertEqual(self.upstream.await_count, 2)

    async def test_distinct_names_types_and_lifetimes_do_not_share(self):
        self.release.set()
        await asyncio.gather(
            self.pool.resolve("example.com", "A"),
            self.pool.resolve("example.com", "AAAA"),
            self.pool.resolve("example.com", "A", lifetime=1),
            self.pool.resolve("example.org", "A"),
        )
        self.assertEqual(self.upstream.await_count, 4)
