import asyncio
from typing import Any

import dns.asyncresolver
import dns.exception
import dns.resolver

_RECORD_TYPES = ("A", "AAAA", "MX", "NS", "TXT", "CNAME")


def _value(record: Any, record_type: str) -> str:
    if record_type == "MX":
        return f"{record.preference} {record.exchange.to_text(omit_final_dot=True)}"
    if record_type == "NS":
        return record.target.to_text(omit_final_dot=True)
    if record_type == "CNAME":
        return record.target.to_text(omit_final_dot=True)
    if record_type == "TXT":
        return b"".join(record.strings).decode("utf-8", errors="replace")
    return record.to_text()


async def lookup(
    domain: str, resolver: dns.asyncresolver.Resolver
) -> tuple[str, dict[str, Any]]:
    async def query(record_type: str) -> tuple[str, list[dict[str, Any]] | Exception]:
        try:
            answer = await resolver.resolve(
                domain,
                record_type,
                lifetime=4.0,
                raise_on_no_answer=False,
                search=False,
            )
            records = []
            if answer.rrset is not None:
                ttl = int(answer.rrset.ttl)
                records = [
                    {
                        "type": record_type,
                        "name": domain,
                        "value": _value(record, record_type),
                        "ttl": ttl,
                    }
                    for record in answer
                ]
            return record_type, records
        except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
            return record_type, []
        except (dns.exception.Timeout, dns.resolver.NoNameservers) as exc:
            return record_type, exc

    results = await asyncio.gather(
        *(query(record_type) for record_type in _RECORD_TYPES)
    )
    records: list[dict[str, Any]] = []
    errors: dict[str, str] = {}
    for record_type, result in results:
        if isinstance(result, Exception):
            errors[record_type] = "DNS query failed."
        else:
            records.extend(result)

    if errors and not records:
        raise TimeoutError("DNS resolver did not respond.")
    return "system DNS resolver", {"records": records, "errors": errors}
