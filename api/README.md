# OpenLookup API

Async, stateless API for passive DNS, RDAP, certificate-transparency, and ASN lookups. It has no database. The in-memory cache and rate limiter are per process; use a shared Redis-backed implementation before running multiple API workers or instances.

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
- `GET /api/domain/{name}` returns all sections in one JSON response.
- `GET /api/domain/{name}/stream` emits one `section` SSE event per completed provider and a final `done` event.
- Both domain endpoints accept `?refresh=1`, which bypasses the section cache and uses a stricter rate limit.

Every section has `section`, `status`, `source`, `fetched_at`, `cached`, `data`, and an optional `message`. A failed provider returns its own error or timeout result; successful sections are cached independently.

## Data sources and cache

- DNS: configured recursive resolver via dnspython; A, AAAA, MX, NS, TXT, and CNAME records (5 minute cache).
- Registration: IANA RDAP bootstrap and the selected registry endpoint (24 hour cache).
- Subdomains: crt.sh with Certspotter fallback (1 hour cache).
- IP/ASN: public A/AAAA records and Team Cymru's DNS-based ASN service (5 minute cache). Private and non-global addresses are excluded from ASN queries.

Outbound HTTP requests use fixed provider hosts, bounded response sizes, timeouts, and do not follow redirects. The API never fetches a user-supplied URL or connects to the target host.

## Configuration

Set `CORS_ORIGINS` to a comma-separated list of exact frontend origins in production. Keep `CERTSPOTTER_API_KEY` and other provider credentials in the API host environment; never put them in the web client. Rate limits and concurrency caps are process-local and should be replaced with shared infrastructure for a multi-instance deployment.
