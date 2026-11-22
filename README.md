# OpenLookup

OpenLookup is an open source web app for inspecting publicly available domain infrastructure and security signals. Enter a domain to view DNS records, DNSSEC validation, registration data, discovered subdomains, IP and ASN details, exposure data, and email security configuration.

Results come from public DNS and third-party data providers. They can be incomplete or out of date, and exposure data is a signal to investigate rather than proof of compromise.

## Features

- DNS records: A, AAAA, MX, NS, TXT, CNAME, and CAA
- DNSSEC validation through Cloudflare DNS over HTTPS
- Email security checks for SPF, DMARC, MTA-STS, and TLS reporting (TLS-RPT)
- Registration data through IANA RDAP bootstrap and registry RDAP servers
- Certificate transparency based subdomain discovery through Cert Spotter
- Public IP and ASN information through DNS and Team Cymru
- Public exposure data from Shodan InternetDB
- Live section updates and individual section refreshes

## Architecture

```text
Browser ──> Web app (Vue + Nginx) ──> API (FastAPI)
                                         ├── DNS / DNSSEC
                                         ├── RDAP
                                         ├── Cert Spotter
                                         ├── Team Cymru
                                         └── Shodan InternetDB
```

The API is stateless and has no database. It uses a bounded in-memory cache and shares identical concurrent provider requests. The Helm chart deploys the API and web app as Kubernetes services; the API service defaults to internal `ClusterIP`. Cloudflare Tunnel can expose the web service without publishing the API service directly.

The API makes outbound requests only to fixed provider services, applies timeouts and response size limits, and does not follow redirects. It does not fetch user-supplied URLs or connect to the target host.

## Run locally

Requirements: Python 3.12+, Node.js 22+, and npm.

Start the API:

```sh
cd api
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --no-access-log
```

The API listens on `http://localhost:8000`. Interactive API documentation is at `http://localhost:8000/docs`.

In another terminal, start the web app:

```sh
cd web
npm ci
npm run dev
```

Open the Vite URL printed in the terminal (usually `http://localhost:5173`). The web development server proxies `/api` requests to the local API.

## API routes

| Method | Route | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Health probe |
| `GET` | `/api/v1/domain/{name}` | Return all lookup sections as JSON |
| `GET` | `/api/v1/domain/{name}/stream` | Stream sections as server-sent events |
| `GET` | `/api/v1/domain/{name}/sections/{section}` | Fetch or retry one section |

Supported section names are `dns`, `dnssec`, `rdap`, `subdomains`, `ip`, `exposure`, and `email_security`. Invalid domains return `422`, unknown sections return `404`, and requests rejected due to API capacity return `503`.

Lookup responses include a server-generated `X-Request-ID` for support and diagnostics. Error details are kept privacy-safe: searched domains and client identifiers are not included in diagnostic logs. Access logs are disabled by default because request URLs contain searched domains.

## Configuration

The API reads settings from environment variables and `api/.env`:

| Variable | Default | Description |
| --- | --- | --- |
| `CORS_ORIGINS` | `http://localhost:5173` | Comma-separated allowed browser origins; use exact production origins. |
| `MAX_CONCURRENT_LOOKUPS` | `12` | Maximum concurrent lookups per API process. |
| `CERTSPOTTER_API_KEY` | unset | Optional Cert Spotter API key. Keep it on the API host. |
| `DNS_CACHE_TTL_SECONDS` | `120` | Successful DNS result cache lifetime. |
| `DNSSEC_CACHE_TTL_SECONDS` | `120` | Successful DNSSEC result cache lifetime. |
| `EMAIL_SECURITY_CACHE_TTL_SECONDS` | `120` | Successful email security cache lifetime. |
| `IP_CACHE_TTL_SECONDS` | `600` | Successful IP/ASN result cache lifetime. |
| `RDAP_CACHE_TTL_SECONDS` | `3600` | Successful RDAP result cache lifetime. |
| `SUBDOMAINS_CACHE_TTL_SECONDS` | `3600` | Successful subdomain result cache lifetime. |
| `EXPOSURE_CACHE_TTL_SECONDS` | `3600` | Successful exposure result cache lifetime. |

Set a section cache TTL to `0` to disable caching for that section. Cache and concurrency settings are process-local; multiple API replicas do not share them.

## Data providers and limitations

- DNS and email security use the configured public recursive resolver.
- DNSSEC is checked separately using Cloudflare DNS-over-HTTPS validation.
- RDAP uses the IANA bootstrap registry to find the appropriate registry service.
- Subdomain discovery uses Certificate Transparency data from Cert Spotter; it cannot discover every hostname.
- ASN details use Team Cymru's DNS service. Private and non-global addresses are excluded from ASN lookups.
- Exposure details use Shodan InternetDB for up to the first 10 public IP addresses. No API key is needed. InternetDB is free for non-commercial use; review [Shodan's terms](https://www.shodan.io/) before commercial use. Its data may be stale and inferred CVEs are not confirmed vulnerabilities.

## Self-hosting

The repository includes Dockerfiles and a Helm chart in `charts/`. Configure the chart image repositories and tags, provide a Kubernetes Secret containing the Cloudflare Tunnel token if enabling the tunnel, and set production `CORS_ORIGINS` for the API. Keep the API service internal and route public traffic through the web service and your Cloudflare Tunnel configuration.

The chart defaults to one API and one web replica. The cache and concurrency cap are per process, so account for that when changing replica counts.

## Development checks

Backend lint and formatting:

```sh
cd api
pip install -r requirements.txt
ruff check .
ruff format --check .
```

Backend tests:

```sh
cd api
python -m unittest discover -s tests
```

Frontend lint and production build:

```sh
cd web
npm ci
npm run lint
npm run build
```

## Contributing

Bug reports, documentation improvements, and focused pull requests are welcome. Please describe the problem and how you verified a change. Run the relevant lint, formatting, test, and build commands above before opening a pull request.

## License

No license file is currently included. Until a license is added, the repository should not be assumed to grant permission to reuse, modify, or distribute its code. Add a license that reflects the maintainer's intended terms before presenting the project as licensed open source.
