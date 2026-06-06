#!/usr/bin/env python3
"""Turn engine: orchestrates one simulated day across all apps."""
import argparse
import csv
import subprocess
import json
import os
import random
import shutil
import sys
from pathlib import Path
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Per-agent wall-clock timeout in seconds. If an agent hasn't finished within
# this window it is killed and the day continues without its output.
AGENT_TIMEOUT_SECONDS = 300  # 5 minutes

# Load .env for GEMINI_API_KEY (optional dep — only needed for Gemini models)
try:
    from dotenv import load_dotenv
    load_dotenv(Path(__file__).parent / ".env")
except ImportError:
    pass  # python-dotenv not installed; rely on env vars being set externally

try:
    from google import genai as google_genai
    from google.genai import types as genai_types
    _GEMINI_AVAILABLE = True
except ImportError:
    _GEMINI_AVAILABLE = False

try:
    import httpx
except ImportError:
    print("Error: 'httpx' not found. Run: pip install httpx")
    sys.exit(1)

try:
    from visualize import generate_charts
    _VISUALIZE_AVAILABLE = True
except ImportError:
    _VISUALIZE_AVAILABLE = False

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich import box
    from rich.text import Text
    from rich.markdown import Markdown
    from rich.live import Live
    from rich.spinner import Spinner
except ImportError:
    print("Error: 'rich' not found. Run: pip install rich")
    sys.exit(1)

console = Console()


class _CallbackWriter:
    """File-like writer that feeds lines (with ANSI codes intact) to a callback."""
    def __init__(self, cb):
        self._cb = cb
        self._buf = ""

    def write(self, text):
        self._buf += text
        while "\n" in self._buf:
            line, self._buf = self._buf.split("\n", 1)
            if line.rstrip():
                self._cb(line.rstrip())

    def flush(self):
        if self._buf.strip():
            self._cb(self._buf.rstrip())
            self._buf = ""

COMPACT_ROLE_CONTRACTS = {
    "provider": """Role: Provider parts supplier.
Hard rules: never call day advance; never change any tier price by more than 15% in one day; do not let a product hit zero when orders are pending.
Use prefetched stock/orders as your assessment. Restock any product below 50% of its observed baseline back toward baseline. Raise prices 5-10% when stock is below 30%; lower top-tier prices 5-10% when stock is above 150%.
Commands: ./provider-cli restock <product> <quantity>; ./provider-cli price set <product> <tier> <price>.""",
    "manufacturer": """Role: Manufacturer 3D printer factory.
Hard rules: never call day advance; do not exceed daily capacity; release oldest producible sales orders first; buy bottleneck parts when stock is below about two days of expected consumption. Price floors: P3D-Classic EUR 163, P3D-Pro EUR 246.
Use prefetched stock, sales orders, capacity, and supplier names as your assessment. If a release fails, buy the missing part instead of repeatedly retrying the same blocked release.
Commands: ./manufacturer-cli production release <order_id>; ./manufacturer-cli purchase create --supplier <name> --product <id> --qty <n>; ./manufacturer-cli price set <model> <price>.""",
    "retailer": """Role: Retailer selling finished printers.
Hard rules: never call day advance; fulfill customer orders from stock where possible; mark insufficient-stock orders as backordered; reorder printers when stock is below roughly three days of recent demand.
Use prefetched stock, customer orders, purchase orders, and prices as your assessment. Raise retail prices about 5% when stock is tight; lower about 5% when inventory is piling up.
Commands: ./retailer-cli fulfill <order_id>; ./retailer-cli backorder <order_id>; ./retailer-cli purchase create <model> <qty>; ./retailer-cli price set <model> <price>.""",
}

ACTIVE_ROW_KEYWORDS = (
    "pending", "backorder", "backordered", "open", "created", "confirmed",
    "processing", "released", "blocked", "failed", "insufficient", "overdue",
)

# ── Helpers ──────────────────────────────────────────────────────────────────

def load_config(path):
    return json.loads(Path(path).read_text())

def load_scenario(path):
    return json.loads(Path(path).read_text())

def todays_signal(day, scenario):
    signal = {
        "day": day,
        "events": [],
        "demand_modifier": 1.0,
        "supply_modifier": 1.0,
        "lead_time_modifier": 1.0,
        "price_sensitivity": "normal",
    }
    for event in scenario.get("events", []):
        if event["start_day"] <= day <= event["end_day"]:
            signal["events"].append(event)
            # Multiply overlapping modifiers so combined stress compounds
            signal["demand_modifier"] *= event.get("demand_modifier", 1.0)
            signal["supply_modifier"] *= event.get("supply_modifier", 1.0)
            signal["lead_time_modifier"] *= event.get("lead_time_modifier", 1.0)
            if event.get("price_sensitivity") == "high":
                signal["price_sensitivity"] = "high"
    signal["base_demand"] = scenario.get("base_demand", {"mean": 5, "variance": 2})
    return signal

def parse_retailer_inventory(items):
    """Return SKU -> on-hand quantity from retailer API inventory payloads."""
    inventory = {}
    for item in items:
        sku = item.get("sku")
        qty = item.get("quantity_on_hand", item.get("quantity"))
        if sku is not None and qty is not None:
            inventory[sku] = qty
    return inventory

