import asyncio
from typing import Any

import dns.asyncresolver
import dns.exception
import dns.resolver


async def _txt_records(
    name: str, resolver: dns.asyncresolver.Resolver
) -> list[str] | Exception:
    try:
        answer = await resolver.resolve(
            name, "TXT", lifetime=4.0, raise_on_no_answer=False, search=False
        )
    except (dns.resolver.NoAnswer, dns.resolver.NXDOMAIN):
        return []
    except (dns.exception.Timeout, dns.resolver.NoNameservers) as exc:
        return exc
    if answer.rrset is None:
        return []
    return [
        b"".join(record.strings).decode("utf-8", errors="replace") for record in answer
    ]


def _spf(records: list[str] | None) -> dict[str, Any]:
    if records is None:
        return {
            "status": "unavailable",
            "summary": "The SPF DNS query failed, so the policy could not be checked.",
            "records": [],
        }
    policies = [
        record
        for record in records
        if record.strip().lower() == "v=spf1"
        or record.strip().lower().startswith("v=spf1 ")
    ]
    if not policies:
        return {
            "status": "missing",
            "summary": "No SPF policy was found at the domain.",
            "records": [],
        }
    if len(policies) > 1:
        return {
            "status": "multiple",
            "summary": "Multiple SPF policies were found; receivers may treat this as an SPF error.",
            "records": policies,
        }
    return {
        "status": "found",
        "summary": "An SPF policy was found. It lists which senders the policy authorizes.",
        "records": policies,
    }


def _dmarc(records: list[str] | None) -> dict[str, Any]:
    if records is None:
        return {
            "status": "unavailable",
            "summary": "The DMARC DNS query failed, so the policy could not be checked.",
            "records": [],
            "policy": None,
        }
    policies = [
        record
        for record in records
        if record.strip().lower() == "v=dmarc1"
        or record.strip().lower().startswith("v=dmarc1;")
    ]
    if not policies:
        return {
            "status": "missing",
            "summary": "No DMARC policy was found at _dmarc.",
            "records": [],
            "policy": None,
        }
    if len(policies) > 1:
        return {
            "status": "multiple",
            "summary": "Multiple DMARC policies were found; receivers may ignore them.",
            "records": policies,
            "policy": None,
        }

    tags = {
        key.strip().lower(): value.strip()
        for item in policies[0].split(";")
        if "=" in item
        for key, value in [item.split("=", 1)]
    }
    policy = tags.get("p")
    if policy not in {"none", "quarantine", "reject"}:
        return {
            "status": "found",
            "summary": "A DMARC record was found, but its policy tag could not be read.",
            "records": policies,
            "policy": policy,
        }

    summaries = {
        "none": "DMARC is monitoring only; receivers are not asked to quarantine or reject failing mail.",
        "quarantine": "DMARC asks receivers to treat failing mail as suspicious, commonly by sending it to spam.",
        "reject": "DMARC asks receivers to reject mail that fails the policy checks.",
    }
    return {
        "status": "found",
        "summary": summaries[policy],
        "records": policies,
        "policy": policy,
    }


async def lookup(
    domain: str, resolver: dns.asyncresolver.Resolver
) -> tuple[str, dict[str, Any]]:
    spf_result, dmarc_result = await asyncio.gather(
        _txt_records(domain, resolver),
        _txt_records(f"_dmarc.{domain}", resolver),
    )
    if isinstance(spf_result, Exception) and isinstance(dmarc_result, Exception):
        raise TimeoutError("Email security DNS queries did not respond.")

    errors = []
    if isinstance(spf_result, Exception):
        errors.append("SPF DNS query failed.")
        spf_result = None
    if isinstance(dmarc_result, Exception):
        errors.append("DMARC DNS query failed.")
        dmarc_result = None

    return "system DNS resolver", {
        "spf": _spf(spf_result),
        "dmarc": _dmarc(dmarc_result),
        "errors": errors,
    }
