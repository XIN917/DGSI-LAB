#!/usr/bin/env python3
"""Week 8 REST turn engine for autonomous supply-chain simulations."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

import httpx

from scenario_utils import deterministic_customer_demand, load_json, signal_for_day


ROOT = Path(__file__).parent
LOG_DIR = ROOT / "logs"


class Engine:
    def __init__(self, config_path: str, scenario_path: str, days: int):
        self.config_path = Path(config_path)
        self.scenario_path = Path(scenario_path)
        self.config = load_json(config_path)
        self.scenario = load_json(scenario_path)
        self.days = days
        self.services = self.config["services"]
        self.client = httpx.Client(timeout=30.0)
        LOG_DIR.mkdir(exist_ok=True)

    def run(self) -> None:
        for day in range(1, self.days + 1):
            signal = signal_for_day(self.scenario, day)
            self.apply_hard_effects(signal.modifiers)
            self.generate_customer_demand(day, signal.modifiers)

            role_results = []
            for role in ("retail", "manufacturer", "provider"):
                result = self.run_role(day, role, signal)
                role_results.append(f"{role}:{result}")

            for service in ("retailer", "manufacturer", "provider"):
                self.post(service, "/api/day/advance")

            for service in ("retailer", "manufacturer", "provider"):
                self.post(service, "/api/metrics/snapshot")

            summary = self.daily_summary()
            print(
                f"day={day:03d} signal={signal.name} "
                f"mods={json.dumps(signal.modifiers, sort_keys=True)} "
                f"roles={','.join(role_results)} summary={summary}"
            )

    def apply_hard_effects(self, modifiers: dict[str, float]) -> None:
        self.post(
            "provider",
            "/api/scenario/effects",
            json={
                "lead_time_modifier": modifiers["lead_time_modifier"],
                "supply_modifier": modifiers["supply_modifier"],
            },
        )

    def generate_customer_demand(self, day: int, modifiers: dict[str, float]) -> None:
        inventory = self.get("retailer", "/api/inventory")
        prices = {item["sku"]: float(item["retail_price"]) for item in inventory}
        for sku, params in self.config["demand"].items():
            qty = deterministic_customer_demand(
                sku=sku,
                base_daily_units=int(params["base_daily_units"]),
                retail_price=prices.get(sku, float(params["reference_price"])),
                reference_price=float(params["reference_price"]),
                demand_modifier=modifiers["demand_modifier"],
                price_sensitivity=modifiers["price_sensitivity"],
                seed=(day * 1000) + sum(ord(c) for c in sku),
            )
            if qty:
                self.post(
                    "retailer",
                    "/api/customer-orders/",
                    params={"sku": sku, "quantity": qty, "customer_name": f"day-{day:03d}-demand"},
                )

    def run_role(self, day: int, role: str, signal: Any) -> str:
        mode = self.config.get("fallback_mode", "auto")
        if mode != "always":
            status = self.run_claude(day, role, signal)
            if status == "claude":
                return status
        self.fallback_role(role)
        return "fallback"

    def run_claude(self, day: int, role: str, signal: Any) -> str:
        claude_path = Path(self.config.get("claude_path", "claude"))
        if "/" in str(claude_path) and not claude_path.exists():
            return "missing"
        skill_path = ROOT / "skills" / f"{role}-manager.md"
        prompt = (
            f"Use this skill to manage simulation day {day}.\n\n"
            f"{skill_path.read_text(encoding='utf-8')}\n\n"
            f"Scenario signal: {signal.name}\n"
            f"Modifiers: {json.dumps(signal.modifiers, sort_keys=True)}\n"
            "Make concise CLI decisions only. Do not explain."
        )
        log_path = LOG_DIR / f"day-{day:03d}-{role}.log"
        try:
            result = subprocess.run(
                [str(claude_path), "--print", "--prompt", prompt],
                text=True,
                capture_output=True,
                timeout=int(self.config.get("claude_timeout_seconds", 180)),
                check=False,
            )
            log_path.write_text(result.stdout + result.stderr, encoding="utf-8")
            return "claude" if result.returncode == 0 else "error"
        except Exception as exc:
            log_path.write_text(f"Claude failed: {exc}\n", encoding="utf-8")
            return "error"

    def fallback_role(self, role: str) -> None:
        if role == "retail":
            self.fallback_retailer()
        elif role == "manufacturer":
            self.fallback_manufacturer()
        elif role == "provider":
            self.fallback_provider()

    def fallback_retailer(self) -> None:
        cfg = self.config["fallback"]
        for item in self.get("retailer", "/api/inventory"):
            if int(item["quantity_on_hand"]) <= int(cfg["retailer_reorder_threshold"]):
                self.post(
                    "retailer",
                    "/api/purchase-orders/",
                    params={
                        "sku": item["sku"],
                        "quantity": int(cfg["retailer_reorder_quantity"]),
                    },
                    tolerate_errors=True,
                )

    def fallback_manufacturer(self) -> None:
        token = self.manufacturer_token()
        orders = self.get("manufacturer", "/api/orders", headers=self.auth(token), tolerate_errors=True) or []
        for order in orders:
            if order.get("status") == "pending":
                self.post(
                    "manufacturer",
                    f"/api/orders/{order['id']}/release",
                    headers=self.auth(token),
                    tolerate_errors=True,
                )
        stock = self.get("manufacturer", "/api/inventory", headers=self.auth(token), tolerate_errors=True) or {}
        for item in stock.get("items", []):
            if item.get("unit_type") == "raw" and float(item.get("quantity", 0)) < self.config["fallback"]["manufacturer_raw_threshold"]:
                self.post(
                    "provider",
                    "/api/stock/restock/1",
                    json={"quantity": int(self.config["fallback"]["manufacturer_restock_quantity"])},
                    tolerate_errors=True,
                )

    def fallback_provider(self) -> None:
        qty = int(self.config["fallback"]["provider_restock_quantity"])
        for item in self.get("provider", "/api/stock/"):
            if int(item["quantity"]) < qty:
                self.post("provider", f"/api/stock/restock/{item['product_id']}", json={"quantity": qty}, tolerate_errors=True)

    def daily_summary(self) -> str:
        try:
            retailer_orders = self.get("retailer", "/api/customer-orders/")
            fulfilled = len([o for o in retailer_orders if str(o.get("status")) == "fulfilled"])
            backordered = len([o for o in retailer_orders if str(o.get("status")) == "backordered"])
            return f"customer_orders={len(retailer_orders)} fulfilled={fulfilled} backordered={backordered}"
        except Exception as exc:
            return f"summary_unavailable={exc}"

    def manufacturer_token(self) -> str | None:
        auth = self.config.get("manufacturer_auth", {})
        try:
            response = self.client.post(
                self.services["manufacturer"].rstrip("/") + "/api/auth/login",
                data={"username": auth.get("username", "admin"), "password": auth.get("password", "admin123")},
            )
            response.raise_for_status()
            return response.json()["access_token"]
        except Exception:
            return None

    @staticmethod
    def auth(token: str | None) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}"} if token else {}

    def url(self, service: str, path: str) -> str:
        return self.services[service].rstrip("/") + path

    def get(self, service: str, path: str, **kwargs):
        tolerate = kwargs.pop("tolerate_errors", False)
        response = self.client.get(self.url(service, path), **kwargs)
        if tolerate and response.status_code >= 400:
            return None
        response.raise_for_status()
        return response.json()

    def post(self, service: str, path: str, **kwargs):
        tolerate = kwargs.pop("tolerate_errors", False)
        response = self.client.post(self.url(service, path), **kwargs)
        if tolerate and response.status_code >= 400:
            return None
        response.raise_for_status()
        return response.json()


def main(argv: list[str]) -> int:
    if len(argv) != 4:
        print("Usage: python turn_engine.py config/sim.json scenarios/holiday-rush.json 25", file=sys.stderr)
        return 2
    try:
        days = int(argv[3])
    except ValueError:
        print("days must be an integer", file=sys.stderr)
        return 2
    if days <= 0:
        print("days must be positive", file=sys.stderr)
        return 2
    Engine(argv[1], argv[2], days).run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