def parse_manufacturer_stock_output(output):
    """Return product -> quantity from the manufacturer CLI stock table."""
    inventory = {}
    for line in output.splitlines():
        if "|" in line:
            cells = [cell.strip() for cell in line.split("|")]
            if len(cells) < 3 or cells[0].upper() == "TYPE":
                continue
            product, qty_text = cells[1], cells[2]
        else:
            parts = line.split()
            if len(parts) < 2:
                continue
            product, qty_text = parts[0], parts[-1]

        try:
            qty = float(qty_text.replace(",", ""))
        except ValueError:
            continue
        inventory[product] = int(qty) if qty.is_integer() else qty
    return inventory

def compact_cli_output(output, max_lines=18):
    """Keep CLI prefetch text bounded while preserving headers and active rows."""
    lines = [line.rstrip() for line in output.splitlines() if line.strip()]
    if len(lines) <= max_lines:
        return "\n".join(lines)

    header = lines[:4]
    active = [
        line for line in lines[4:]
        if any(keyword in line.lower() for keyword in ACTIVE_ROW_KEYWORDS)
    ]
    tail = lines[-6:]

    selected = []
    seen = set()
    for line in header + active + tail:
        if line not in seen:
            selected.append(line)
            seen.add(line)
        if len(selected) >= max_lines:
            break

    omitted = len(lines) - len(selected)
    if omitted > 0:
        selected.append(f"... ({omitted} older/less relevant rows omitted)")
    return "\n".join(selected)

def role_contract(role, skill_path=None, full_skill_prompt=False):
    """Return full skill text for debugging or compact role contract for normal runs."""
    if full_skill_prompt and skill_path:
        return Path(skill_path).absolute().read_text()
    return COMPACT_ROLE_CONTRACTS.get(role, "")

# ── Customer demand ───────────────────────────────────────────────────────────

def generate_customer_orders(retailer_url, signal):
    try:
        response = httpx.get(f"{retailer_url}/api/catalog")
        catalog = response.json()
    except Exception as e:
        console.print(f"  [red]✗ Could not fetch catalog: {e}[/red]")
        return 0

    base = signal.get("base_demand", {"mean": 5, "variance": 2})
    modifier = signal.get("demand_modifier", 1.0)
    total = 0

    for item in catalog:
        model = item["sku"]
        price = item["retail_price"]
        base_price = item.get("wholesale_price", 0)
        if base_price <= 0:
            base_price = price / 1.3
        mean_orders = base["mean"] * modifier
        target_price = base_price * 1.3
        price_factor = max(0.2, 1.0 - (price - target_price) / target_price)
        adjusted_mean = mean_orders * price_factor
        n = max(0, int(random.gauss(adjusted_mean, base["variance"])))
        if n > 0:
            total += n
            console.print(f"  [cyan]{model}[/cyan]  [white]{n} orders[/white]")
            for _ in range(n):
                try:
                    httpx.post(f"{retailer_url}/api/customer-orders",
                               json={"customer": "auto", "model": model, "quantity": 1})
                except Exception as e:
                    console.print(f"  [red]✗ Order error: {e}[/red]")

    if total == 0:
        console.print("  [dim]No orders generated[/dim]")
    return total

# ── Prefetch ──────────────────────────────────────────────────────────────────

def prefetch_state(role, cwd, compact=True):
    """Run read-only CLI commands in parallel and return combined output."""
    cli = f"./{role}-cli"
    commands = {
        "manufacturer": ["stock", "sales orders", "capacity", "suppliers list"],
        "retailer":     ["stock", "customers orders", "purchase list", "price list"],
        "provider":     ["stock", "orders list --status pending"],
    }

    def run_cmd(cmd):
        try:
            result = subprocess.run(
                f"{cli} {cmd}", shell=True, capture_output=True, text=True, cwd=cwd, timeout=10
            )
            out = result.stdout.strip() or result.stderr.strip()
            if compact:
                out = compact_cli_output(out)
            return cmd, f"### {cli} {cmd}\n{out}"
        except Exception as e:
            return cmd, f"### {cli} {cmd}\nerror: {e}"

    cmds = commands.get(role, [])
    results = {}
    with ThreadPoolExecutor(max_workers=len(cmds)) as ex:
        for cmd, output in ex.map(lambda c: run_cmd(c), cmds):
            results[cmd] = output
    return "\n\n".join(results[c] for c in cmds)

# ── Agent runner ──────────────────────────────────────────────────────────────

