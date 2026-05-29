from pathlib import Path
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from dashboard.config import load_services
from dashboard.collector import collect_all
from dashboard.history import (read_provider_history, read_manufacturer_history, read_retailer_history)
from dashboard.context import load_context
from dashboard.alerts import compute_alerts

_FRONTEND = Path(__file__).parent.parent / "frontend"
_PAGES = {"/": "overview", "/provider": "provider", "/manufacturer": "manufacturer",
          "/retailer": "retailer", "/simulation": "simulation"}
_API = "http://127.0.0.1:8000"


def build_history(services) -> dict:
    return {
        "provider": read_provider_history(services["provider"].db_path),
        "manufacturer": read_manufacturer_history(services["manufacturer"].db_path),
        "retailer": read_retailer_history(services["retailer"].db_path),
    }


def _render_shell(page: str, refresh: int) -> str:
    html = (_FRONTEND / "index.html").read_text()
    return html.replace("{{PAGE}}", page).replace("{{REFRESH}}", str(refresh))


def create_app(sim_json_path: Path, refresh: int = 2) -> FastAPI:
    services = load_services(sim_json_path)
    app = FastAPI(title="Supply Chain Live Dashboard")
    app.mount("/static", StaticFiles(directory=_FRONTEND), name="static")

    @app.get("/api/state")
    async def api_state():
        tiers = await collect_all(services)
        ctx = load_context(run_csv=Path("logs/run.csv"), scenarios_dir=Path("scenarios"))
        backlog = sum(1 for o in tiers["retailer"]["orders"] if o.get("status") == "backordered")
        day = max((t["current_day"] for t in tiers.values() if t.get("current_day") is not None), default=None)
        latest = ctx.get("latest") or {}
        fill_rate = latest.get("fill_rate")
        util = tiers["manufacturer"]["extra"].get("utilisation_pct")
        return JSONResponse({
            "day": day, "day_total": ctx.get("day_total"), "scenario": ctx.get("scenario"),
            "events": {"label": latest.get("events"), "demand_mod": latest.get("demand_mod"),
                       "supply_mod": latest.get("supply_mod"), "lead_mod": latest.get("lead_mod")},
            "kpis": {"fill_rate": fill_rate, "backlog": backlog, "production_util": util},
            "alerts": compute_alerts(tiers, backlog),
            "tiers": tiers, "history": build_history(services),
            "fill_rate_series": ctx.get("fill_rate_series", []),
        })

    # ── Simulation control proxies to api_server (:8000) ──────────────────────

    _API_DOWN = JSONResponse({"error": "api_server is not running — start it with: venv/bin/python api_server.py"}, status_code=503)

    @app.post("/api/sim/reset")
    async def proxy_reset():
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.post(f"{_API}/reset")
            return JSONResponse(r.json(), status_code=r.status_code)
        except httpx.ConnectError:
            return _API_DOWN

    @app.get("/api/sim/reset/status")
    async def proxy_reset_status():
        try:
            async with httpx.AsyncClient(timeout=5) as c:
                r = await c.get(f"{_API}/reset/status")
            return JSONResponse(r.json())
        except httpx.ConnectError:
            return _API_DOWN

    @app.get("/api/sim/scenarios")
    async def proxy_scenarios():
        try:
            async with httpx.AsyncClient() as c:
                r = await c.get(f"{_API}/scenarios", timeout=5)
            return JSONResponse(r.json())
        except httpx.ConnectError:
            return _API_DOWN

    @app.get("/api/sim/models")
    async def proxy_models():
        try:
            async with httpx.AsyncClient() as c:
                r = await c.get(f"{_API}/models", timeout=5)
            return JSONResponse(r.json())
        except httpx.ConnectError:
            return _API_DOWN

    @app.post("/api/sim/run")
    async def proxy_start_run(request: Request):
        try:
            body = await request.json()
            async with httpx.AsyncClient() as c:
                r = await c.post(f"{_API}/run", json=body, timeout=10)
            return JSONResponse(r.json(), status_code=r.status_code)
        except httpx.ConnectError:
            return _API_DOWN

    @app.delete("/api/sim/run/{run_id}")
    async def proxy_cancel_run(run_id: str):
        try:
            async with httpx.AsyncClient() as c:
                r = await c.delete(f"{_API}/run/{run_id}", timeout=5)
            return JSONResponse(r.json(), status_code=r.status_code)
        except httpx.ConnectError:
            return _API_DOWN

    @app.get("/api/sim/run/{run_id}/status")
    async def proxy_run_status(run_id: str):
        try:
            async with httpx.AsyncClient() as c:
                r = await c.get(f"{_API}/run/{run_id}/status", timeout=5)
            return JSONResponse(r.json())
        except httpx.ConnectError:
            return _API_DOWN

    @app.get("/api/sim/run/{run_id}/stream")
    async def proxy_stream(run_id: str):
        async def event_gen():
            try:
                async with httpx.AsyncClient(timeout=None) as c:
                    async with c.stream("GET", f"{_API}/run/{run_id}/stream") as r:
                        async for line in r.aiter_lines():
                            yield line + "\n"
            except httpx.ConnectError:
                yield "data: ERROR api_server is not running\n\n"
        return StreamingResponse(event_gen(), media_type="text/event-stream")

    @app.get("/api/sim/runs")
    async def proxy_runs():
        try:
            async with httpx.AsyncClient() as c:
                r = await c.get(f"{_API}/runs", timeout=5)
            return JSONResponse(r.json())
        except httpx.ConnectError:
            return JSONResponse([])

    @app.delete("/api/sim/runs")
    async def proxy_delete_runs(request: Request):
        ids = request.query_params.get("ids", "")
        try:
            async with httpx.AsyncClient() as c:
                r = await c.delete(f"{_API}/runs", params={"ids": ids} if ids else {}, timeout=5)
            return JSONResponse(r.json(), status_code=r.status_code)
        except httpx.ConnectError:
            return _API_DOWN

    @app.get("/api/sim/run/{run_id}/charts")
    async def proxy_charts(run_id: str):
        try:
            async with httpx.AsyncClient() as c:
                r = await c.get(f"{_API}/run/{run_id}/charts", timeout=5)
            return JSONResponse(r.json(), status_code=r.status_code)
        except httpx.ConnectError:
            return _API_DOWN

    @app.get("/api/sim/run/{run_id}/charts/{filename}")
    async def proxy_chart_file(run_id: str, filename: str):
        from fastapi.responses import Response
        try:
            async with httpx.AsyncClient(timeout=10) as c:
                r = await c.get(f"{_API}/run/{run_id}/charts/{filename}")
            return Response(content=r.content, media_type="image/png")
        except httpx.ConnectError:
            return _API_DOWN

    @app.get("/api/sim/logs")
    async def list_logs():
        logs_dir = Path("logs")
        files = []
        for f in sorted(logs_dir.rglob("day-*.log"), reverse=True)[:100]:
            files.append({"path": str(f.relative_to(logs_dir)), "size": f.stat().st_size})
        return JSONResponse(files)

    @app.get("/api/sim/summaries")
    async def list_summaries():
        logs_dir = Path("logs")
        files = []
        for f in sorted(logs_dir.glob("*/summary.log"), reverse=True):
            files.append({"name": f.parent.name, "path": str(f.relative_to(logs_dir)), "size": f.stat().st_size})
        return JSONResponse(files)

    @app.get("/api/sim/log")
    async def read_log(path: str):
        target = (Path("logs") / path).resolve()
        if not str(target).startswith(str(Path("logs").resolve())):
            return JSONResponse({"error": "invalid path"}, status_code=400)
        if not target.exists():
            return JSONResponse({"error": "not found"}, status_code=404)
        return JSONResponse({"content": target.read_text(errors="replace")})

    # ── Page routes ────────────────────────────────────────────────────────────

    for route, page in _PAGES.items():
        async def page_handler(_page=page):
            return HTMLResponse(_render_shell(_page, refresh))
        app.get(route)(page_handler)

    return app
