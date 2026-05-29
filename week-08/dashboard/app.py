from pathlib import Path
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from dashboard.config import load_services
from dashboard.collector import collect_all
from dashboard.history import (read_provider_history, read_manufacturer_history, read_retailer_history)
from dashboard.context import load_context
from dashboard.alerts import compute_alerts

_FRONTEND = Path(__file__).parent.parent / "frontend"
_PAGES = {"/": "overview", "/provider": "provider", "/manufacturer": "manufacturer", "/retailer": "retailer"}


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

    for route, page in _PAGES.items():
        async def page_handler(_page=page):
            return HTMLResponse(_render_shell(_page, refresh))
        app.get(route)(page_handler)

    return app