def _run_agent_gemini(role, prompt, cwd, max_turns, model):
    """Agent loop for Gemini models using the google-genai SDK with function calling."""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY not set in .env or environment")
    if not _GEMINI_AVAILABLE:
        raise RuntimeError("google-genai not installed. Run: pip install google-genai")

    client = google_genai.Client(api_key=api_key)

    bash_fn = genai_types.FunctionDeclaration(
        name="bash",
        description="Run a shell command in the agent's working directory and return stdout+stderr.",
        parameters={
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    )
    tools = [genai_types.Tool(function_declarations=[bash_fn])]
    thinking_cfg = None
    if "2.5" in model:
        try:
            thinking_cfg = genai_types.ThinkingConfig(thinking_budget=0)
        except Exception:
            pass
    config = genai_types.GenerateContentConfig(
        tools=tools,
        max_output_tokens=1024,
        thinking_config=thinking_cfg,
    )

    history = []
    output_lines = []

    def _gemini_call(contents):
        delay = 15
        for attempt in range(4):
            try:
                return client.models.generate_content(
                    model=model, contents=contents, config=config
                )
            except Exception as e:
                if ("429" in str(e) or "503" in str(e)) and attempt < 3:
                    import re as _re
                    m = _re.search(r"retryDelay.*?(\d+)s", str(e))
                    time.sleep(int(m.group(1)) if m else delay)
                    delay *= 2
                else:
                    raise

    history.append(genai_types.Content(role="user", parts=[genai_types.Part(text=prompt)]))

    for _ in range(max_turns):
        response = _gemini_call(history)
        candidate = response.candidates[0]
        history.append(candidate.content)

        tool_calls = [p for p in candidate.content.parts if p.function_call]
        if not tool_calls:
            for p in candidate.content.parts:
                if p.text:
                    output_lines.append(p.text)
            break

        fn_responses = []
        for part in tool_calls:
            fc = part.function_call
            if fc.name == "bash":
                cmd = fc.args.get("command", "")
                result = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True, cwd=cwd
                )
                tool_output = result.stdout + result.stderr
                output_lines.append(f"$ {cmd}\n{tool_output}")
                fn_responses.append(
                    genai_types.Part(
                        function_response=genai_types.FunctionResponse(
                            name="bash", response={"output": tool_output}
                        )
                    )
                )

        history.append(genai_types.Content(role="user", parts=fn_responses))

    return "\n".join(output_lines)


def run_agent(
    role,
    skill_path,
    context,
    cwd,
    verbose=False,
    day_log=None,
    spinner=True,
    prefetched_state=None,
    model="gemini-3.1-flash-lite",
    full_skill_prompt=False,
):
    role_label = role.upper()
    role_colors = {"retailer": "magenta", "manufacturer": "blue", "provider": "green"}
    color = role_colors.get(role, "white")
    abs_skill_path = Path(skill_path).absolute() if skill_path else None

    state = prefetched_state if prefetched_state is not None else prefetch_state(role, cwd)
    day_val = json.loads(context).get("day", 0)
    skill_content = role_contract(role, abs_skill_path, full_skill_prompt)

    notes = []
    if role == "manufacturer":
        if day_val == 1:
            notes.append(
                "NOTE: This is Day 1. The capacity history has no previous days. "
                "Do NOT adjust prices today — the 2-day utilisation rule requires at least 2 days of history. Hold all prices."
            )
        notes.append(
            "NOTE: Supplier names are pre-fetched below under '### ./manufacturer-cli suppliers list'. "
            "Use those exact names when calling 'purchase create --supplier <name>'. Do not guess."
        )

    notes_block = ("\n\n" + "\n".join(notes)) if notes else ""

    prompt = (
        f"Your role and decision rules:\n{skill_content}\n\n"
        f"Today's context: {context}{notes_block}\n\n"
        f"Current state (already fetched — skip all read commands, go straight to decisions):\n{state}\n\n"
        "EFFICIENCY RULES:\n"
        "1. Treat the pre-fetched current state above as the required assessment step from your role rules.\n"
        "2. Do not run read-only commands (stock, orders, capacity, catalog, price list) unless a mutation fails and you need to diagnose it.\n"
        "3. Perform related mutation commands (purchase, release, price set, restock, etc.) in as few Bash turns as practical.\n"
        "4. Final output must be at most 3 bullets and under 120 words. Do not restate the full assessment.\n"
        "5. After mutations and the short summary, exit."
    )
    start_time = time.time()
    is_gemini = model.lower().startswith("gemini") or model.lower().startswith("gemma")

    try:
        env = os.environ.copy()
        env["PATH"] = "/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:" + env.get("PATH", "")

        max_turns = {"retailer": 6, "manufacturer": 8, "provider": 8}.get(role, 4)

        if spinner:
            spin = Spinner("dots", text=f"[bold {color}]{role_label}[/bold {color}] [dim]thinking...[/dim]")
            ctx = Live(spin, console=console, refresh_per_second=10)
        else:
            ctx = __import__("contextlib").nullcontext()
            console.print(f"  [dim]{role_label} thinking...[/dim]")

        if is_gemini:
            result_box = [None]
            exc_box = [None]

            def _gemini_thread():
                try:
                    result_box[0] = _run_agent_gemini(role, prompt, cwd, max_turns, model)
                except Exception as e:
                    exc_box[0] = e

            t = threading.Thread(target=_gemini_thread, daemon=True)
            with ctx:
                t.start()
                t.join(timeout=AGENT_TIMEOUT_SECONDS)

            if t.is_alive():
                raise TimeoutError(f"{role_label} timed out after {AGENT_TIMEOUT_SECONDS}s")
            if exc_box[0]:
                raise exc_box[0]
            stdout_content = result_box[0]
            return_code = 0
        else:
            cmd = [
                "claude", "--print", "--dangerously-skip-permissions",
                "--allowedTools", "Bash",
                "--model", model,
                "--max-turns", str(max_turns),
                prompt,
            ]
            stdout_lines = []
            with ctx:
                process = subprocess.Popen(
                    cmd,
                    shell=False,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=cwd,
                    env=env,
                    bufsize=1,
                )
                deadline = time.time() + AGENT_TIMEOUT_SECONDS
                while True:
                    line = process.stdout.readline()
                    if not line and process.poll() is not None:
                        break
                    if line:
                        stdout_lines.append(line)
                    if time.time() > deadline:
                        process.kill()
                        process.wait()
                        raise TimeoutError(f"{role_label} timed out after {AGENT_TIMEOUT_SECONDS}s")
            return_code = process.wait()
            stdout_content = "".join(stdout_lines)

        duration = time.time() - start_time

        if verbose:
            display_content = Markdown(stdout_content.strip())
        else:
            lines = [l.rstrip() for l in stdout_content.splitlines() if l.strip()]
            summary = "\n".join(lines[-3:]) if lines else "(no output)"
            display_content = Text(summary, style="dim")

        status_icon = "[green]✓[/green]" if return_code == 0 else "[red]✗[/red]"
        console.print(Panel(
            display_content,
            title=f"{status_icon} [bold {color}]{role_label}[/bold {color}]  [dim]{duration:.0f}s[/dim]",
            border_style=color,
            padding=(0, 1),
        ))

        if day_log:
            day_log.parent.mkdir(parents=True, exist_ok=True)
            header = f"=== {role_label} | context: {context} ===\n\n"
            with day_log.open("a") as f:
                f.write(header + stdout_content + "\n\n")

        if return_code != 0:
            console.print(f"  [red]✗ Agent exited with code {return_code}[/red]")
        elif not verbose:
            console.print(f"  [dim]Full log → {day_log}[/dim]")

        return stdout_content

    except Exception as e:
        err_str = str(e)
        if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
            import re as _re
            retry = _re.search(r"retryDelay.*?(\d+)s", err_str)
            limit = _re.search(r"limit.*?(\d+)", err_str)
            wait = int(retry.group(1)) if retry else 60
            for attempt in range(3):
                wait = max(wait, 5)
                limit_msg = f" (limit: {limit.group(1)} req/min)" if limit else ""
                console.print(f"  [yellow]✗ {role_label} rate-limited{limit_msg}. Retrying in {wait}s… (attempt {attempt+1}/3)[/yellow]")
                time.sleep(wait)
                try:
                    return run_agent(role, skill_path, context, cwd, verbose, day_log, False, prefetched_state, model, full_skill_prompt)
                except Exception as e2:
                    err_str = str(e2)
                    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                        retry = _re.search(r"retryDelay.*?(\d+)s", err_str)
                        wait = int(retry.group(1)) if retry else 60
                        continue
                    msg = f"✗ {role_label} error after retry: {e2}"
                    break
            else:
                msg = f"✗ {role_label} gave up after 3 rate-limit retries"
        else:
            msg = f"✗ {role_label} error: {e}"
        console.print(f"  [red]{msg}[/red]")
        if day_log:
            day_log.parent.mkdir(parents=True, exist_ok=True)
            with day_log.open("a") as f:
                f.write(f"=== {role_label} ===\n{msg}\n\n")
        return None

