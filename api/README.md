# OpenLookup API

Async, stateless API for passive DNS, email security, RDAP, certificate-transparency, and ASN lookups. It has no database or application-level cache.

## Run locally

```sh
cd api
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --no-access-log
```

The API listens on `http://localhost:8000`. Interactive docs and the OpenAPI schema are at `/docs` and `/openapi.json`. Access logging is disabled so searched domains are not written into Uvicorn request logs. Do not enable access logs without disclosing that searches may be logged.

## Endpoints

- `GET /api/health`
- `GET /api/v1/domain/{name}` returns all sections in one JSON response.
- `GET /api/v1/domain/{name}/stream` emits one `section` SSE event per completed provider and a final `done` event.
- `GET /api/v1/domain/{name}/sections/{section}` runs a single provider and returns one section with `Cache-Control: no-store`. Supported sections are `dns`, `rdap`, `subdomains`, `ip`, and `email_security`. Unknown sections return 404 and invalid domains return 422. Lookup requests that wait two seconds for capacity return 503.

Every section has `section`, `status`, `source`, `fetched_at`, `data`, a `retryable` flag, and an optional `message`. A failed provider returns its own error or timeout result.

## Data sources

- DNS: configured recursive resolver via dnspython; A, AAAA, MX, NS, TXT, and CNAME records.
- Email security: SPF at the domain and DMARC at `_dmarc.<domain>` via the configured recursive resolver.
- Registration: IANA RDAP bootstrap and the selected registry endpoint.
- Subdomains: Cert Spotter.
- IP/ASN: public A/AAAA records and Team Cymru's DNS-based ASN service. Private and non-global addresses are excluded from ASN queries.

Outbound HTTP requests use fixed provider hosts, bounded response sizes, timeouts, and do not follow redirects. The API never fetches a user-supplied URL or connects to the target host.

## Configuration

Set `CORS_ORIGINS` to a comma-separated list of exact frontend origins in production. Keep `CERTSPOTTER_API_KEY` and other provider credentials in the API host environment; never put them in the web client. The lookup concurrency cap and section cache are process-local and should be coordinated across instances if needed. Successful section results are cached for 2 minutes for DNS and email security, 10 minutes for IP/ASN and subdomains, and 1 hour for RDAP. Set `DNS_CACHE_TTL_SECONDS`, `EMAIL_SECURITY_CACHE_TTL_SECONDS`, `IP_CACHE_TTL_SECONDS`, `SUBDOMAINS_CACHE_TTL_SECONDS`, or `RDAP_CACHE_TTL_SECONDS` to change each lifetime. Set a TTL to `0` to disable caching for that section. Identical concurrent requests for a section share one provider call. Manual section refreshes bypass cached results and join an identical request already in progress. The in-memory cache is bounded to 2,048 entries.
