"""FastAPI entry point."""
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .db import Base, engine
from .routes import accounts, drafts, health, leads

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

app = FastAPI(title="Outreach Engine API", version="0.1.0")

_origins = list({
    settings.app_base_url,
    "http://localhost:3000",
})
# Allow any onrender.com subdomain (so dev and prod both work without re-config)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_origin_regex=r"https://.*\.onrender\.com",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Auto-create tables on first run (Alembic recommended for prod)
@app.on_event("startup")
def _create_tables() -> None:
    Base.metadata.create_all(bind=engine)


app.include_router(health.router)
app.include_router(accounts.router)
app.include_router(leads.router)
app.include_router(drafts.router)