# ── Day advance ───────────────────────────────────────────────────────────────

def advance_all(config, signal):
    console.print("\n[bold]Advancing all services...[/bold]")
    lead_time_modifier = signal.get("lead_time_modifier", 1.0)
    provider_urls = {p["url"] for p in config["providers"]}

    all_urls = (
        [r["url"] for r in config["retailers"]] +
        [config["manufacturer"]["url"]] +
        [p["url"] for p in config["providers"]]
    )
    for url in all_urls:
        try:
            body = {"lead_time_modifier": lead_time_modifier} if url in provider_urls else {}
            httpx.post(f"{url}/api/day/advance", json=body)
            console.print(f"  [green]✓[/green] {url}")
        except Exception as e:
            console.print(f"  [red]✗[/red] {url}: {e}")

# ── Global state table ────────────────────────────────────────────────────────

def fetch_global_state(config):
    """Fetch stock/inventory from all three services and return a summary dict."""
    state = {"retailer": {}, "manufacturer": {}, "provider": {}}

    try:
        retailer_url = config["retailers"][0]["url"]
        r = httpx.get(f"{retailer_url}/api/inventory", timeout=5)
        if r.status_code == 200:
            state["retailer"].update(parse_retailer_inventory(r.json()))
    except Exception:
        pass

    # Manufacturer inventory — use CLI (stock endpoint requires warehouse capacity config not on the public API)
    try:
        mfr_path = config["manufacturer"]["path"]
        result = subprocess.run(
            "./manufacturer-cli stock", shell=True, capture_output=True, text=True,
            cwd=mfr_path, timeout=10
        )
        state["manufacturer"].update(parse_manufacturer_stock_output(result.stdout))
    except Exception:
        pass

    try:
        provider_url = config["providers"][0]["url"]
        id_to_name = {}
        rc = httpx.get(f"{provider_url}/api/catalog/", timeout=5)
        if rc.status_code == 200:
            for p in rc.json():
                id_to_name[p["id"]] = p["name"]
        r = httpx.get(f"{provider_url}/api/stock/", timeout=5)
        if r.status_code == 200:
            for item in r.json():
                pid = item.get("product_id")
                name = id_to_name.get(pid) or item.get("name") or str(pid)
                state["provider"][name] = item.get("quantity", 0)
    except Exception:
        pass

    return state

