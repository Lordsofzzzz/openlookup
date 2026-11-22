from contextlib import asynccontextmanager

import httpx
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from core.diagnostics import RequestContextMiddleware, configure_logging
from providers.dns_resolver import DNSResolverPool
from routes.domain import router as domain_router
from routes.health import router as health_router
from routes.sections import router as sections_router
from routes.stream import router as stream_router
from services.lookup import LookupService


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    client = httpx.AsyncClient(
        timeout=httpx.Timeout(8.0, connect=3.0),
        limits=httpx.Limits(max_connections=40, max_keepalive_connections=20),
        follow_redirects=False,
        trust_env=False,
        headers={"User-Agent": "OpenLookup/1.0 (+passive public-data lookup)"},
    )
    app.state.lookup = LookupService(
        client, DNSResolverPool(), settings.max_concurrent_lookups
    )
    try:
        yield
    finally:
        await client.aclose()


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
    expose_headers=["X-Request-ID"],
    allow_methods=["GET"],
    allow_headers=["Accept", "Content-Type"],
)
app.include_router(domain_router)
app.include_router(sections_router)
app.include_router(stream_router)
app.include_router(health_router)

app.add_middleware(RequestContextMiddleware)
