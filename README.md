# OpenLookup

OpenLookup is a self-hosted domain lookup tool. Enter a domain to see how its email is configured, who operates its network, and which hosts appear in public records. The app queries DNS resolvers and public data providers without probing the target host.

Results appear one section at a time. If a provider times out, you can refresh that section while keeping the results already on screen. Copy the results URL to share the domain lookup.

## What a lookup shows

| Section | Results | Source |
| --- | --- | --- |
| DNS records | A, AAAA, MX, NS, TXT, CNAME, and CAA records with TTLs | Recursive DNS resolver |
| DNSSEC | Whether the resolver validated the domain’s DNSKEY response | Cloudflare DNS over HTTPS |
| Email security | Published SPF, DMARC, MTA-STS, and TLS reporting policies | DNS TXT records |
| Registration | Registrar, nameservers, status flags, and registration dates | Registry RDAP via IANA bootstrap |
| Subdomains | Hostnames observed in public certificates | Cert Spotter |
| Infrastructure | Public IP addresses, network prefixes, and autonomous system numbers | DNS and Team Cymru |
| Exposure | Previously observed ports, software, and inferred CVEs for up to ten public IPs | Shodan InternetDB |

Certificate records show only the hostnames observed by the provider. Exposure data can lag behind infrastructure changes, and a CVE inferred from a software version needs independent verification.

## Run locally

Use Python 3.12+, Node.js 22+, and npm. From the repository root, start the FastAPI server in one terminal.

```sh
cd api
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --no-access-log
```

In a second terminal, start the Vue app from the repository root.

```sh
cd web
npm ci
npm run dev
```

Open the local URL printed by Vite (usually [localhost:5173](http://localhost:5173)) and enter `example.com`. Vite forwards requests under `/api` to port 8000. The API needs outbound network access for lookups. The Cert Spotter API key is optional.

## Use the API

To retrieve just the DNS records for a domain, run the following with the API server running.

```sh
curl http://localhost:8000/api/v1/domain/example.com/sections/dns
```

Use `GET /api/v1/domain/{name}` for the complete JSON result, or append `/stream` to receive a server-sent event as each section finishes. Each section carries its source, fetch time, and lookup status. Explore the [interactive API docs](http://localhost:8000/docs) or see the [API guide](api/README.md) for endpoints, cache settings, provider terms, and diagnostics.

## Self-hosting

The [Helm chart](charts/) runs the Vue frontend behind Nginx and forwards API traffic to an internal FastAPI service. Each API process caches successful lookups in memory. No database setup is required.

Set the API and web image tags in [values.yaml](charts/values.yaml). Cloudflare Tunnel is enabled by default and expects a Kubernetes Secret named `cloudflared-token` with a `token` key. Set `cloudflared.enabled=false` if you provide your own ingress. Configure allowed browser origins with `CORS_ORIGINS` and keep provider credentials on the API server.

## Development

From `api/`, activate the virtual environment and run the backend checks.

```sh
ruff check .
ruff format --check .
python -m unittest discover -s tests
```

From `web/`, run the frontend checks.

```sh
npm run lint
npm run build
```

Bug reports and pull requests are welcome. Include steps to reproduce a problem and the checks you ran.

## License

This repository currently has no license file.
