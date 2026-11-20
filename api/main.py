import asyncio
from contextlib import asynccontextmanager

import dns.asyncresolver
import httpx
from config import settings
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routes.domain import router as domain_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.http_client = httpx.AsyncClient(
        timeout=httpx.Timeout(8.0, connect=3.0),
        limits=httpx.Limits(max_connections=40, max_keepalive_connections=20),
        follow_redirects=False,
        trust_env=False,
        headers={"User-Agent": "OpenLookup/1.0 (+passive public-data lookup)"},
    )
    app.state.dns_resolver = dns.asyncresolver.Resolver(configure=True)
    app.state.dns_resolver.timeout = 4.0
    app.state.dns_resolver.lifetime = 5.0
    app.state.lookup_semaphore = asyncio.Semaphore(settings.max_concurrent_lookups)
    try:
        yield
    finally:
        await app.state.http_client.aclose()


app = FastAPI(
    title="OpenLookup API",
    version="1.0.0",
    description="Passive public-data lookups for domain infrastructure.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=False,
    allow_methods=["GET"],
    allow_headers=["Accept", "Content-Type"],
)
app.include_router(domain_router)


@app.get("/api/health", tags=["health"])
async def health() -> dict[str, str]:
    return {"status": "ok", "service": "openlookup-api"}