def print_global_state(config, day, signal):
    """Print a rich table showing inventory across all three services."""
    state = fetch_global_state(config)

    table = Table(
        title=f"[bold]Day {day} — Global Inventory Snapshot[/bold]",
        box=box.SIMPLE_HEAVY,
        show_lines=False,
        expand=False,
    )
    table.add_column("Service", style="bold", min_width=14)
    table.add_column("Product / Part", min_width=18)
    table.add_column("Stock", justify="right", min_width=8)

    def stock_color(qty):
        if qty <= 0:
            return "red"
        if qty < 10:
            return "yellow"
        return "green"

    for sku, qty in state["retailer"].items():
        color = stock_color(qty)
        table.add_row("RETAILER", sku, f"[{color}]{qty}[/{color}]")

    for product, qty in state["manufacturer"].items():
        color = stock_color(qty)
        table.add_row("MANUFACTURER", product, f"[{color}]{qty}[/{color}]")

    if not state["provider"]:
        table.add_row("PROVIDER", "[dim]—[/dim]", "[dim]—[/dim]")
    else:
        for part, qty in list(state["provider"].items())[:5]:  # cap at 5 parts
            color = stock_color(qty)
            table.add_row("PROVIDER", str(part), f"[{color}]{qty}[/{color}]")
        extra = len(state["provider"]) - 5
        if extra > 0:
            table.add_row("", f"[dim]…+{extra} more parts[/dim]", "")

    console.print(table)
    return state

# ── KPI summary & CSV ─────────────────────────────────────────────────────────

def orders_created_during_turn(orders, day):
    """Return customer orders generated during turn Day N.

    Retailer orders are created before services advance, so Day N demand has a
    retailer created_day of N-1.
    """
    demand_created_day = day - 1
    filtered_orders = []
    for order in orders:
        created_day = order.get("created_day")
        try:
            if int(created_day) == demand_created_day:
                filtered_orders.append(order)
        except (TypeError, ValueError):
            continue
    return filtered_orders

def print_kpi_and_log_csv(config, day, signal, scenario_name):
    """Print day-end KPI bar and append a row to logs/run.csv."""
    try:
        retailer_url = config["retailers"][0]["url"]
        resp = httpx.get(f"{retailer_url}/api/customer-orders", timeout=5)
        orders = resp.json() if resp.status_code == 200 else []
    except Exception:
        orders = []

    orders = orders_created_during_turn(orders, day)

    placed = len(orders)
    fulfilled = sum(1 for o in orders if o.get("status", "").lower() == "fulfilled")
    backordered = sum(1 for o in orders if o.get("status", "").lower() == "backordered")
    stockout = max(0, placed - fulfilled - backordered)
    fill_rate = (fulfilled / placed * 100) if placed else 0

    bar_filled = int(fill_rate / 5)  # 20 chars = 100%
    bar = "█" * bar_filled + "░" * (20 - bar_filled)
    fill_color = "green" if fill_rate >= 80 else ("yellow" if fill_rate >= 50 else "red")

    demand_mod = signal.get("demand_modifier", 1.0)
    supply_mod = signal.get("supply_modifier", 1.0)
    events = signal.get("events", [])
    event_str = ", ".join(e["name"] for e in events) if events else "—"

    console.print(
        f"\n  [bold]Day {day}[/bold]  [{fill_color}]{bar}[/{fill_color}] "
        f"[{fill_color}]{fill_rate:.0f}%[/{fill_color}] fulfillment  │  "
        f"[green]{fulfilled}✓[/green]  [yellow]{backordered}⏳[/yellow]  [red]{stockout}✗[/red]  "
        f"[dim]│ demand x{demand_mod:.1f}  supply x{supply_mod:.1f}  events: {event_str}[/dim]"
    )

    csv_path = Path("logs") / scenario_name / "run.csv"
    write_header = not csv_path.exists()
    with csv_path.open("a", newline="") as f:
        writer = csv.writer(f)
        if write_header:
            writer.writerow([
                "scenario", "day", "demand_mod", "supply_mod", "lead_mod",
                "price_sensitivity", "events",
                "orders_placed", "fulfilled", "backordered", "stockout", "fill_rate_pct",
            ])
        writer.writerow([
            scenario_name, day,
            round(signal.get("demand_modifier", 1.0), 3),
            round(signal.get("supply_modifier", 1.0), 3),
            round(signal.get("lead_time_modifier", 1.0), 3),
            signal.get("price_sensitivity", "normal"),
            event_str,
            placed, fulfilled, backordered, stockout, round(fill_rate, 1),
        ])

    return {"placed": placed, "fulfilled": fulfilled, "backordered": backordered, "stockout": stockout}

# ── Day banner ────────────────────────────────────────────────────────────────

