import re

_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")
_TLD = re.compile(r"^(?:[a-z]{2,63}|xn--[a-z0-9-]{2,59})$")


def normalize_domain(value: str) -> str:
    """Normalize a bare domain to lowercase ASCII IDNA and reject URL-like input."""
    candidate = value.strip()
    if not candidate or any(char in candidate for char in "/\\?#@: "):
        raise ValueError("Invalid domain name.")

    try:
        domain = candidate.rstrip(".").encode("idna").decode("ascii").lower()
    except UnicodeError as exc:
        raise ValueError("Invalid domain name.") from exc

    if not domain or len(domain) > 253:
        raise ValueError("Invalid domain name.")
    labels = domain.split(".")
    if len(labels) < 2 or any(
        len(label) > 63 or not _LABEL.fullmatch(label) for label in labels
    ):
        raise ValueError("Invalid domain name.")
    if not _TLD.fullmatch(labels[-1]):
        raise ValueError("Invalid domain name.")
    return domain
