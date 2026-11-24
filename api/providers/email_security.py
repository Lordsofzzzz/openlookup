import asyncio
from typing import Any

import dns.resolver

from .dns_resolver import DNS_SOURCE, DNSResolverPool


async def _txt_records(
    name: str, resolver: DNSResolverPool
) -> tuple[list[str] | None, bool]:
    results = await resolver.resolve(name, "TXT")
    records: dict[str, None] = {}
    answered = False
    failed = False
    for answer in results:
        if resolver.is_failure(answer):
            failed = True
            continue
        answered = True
        if isinstance(answer, dns.resolver.NXDOMAIN) or answer.rrset is None:
            continue
        for record in answer:
            value = b"".join(record.strings).decode("utf-8", errors="replace")
            records[value] = None
    return (list(records) if answered else None), failed


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


def _versioned_policy(
    records: list[str] | None,
    version: str,
    lookup_name: str,
) -> dict[str, Any]:
    if records is None:
        return {
            "status": "unavailable",
            "summary": f"The {lookup_name} DNS query failed, so the policy could not be checked.",
            "records": [],
        }

    policies = [
        record
        for record in records
        if record.strip().split(";", 1)[0].strip().lower() == version.lower()
    ]
    if not policies:
        return {
            "status": "missing",
            "summary": f"No {lookup_name} policy record was found.",
            "records": [],
        }
    if len(policies) > 1:
        return {
            "status": "multiple",
            "summary": f"Multiple {lookup_name} policy records were found.",
            "records": policies,
        }
    return {
        "status": "found",
        "summary": f"A {lookup_name} policy record was found.",
        "records": policies,
    }


async def lookup(domain: str, resolver: DNSResolverPool) -> tuple[str, dict[str, Any]]:
    spf_result, dmarc_result, mta_sts_result, tls_rpt_result = await asyncio.gather(
        _txt_records(domain, resolver),
        _txt_records(f"_dmarc.{domain}", resolver),
        _txt_records(f"_mta-sts.{domain}", resolver),
        _txt_records(f"_smtp._tls.{domain}", resolver),
    )
    query_results = {
        "SPF": spf_result,
        "DMARC": dmarc_result,
        "MTA-STS": mta_sts_result,
        "TLS-RPT": tls_rpt_result,
    }
    if all(result[0] is None for result in query_results.values()):
        raise TimeoutError("Email security DNS queries did not respond.")

    errors = [
        f"One or more {label} DNS resolvers failed."
        for label, (records, failed) in query_results.items()
        if records is None or failed
    ]

    return DNS_SOURCE, {
        "spf": _spf(spf_result[0]),
        "dmarc": _dmarc(dmarc_result[0]),
        "mta_sts": _versioned_policy(mta_sts_result[0], "v=stsv1", "MTA-STS"),
        "tls_rpt": _versioned_policy(tls_rpt_result[0], "v=tlsrptv1", "TLS-RPT"),
        "errors": errors,
    }