def print_day_banner(day, total_days, signal, scenario_name):
    demand_mod = signal.get("demand_modifier", 1.0)
    supply_mod = signal.get("supply_modifier", 1.0)
    lead_mod = signal.get("lead_time_modifier", 1.0)
    price_sens = signal.get("price_sensitivity", "normal")
    events = signal.get("events", [])
    event_str = ", ".join(e["name"] for e in events) if events else "normal"

    def mod_str(val, invert=False):
        if abs(val - 1.0) < 0.05:
            return f"[dim]x{val:.1f}[/dim]"
        high = val > 1.0
        if invert:
            high = not high
        color = "green" if high else "red"
        arrow = "▲" if val > 1.0 else "▼"
        return f"[{color}]{arrow} x{val:.2f}[/{color}]"

    progress = f"{day}/{total_days}"
    banner_text = (
        f"[bold white] DAY {day} [/bold white][dim]({progress})[/dim]   "
        f"[dim]scenario:[/dim] {scenario_name}   "
        f"[dim]events:[/dim] {event_str}\n"
        f"[dim]demand[/dim] {mod_str(demand_mod)}   "
        f"[dim]supply[/dim] {mod_str(supply_mod, invert=True)}   "
        f"[dim]lead time[/dim] {mod_str(lead_mod, invert=True)}   "
        f"[dim]price sensitivity[/dim] {price_sens}"
    )

    console.print()
    console.print(Panel(banner_text, border_style="bright_blue", padding=(0, 2)))

# ── Main day runner ───────────────────────────────────────────────────────────

def run_day(
    day,
    total_days,
    config,
    scenario,
    scenario_name,
    verbose=False,
    output_dir=None,
    model="gemini-3.1-flash-lite",
    full_skill_prompt=False,

):
    signal = todays_signal(day, scenario)
    
    log_dir = output_dir if output_dir else Path("logs")
    log_dir.mkdir(exist_ok=True, parents=True)
    day_log = log_dir / f"day-{day:03d}.log"
    day_log.write_text(f"=== DAY {day} | scenario: {scenario_name} ===\n\n")

    print_day_banner(day, total_days, signal, scenario_name)

    console.print("\n[bold]Customer demand[/bold]")
    for retailer in config["retailers"]:
        generate_customer_orders(retailer["url"], signal)

    if day == 1:
        # Seed a random Day 0 purchase order so manufacturer has something to process on Day 1
        retailer_cfg = config["retailers"][0]
        classic_qty = random.randint(5, 15)
        pro_qty = random.randint(3, 10)
        for model_sku, qty in [("P3D-Classic", classic_qty), ("P3D-Pro", pro_qty)]:
            subprocess.run(
                f"./retailer-cli purchase create {model_sku} {qty}",
                shell=True, cwd=retailer_cfg["path"], capture_output=True
            )
        console.print(f"  [dim]Seeded Day 0 orders: {classic_qty}× Classic, {pro_qty}× Pro[/dim]")

    console.print("\n[bold]Agent decisions[/bold]")

    # 1. Prefetch state for all agents at once
    all_agent_roles = [
        ("retailer", config["retailers"][0]["path"]),
        ("manufacturer", config["manufacturer"]["path"]),
    ] + [
        ("provider", p["path"]) for p in config["providers"]
    ]
    
    with ThreadPoolExecutor(max_workers=len(all_agent_roles)) as prefetch_ex:
        prefetch_futures = {
            role: prefetch_ex.submit(prefetch_state, role, path, not full_skill_prompt)
            for role, path in all_agent_roles
        }
        prefetched = {role: f.result() for role, f in prefetch_futures.items()}

    # 2. Run all three agents in parallel (manufacturer sees yesterday's retailer orders)
    all_agents = []
    for retailer in config["retailers"]:
        all_agents.append(("retailer", retailer.get("skill"), retailer["path"]))
    for provider in config["providers"]:
        all_agents.append(("provider", provider.get("skill"), provider["path"]))
    mfr = config["manufacturer"]
    all_agents.append(("manufacturer", mfr.get("skill"), mfr["path"]))

    executor = ThreadPoolExecutor(max_workers=len(all_agents))
    futures = {
        executor.submit(run_agent, role, skill, json.dumps(signal), path,
                        verbose, day_log, False, prefetched.get(role), model, full_skill_prompt): role
        for role, skill, path in all_agents
    }
    try:
        for future in as_completed(futures):
            future.result()
    except KeyboardInterrupt:
        executor.shutdown(wait=False, cancel_futures=True)
        raise
    else:
        executor.shutdown(wait=False)

    advance_all(config, signal)
    print_global_state(config, day, signal)
    print_kpi_and_log_csv(config, day, signal, scenario_name)

# ── Programmatic entry point ──────────────────────────────────────────────────

