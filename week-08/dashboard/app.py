from pathlib import Path
import httpx
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from dashboard.config import load_services, ServiceConfig
from dashboard.collector import collect_all
from dashboard.history import (read_provider_history, read_manufacturer_history, read_retailer_history,
                                latest_manufacturer_state, latest_provider_state, latest_retailer_state,
                                latest_retailer_orders, count_retailer_in_transit,
                                count_retailer_stalled)
from dashboard.context import load_context
from dashboard.alerts import compute_alerts
from dashboard import derive

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

    @app.get("/api/archive/scenarios")
    async def archive_scenarios():
        logs_dir = Path("logs")
        result = []
        for d in sorted(logs_dir.iterdir()):
            if d.is_dir() and (d / "run.csv").exists():
                result.append(d.name)
        return JSONResponse(result)

    @app.get("/api/archive/{scenario}/state")
    async def archive_state(scenario: str):
        logs_dir = Path("logs") / scenario
        arc_services = {
            tier: ServiceConfig(tier, "", logs_dir / f"{tier}.db")
            for tier in ("provider", "manufacturer", "retailer")
        }
        history = {
            "provider": read_provider_history(arc_services["provider"].db_path),
            "manufacturer": read_manufacturer_history(arc_services["manufacturer"].db_path),
            "retailer": read_retailer_history(arc_services["retailer"].db_path),
        }
        ctx = load_context(run_csv=logs_dir / "run.csv", scenarios_dir=Path("scenarios"))
        mfr_state = latest_manufacturer_state(arc_services["manufacturer"].db_path)
        util = round(mfr_state["util"] * 100, 1) if mfr_state and mfr_state["util"] is not None else None
        prov_items, prov_orders = latest_provider_state(arc_services["provider"].db_path)
        ret_items = latest_retailer_state(arc_services["retailer"].db_path)
        ret_orders = latest_retailer_orders(arc_services["retailer"].db_path)
        prov_in_transit = sum(i.get("in_transit", 0) for i in prov_items)
        mfr_items = []
        if mfr_state:
            mfr_items = [{"name": f["name"], "stock": f["stock"], "price": f["price"], "kind": "finished"}
                         for f in mfr_state["finished"]]
            finished_names = {i["name"] for i in mfr_items}
            mfr_items += [{"name": k, "stock": v, "price": None, "kind": "part"}
                          for k, v in derive.dedup_parts(mfr_state["parts"], finished_names).items()]
        latest = ctx.get("latest") or {}
        arc_tiers = {
            "provider": {"online": True, "items": prov_items, "orders": prov_orders, "in_transit_out": prov_in_transit, "extra": {}},
            "manufacturer": {"online": True, "items": mfr_items, "orders": [], "in_transit_out": None, "extra": {"utilisation_pct": util, "sales_pending": mfr_state["pending"] if mfr_state else 0, "sales_completed": mfr_state["completed"] if mfr_state else 0}},
            "retailer": {"online": True, "items": ret_items, "orders": ret_orders, "in_transit_out": count_retailer_in_transit(arc_services["retailer"].db_path), "extra": {"stalled": count_retailer_stalled(arc_services["retailer"].db_path)}},
        }
        arc_backlog = ctx.get("total_backordered", 0)
        arc_avg_fill = ctx.get("avg_fill_rate")
        return JSONResponse({
            "day": latest.get("day"), "day_total": ctx.get("day_total"), "scenario": scenario,
            "events": {"label": latest.get("events"), "demand_mod": latest.get("demand_mod"),
                       "supply_mod": latest.get("supply_mod"), "lead_mod": latest.get("lead_mod")},
            "kpis": {"fill_rate": arc_avg_fill, "backlog": arc_backlog, "production_util": util},
            "alerts": compute_alerts(arc_tiers, arc_backlog),
            "tiers": arc_tiers,
            "history": history,
            "fill_rate_series": ctx.get("fill_rate_series", []),
        })

    @app.get("/api/state")
    async def api_state():
        tiers = await collect_all(services)
        # find the most recently modified per-scenario run.csv as live context
        logs_dir = Path("logs")
        csv_candidates = sorted(logs_dir.glob("*/run.csv"), key=lambda p: p.stat().st_mtime, reverse=True)
        ctx = load_context(run_csv=csv_candidates[0], scenarios_dir=Path("scenarios")) if csv_candidates else {"scenario": None, "day_total": None, "latest": None, "fill_rate_series": []}
        day = max((t["current_day"] for t in tiers.values() if t.get("current_day") is not None), default=None)
        latest = ctx.get("latest") or {}
        util = tiers["manufacturer"]["extra"].get("utilisation_pct")
        avg_fill_rate = ctx.get("avg_fill_rate")
        # Use cumulative backlog from CSV when available; fall back to live order count
        backlog = ctx.get("total_backordered") if ctx.get("total_backordered") is not None else derive.count_backordered(tiers["retailer"]["orders"])
        stale = not day
        return JSONResponse({
            "day": day, "day_total": None if stale else ctx.get("day_total"), "scenario": ctx.get("scenario"),
            "events": {} if stale else {"label": latest.get("events"), "demand_mod": latest.get("demand_mod"),
                       "supply_mod": latest.get("supply_mod"), "lead_mod": latest.get("lead_mod")},
            "kpis": {"fill_rate": None if stale else avg_fill_rate, "backlog": None if stale else backlog, "production_util": util},
            "alerts": compute_alerts(tiers, backlog),
            "tiers": tiers, "history": build_history(services),
            "fill_rate_series": [] if stale else ctx.get("fill_rate_series", []),
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
