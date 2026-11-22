import ipaddress
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch

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
                new=AsyncMock(side_effect=[[google], [cloudflare]]),
            ),
        ):
            _, data = await lookup("example.com", resolver=None)

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
            patch("providers.ip._asn_record", new=AsyncMock(return_value=[])),
        ):
            _, data = await lookup("example.com", resolver=None)

        self.assertEqual(data["address_asns"], [{"ip": "8.8.8.8", "asns": []}])