def run_simulation(
    config_json,
    scenario_json,
    days,
    start_day=1,
    model="gemini-3.1-flash-lite",
    verbose=False,
    full_skill_prompt=False,
    progress_cb=None,
    cancel_check=None,
):
    """Run a full simulation programmatically.

    progress_cb(msg: str) is called for each log line so callers (e.g. the API
    server) can stream output without capturing stdout.  Defaults to console.print.
    """
    global console
    import re as _re

    output_dir = Path("logs") / Path(scenario_json).stem
    output_dir.mkdir(exist_ok=True, parents=True)
    _run_log_path = output_dir / "run.log"
    _run_log = _run_log_path.open("w" if start_day == 1 else "a")

    def _strip_ansi(s: str) -> str:
        return _re.sub(r"\x1b\[[0-9;]*m", "", s)

    class _TeeWriter:
        """Writes to both a log file (ANSI-stripped) and an optional callback."""
        def __init__(self, cb=None):
            self._cb = cb
            self._buf = ""

        def write(self, text):
            self._buf += text
            while "\n" in self._buf:
                line, self._buf = self._buf.split("\n", 1)
                _run_log.write(_strip_ansi(line) + "\n")
                _run_log.flush()
                if self._cb:
                    self._cb(line)

        def flush(self):
            if self._buf.strip():
                _run_log.write(_strip_ansi(self._buf) + "\n")
                _run_log.flush()
                if self._cb:
                    self._cb(self._buf)
                self._buf = ""

    if progress_cb:
        console = Console(file=_TeeWriter(progress_cb), force_terminal=True, width=150, highlight=False)
    else:
        console = Console(file=_TeeWriter(), force_terminal=True, width=150, highlight=False)

    _cb = progress_cb or (lambda msg: None)  # explicit _cb calls now redundant — console handles all

    config = load_config(config_json)
    scenario = load_scenario(scenario_json)
    scenario_name = Path(scenario_json).stem

    if start_day < 1 or start_day > days:
        raise ValueError("start_day must be between 1 and days")

    console.print(f"START scenario={scenario_name} days={start_day}-{days} model={model}")

    if start_day == 1:
        csv_path = Path("logs") / scenario_name / "run.csv"
        if csv_path.exists():
            csv_path.unlink()
        # Clear stale day logs and run/summary logs for this scenario so only the latest run is shown
        for f in output_dir.glob("day-*.log"):
            f.unlink()
        for fname in ("run.log", "summary.log"):
            p = output_dir / fname
            if p.exists():
                p.unlink()

    run_start = time.time()
    for day in range(start_day, days + 1):
        if cancel_check and cancel_check():
            console.print(f"CANCELLED after day {day - 1}")
            break
        console.print(f"DAY {day}/{days}")
        run_day(
            day, days, config, scenario, scenario_name,
            verbose=verbose, output_dir=output_dir,
            model=model, full_skill_prompt=full_skill_prompt,
        )
        console.print(f"DAY_DONE {day}/{days}")

    run_duration = time.time() - run_start

    console.print("Backing up databases…")
    for svc in ("provider", "manufacturer", "retailer"):
        src = Path(f"{svc}/data/{svc}.db")
        if src.exists():
            shutil.copy(src, output_dir / f"{svc}.db")

    if _VISUALIZE_AVAILABLE:
        console.print("Generating charts…")
        try:
            generate_charts(scenario_name, str(output_dir))
            console.print(f"Charts saved to {output_dir}/charts/")
        except Exception as e:
            console.print(f"WARNING chart generation failed: {e}")

    csv_path = Path("logs") / scenario_name / "run.csv"
    kpi_rows = []
    if csv_path.exists():
        with csv_path.open() as f:
            kpi_rows = list(csv.DictReader(f))

    mins, secs = divmod(int(run_duration), 60)
    duration_str = f"{mins}m {secs}s" if mins else f"{secs}s"
    console.print(f"DONE duration={duration_str} scenario={scenario_name}")

    # Write summary.log
    if kpi_rows:
        summary_log = output_dir / "summary.log"
        lines = [
            f"Run Summary — {scenario_name}\n",
            "=" * 60 + "\n",
            f"Duration: {duration_str}  |  Model: {model}  |  Days: {start_day}–{days}\n\n",
            f"{'Day':>4}  {'Events':<28}  {'Orders':>6}  {'Fill':>5}  {'Back':>5}  {'Lost':>5}  {'Fill%':>6}\n",
            "-" * 60 + "\n",
        ]
        for r in kpi_rows:
            lines.append(
                f"{r['day']:>4}  {r['events']:<28}  {r['orders_placed']:>6}  "
                f"{r['fulfilled']:>5}  {r['backordered']:>5}  {r['stockout']:>5}  "
                f"{float(r['fill_rate_pct']):>5.1f}%\n"
            )
        total_orders = sum(int(r["orders_placed"]) for r in kpi_rows)
        total_fill   = sum(int(r["fulfilled"])     for r in kpi_rows)
        total_back   = sum(int(r["backordered"])   for r in kpi_rows)
        total_lost   = sum(int(r["stockout"])      for r in kpi_rows)
        avg_fill = (total_fill / total_orders * 100) if total_orders else 0
        lines += [
            "-" * 60 + "\n",
            f"{'TOTAL':>4}  {'':28}  {total_orders:>6}  {total_fill:>5}  "
            f"{total_back:>5}  {total_lost:>5}  {avg_fill:>5.1f}%\n",
        ]
        summary_log.write_text("".join(lines))
        console.print(f"  Summary log → {summary_log}")

    if progress_cb:
        console = Console()

    _run_log.close()

    return {
        "scenario": scenario_name,
        "days_run": days - start_day + 1,
        "duration_seconds": round(run_duration, 1),
        "kpi_rows": kpi_rows,
        "output_dir": str(output_dir),
    }


