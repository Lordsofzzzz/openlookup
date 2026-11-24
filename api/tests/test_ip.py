import ipaddress
from types import SimpleNamespace
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, call, patch

import dns.exception
import dns.resolver

from providers.ip import lookup


class IPLookupTest(IsolatedAsyncioTestCase):
    async def test_keeps_networks_grouped_and_maps_asns_to_each_address(self):
        addresses = [
            ipaddress.ip_address("8.8.8.8"),
            ipaddress.ip_address("1.1.1.1"),
        ]
        google = {
            "asn": "AS15169",
            "prefix": "8.8.8.0/24",
            "country": "US",
            "registry": "arin",
            "allocated": "2012-07-12",
            "name": "Google LLC, US",
        }
        cloudflare = {
            "asn": "AS13335",
            "prefix": "1.1.1.0/24",
            "country": "AU",
            "registry": "apnic",
            "allocated": "2011-01-01",
            "name": "Cloudflare, Inc., US",
        }

        with (
            patch(
                "providers.ip.resolve_public_addresses",
                new=AsyncMock(return_value=addresses),
            ),
            patch(
                "providers.ip._asn_record",
                new=AsyncMock(side_effect=[([google], False), ([cloudflare], False)]),
            ),
        ):
            outcome = await lookup("example.com", resolver=None)
            data = outcome.data

        self.assertEqual(data["addresses"], ["8.8.8.8", "1.1.1.1"])
        self.assertEqual(data["networks"], [google, cloudflare])
        self.assertEqual(
            data["address_asns"],
            [
                {
                    "ip": "8.8.8.8",
                    "asns": [{"asn": "AS15169", "name": "Google LLC, US"}],
                },
                {
                    "ip": "1.1.1.1",
                    "asns": [{"asn": "AS13335", "name": "Cloudflare, Inc., US"}],
                },
            ],
        )

    async def test_ip_without_asn_has_an_empty_mapping(self):
        address = ipaddress.ip_address("8.8.8.8")

        with (
            patch(
                "providers.ip.resolve_public_addresses",
                new=AsyncMock(return_value=[address]),
            ),
            patch(
                "providers.ip._asn_record",
                new=AsyncMock(return_value=([], False)),
            ),
        ):
            outcome = await lookup("example.com", resolver=None)
            data = outcome.data

        self.assertEqual(data["address_asns"], [{"ip": "8.8.8.8", "asns": []}])

    async def test_failed_asn_query_is_reported_as_partial_data(self):
        address = ipaddress.ip_address("57.144.242.1")

        with (
            patch(
                "providers.ip.resolve_public_addresses",
                new=AsyncMock(return_value=[address]),
            ),
            patch(
                "providers.ip._asn_record",
                new=AsyncMock(return_value=([], True)),
            ),
        ):
            outcome = await lookup("facebook.com", resolver=None)
            data = outcome.data

        self.assertEqual(data["errors"], ["Some ASN lookups failed."])
        self.assertEqual(data["address_asns"], [{"ip": "57.144.242.1", "asns": []}])


class ASNRetryTest(IsolatedAsyncioTestCase):
    origin = "8.8.8.8.origin.asn.cymru.com"
    name = "AS15169.asn.cymru.com"

    @staticmethod
    def txt(value):
        class Answer(list):
            rrset = True

        return Answer([SimpleNamespace(strings=[value.encode()])])

    async def lookup_with(self, names, replies):
        query = AsyncMock(side_effect=replies)
        with (
            patch(
                "providers.ip.resolve_public_addresses",
                new=AsyncMock(return_value=[ipaddress.ip_address("8.8.8.8")]),
            ),
            patch(
                "providers.ip._system_resolver",
                return_value=SimpleNamespace(resolve=query),
            ),
        ):
            outcome = await lookup("example.com", resolver=None)
            data = outcome.data
        self.assertEqual(
            query.await_args_list,
            [
                call(name, "TXT", search=False, raise_on_no_answer=False)
                for name in names
            ],
        )
        return data

    async def test_transient_origin_timeout_retries_once_then_returns_network(self):
        data = await self.lookup_with(
            [self.origin, self.origin, self.name],
            [
                dns.exception.Timeout(),
                self.txt("15169 | 8.8.8.0/24 | US | arin | 2012-07-12"),
                self.txt("15169 | US | arin | 2012-07-12 | Google LLC"),
            ],
        )
        self.assertEqual(data["networks"][0]["name"], "Google LLC")
        self.assertNotIn("errors", data)

    async def test_missing_origin_is_complete_without_retry(self):
        data = await self.lookup_with([self.origin], [dns.resolver.NXDOMAIN()])
        self.assertEqual(data["networks"], [])
        self.assertNotIn("errors", data)

    async def test_exhausted_name_query_preserves_origin_record(self):
        data = await self.lookup_with(
            [self.origin, self.name, self.name],
            [
                self.txt("15169 | 8.8.8.0/24 | US | arin | 2012-07-12"),
                dns.exception.Timeout(),
                dns.exception.Timeout(),
            ],
        )
        self.assertEqual(data["errors"], ["Some ASN lookups failed."])
        self.assertEqual(
            data["address_asns"],
            [{"ip": "8.8.8.8", "asns": [{"asn": "AS15169", "name": None}]}],
        )
        self.assertEqual(data["networks"][0]["prefix"], "8.8.8.0/24")
