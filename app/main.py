"""FastAPI application factory.

Assembles all routers, middleware, and lifecycle hooks into a single ``app``
instance that Uvicorn serves.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine
from app.routers import health, shap, stations

# ── Logging ────────────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger(__name__)


# ── Lifespan ───────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle manager."""
    logger.info("Water Quality Cloud API starting up…")
    yield
    logger.info("Shutting down — disposing async DB engine…")
    await engine.dispose()


# ── App ────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Water Quality Cloud API",
    description=(
        "Cloud Integration Layer (Zone 3) for the **Explainable Hybrid ML "
        "Ensemble** edge-to-cloud IoT water quality monitoring system.\n\n"
        "All endpoints (except `/health`) require an `X-API-Key` header."
    ),
    version="2.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],          # tighten in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────

app.include_router(health.router)
app.include_router(stations.router)
app.include_router(shap.router)