# ── CLI ───────────────────────────────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(description="Run the DGSI turn engine simulation.")
    parser.add_argument("config_json", help="Config JSON path")
    parser.add_argument("scenario_json", help="Scenario JSON path")
    parser.add_argument("days", type=int, help="Number of days to simulate")
    parser.add_argument("-v", "--verbose", action="store_true",
                        help="Print full agent output (default: compact 3-line summary)")
    parser.add_argument("--model", default="gemini-3.1-flash-lite",
                        help="LLM model for agents. Claude: 'claude-haiku-4-5-20251001'. "
                             "Gemini/Gemma (requires GEMINI_API_KEY): 'gemini-3.1-flash-lite', 'gemma-4-26b-a4b-it', etc.")
    parser.add_argument("--start-day", type=int, default=1,
                        help="First simulated day to run, for resuming/chunking long scenarios (default: 1)")
    parser.add_argument("--full-skill-prompt", action="store_true",
                        help="Send full skill markdown to agents instead of compact role contracts")
    return parser.parse_args()

if __name__ == "__main__":
    args = parse_args()

    config = load_config(args.config_json)
    scenario = load_scenario(args.scenario_json)
    scenario_name = Path(args.scenario_json).stem

    console.print(Panel(
        f"[bold]Config:[/bold] {args.config_json}   "
        f"[bold]Scenario:[/bold] {scenario_name}   "
        f"[bold]Days:[/bold] {args.start_day}-{args.days}   "
        f"[bold]Model:[/bold] {args.model}   "
        f"[bold]Mode:[/bold] {'verbose' if args.verbose else 'compact'}   "
        f"[bold]Prompt:[/bold] {'full skill' if args.full_skill_prompt else 'compact role'}",
        title="[bold cyan] DGSI Turn Engine [/bold cyan]",
        border_style="cyan",
    ))

    result = run_simulation(
        args.config_json,
        args.scenario_json,
        args.days,
        start_day=args.start_day,
        model=args.model,
        verbose=args.verbose,
        full_skill_prompt=args.full_skill_prompt,
    )

    run_duration = result["duration_seconds"]
    output_dir = Path(result["output_dir"])
    scenario_name = result["scenario"]

    mins, secs = divmod(int(run_duration), 60)
    duration_str = f"{mins}m {secs}s" if mins else f"{secs}s"
    console.rule(f"[bold green] Simulation complete — {duration_str} [/bold green]", style="green")

    csv_path = Path("logs") / scenario_name / "run.csv"
    if csv_path.exists():
        with csv_path.open() as f:
            rows = list(csv.DictReader(f))
        if rows:
            summary = Table(
                title=f"[bold]Run Summary — {scenario_name}[/bold]",
                box=box.SIMPLE_HEAVY,
                show_lines=False,
                expand=False,
            )
            summary.add_column("Day", justify="right", min_width=4)
            summary.add_column("Events / Conditions", min_width=24, no_wrap=True)
            summary.add_column("Orders", justify="right", min_width=7)
            summary.add_column("Fulfilled", justify="right", min_width=9)
            summary.add_column("Backordered", justify="right", min_width=11)
            summary.add_column("Lost", justify="right", min_width=6)
            summary.add_column("Fill rate", justify="right", min_width=9)

            def mod_tag(label, val, invert=False):
                v = float(val)
                if abs(v - 1.0) < 0.05:
                    return ""
                high = v > 1.0
                if invert:
                    high = not high
                color = "green" if high else "red"
                arrow = "▲" if v > 1.0 else "▼"
                return f" [{color}]{label}{arrow}x{v:.2f}[/{color}]"

            for r in rows:
                fill = float(r["fill_rate_pct"])
                fill_color = "green" if fill >= 95 else ("yellow" if fill >= 70 else "red")
                mods = mod_tag("D", r['demand_mod']) + mod_tag("S", r['supply_mod'], invert=True)
                event_cell = r["events"] + (f"  [dim]{mods.strip()}[/dim]" if mods.strip() else "")
                summary.add_row(
                    r["day"],
                    event_cell,
                    r["orders_placed"],
                    f"[green]{r['fulfilled']}[/green]",
                    f"[yellow]{r['backordered']}[/yellow]" if int(r["backordered"]) else f"[dim]{r['backordered']}[/dim]",
                    f"[red]{r['stockout']}[/red]" if int(r["stockout"]) else f"[dim]{r['stockout']}[/dim]",
                    f"[{fill_color}]{fill:.0f}%[/{fill_color}]",
                )
            total_orders = sum(int(r["orders_placed"]) for r in rows)
            total_fill = sum(int(r["fulfilled"]) for r in rows)
            total_back = sum(int(r["backordered"]) for r in rows)
            total_lost = sum(int(r["stockout"]) for r in rows)
            avg_fill = (total_fill / total_orders * 100) if total_orders else 0
            fill_color = "green" if avg_fill >= 95 else ("yellow" if avg_fill >= 70 else "red")
            summary.add_section()
            summary.add_row(
                "[bold]TOTAL[/bold]",
                "",
                f"[bold]{total_orders}[/bold]",
                f"[bold green]{total_fill}[/bold green]",
                f"[bold yellow]{total_back}[/bold yellow]" if total_back else f"[dim]{total_back}[/dim]",
                f"[bold red]{total_lost}[/bold red]" if total_lost else f"[dim]{total_lost}[/dim]",
                f"[bold {fill_color}]{avg_fill:.0f}%[/bold {fill_color}]",
            )
            console.print(summary)

    console.print(f"  KPI log → logs/{scenario_name}/run.csv")
    console.print()
