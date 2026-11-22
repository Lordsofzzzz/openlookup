# OpenLookup API

Async, stateless API for passive DNS, DNSSEC, email security, RDAP, certificate-transparency, and ASN lookups. It has no database; successful provider results use a bounded, process-local cache.

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
- `GET /api/v1/domain/{name}/sections/{section}` runs a single provider and returns one section with `Cache-Control: no-store`. Supported sections are `dns`, `dnssec`, `rdap`, `subdomains`, `ip`, `exposure`, and `email_security`. Unknown sections return 404 and invalid domains return 422. Lookup requests that wait two seconds for capacity return 503.

Every section has `section`, `status`, `source`, `fetched_at`, `data`, a `retryable` flag, and an optional `message`. A failed provider returns its own error or timeout result.

## Data sources

- DNS: configured recursive resolver via dnspython; A, AAAA, MX, NS, TXT, CNAME, and CAA records. DNSSEC status is checked separately through Cloudflare DNS-over-HTTPS validation.
- Email security: SPF, DMARC, MTA-STS, and TLS-RPT TXT records via the configured recursive resolver.
- Registration: IANA RDAP bootstrap and the selected registry endpoint.
- Subdomains: Cert Spotter.
- IP/ASN: public A/AAAA records and Team Cymru's DNS-based ASN service. Each IP includes its associated ASNs and network names when available; grouped network details remain available. Private and non-global addresses are excluded from ASN queries.
- Exposure: [Shodan InternetDB](https://internetdb.shodan.io/) returns open ports, software (CPE), tags, and CVEs it has recorded for each public IP (first 10 addresses). No API key is needed. The API sends only the resolved public IP addresses to Shodan, never the target host. InternetDB is free for non-commercial use only, so check its terms before offering OpenLookup commercially. Its data can be stale, and its CVE list is inferred from software versions, so treat it as a lead, not a confirmed finding.

Outbound HTTP requests use fixed provider hosts, bounded response sizes, timeouts, and do not follow redirects. The API never fetches a user-supplied URL or connects to the target host.

## Configuration

Set `CORS_ORIGINS` to a comma-separated list of exact frontend origins in production. Keep `CERTSPOTTER_API_KEY` and other provider credentials in the API host environment; never put them in the web client. The lookup concurrency cap and section cache are process-local and should be coordinated across instances if needed. Successful section results are cached for 2 minutes for DNS, DNSSEC, and email security, 10 minutes for IP/ASN, 1 hour for subdomains, 1 hour for exposure, and 1 hour for RDAP. Set `DNS_CACHE_TTL_SECONDS`, `DNSSEC_CACHE_TTL_SECONDS`, `EMAIL_SECURITY_CACHE_TTL_SECONDS`, `IP_CACHE_TTL_SECONDS`, `SUBDOMAINS_CACHE_TTL_SECONDS`, `EXPOSURE_CACHE_TTL_SECONDS`, or `RDAP_CACHE_TTL_SECONDS` to change each lifetime. Set a TTL to `0` to disable caching for that section. Identical concurrent requests for a section share one provider call. Manual section refreshes bypass cached results and join an identical request already in progress. The in-memory cache is bounded to 2,048 entries.
