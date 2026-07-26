from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from taskiq.api.scheduler import run_scheduler_task

from app.api import router
from app.broker import broker, scheduler
from app.config import settings
from app.db import init_db

# Register scheduled poll tasks with the broker (LabelScheduleSource).
import app.tasks.polling  # noqa: F401

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("freedompay")

STATIC_DIR = Path(__file__).resolve().parent / "static"
WEB_DIR = STATIC_DIR / "web"


@asynccontextmanager
async def lifespan(_app: FastAPI):
    init_db()
    scheduler_task: asyncio.Task | None = None

    if settings.TASKIQ_EMBEDDED and not broker.is_worker_process:
        await broker.startup()
        # Scheduler enqueues; InMemoryBroker executes polls as asyncio tasks.
        scheduler_task = asyncio.create_task(
            run_scheduler_task(
                scheduler,
                run_startup=True,
                update_interval=timedelta(seconds=30),
                loop_interval=timedelta(seconds=1),
            ),
            name="taskiq-scheduler",
        )
        logger.info(
            "Taskiq scheduler started (embedded InMemoryBroker, per-chain poll)"
        )

    logger.info(
        "FreedomPay started network=%s demo=%s fee=%s%%",
        settings.NETWORK,
        settings.DEMO_MODE,
        settings.SERVICE_FEE_PERCENT,
    )
    yield

    if scheduler_task is not None:
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass
    if settings.TASKIQ_EMBEDDED and not broker.is_worker_process:
        await broker.shutdown()


app = FastAPI(
    title="FreedomPay",
    version="0.2.0",
    description="Lightweight multi-chain merchant crypto gateway (BTC / TON / SOL)",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)

if STATIC_DIR.is_dir():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/embed.js")
def embed_script() -> FileResponse:
    path = STATIC_DIR / "embed.js"
    if not path.is_file():
        raise HTTPException(status_code=404, detail="embed.js missing")
    return FileResponse(path, media_type="application/javascript")


@app.get("/logo.png")
def logo() -> FileResponse:
    for path in (WEB_DIR / "logo.png", STATIC_DIR / "logo.png"):
        if path.is_file():
            return FileResponse(path, media_type="image/png")
    raise HTTPException(status_code=404, detail="logo missing")


def _spa_index() -> HTMLResponse | FileResponse:
    index = WEB_DIR / "index.html"
    if index.is_file():
        return FileResponse(index)
    return HTMLResponse(
        """<!doctype html><html><head><meta charset="utf-8"/>
<title>FreedomPay</title>
<link rel="icon" href="/logo.png"/>
<style>
:root{--gold:#F5C518}
body{margin:0;min-height:100vh;font-family:Syne,Segoe UI,sans-serif;
background:radial-gradient(ellipse at 20% 0%,#3a3a3a,#1a1a1a 55%,#0e0e0e);
color:#f2f2f2;display:grid;place-items:center}
.card{text-align:center;padding:2rem}
img{width:96px;height:96px;border-radius:50%;box-shadow:inset 0 0 0 2px #111}
h1{color:var(--gold);letter-spacing:.04em}
a{color:var(--gold)}
</style></head><body><div class="card">
<img src="/logo.png" alt="FreedomPay"/>
<h1>FreedomPay</h1>
<p>API up. Build frontend: <code>cd frontend && npm i && npm run build</code></p>
<p><a href="/docs">OpenAPI</a> · <a href="/v1/gateways">Gateways</a> · <a href="/demo">Demo</a></p>
</div></body></html>"""
    )


@app.get("/")
def home():
    return _spa_index()


@app.get("/pay/{invoice_id}")
def pay_page(invoice_id: str):
    """Prefer server-rendered checkout (QR + copy fields)."""
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url=f"/v1/pay/{invoice_id}/page", status_code=307)


@app.get("/embed")
def embed_page():
    return _spa_index()


@app.get("/demo")
def demo_page():
    return _spa_index()


if (WEB_DIR / "assets").is_dir():
    app.mount(
        "/assets",
        StaticFiles(directory=str(WEB_DIR / "assets")),
        name="web-assets",
    )
