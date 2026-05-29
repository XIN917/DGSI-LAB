const PAGE = document.body.dataset.page;
const REFRESH = (parseInt(document.body.dataset.refresh, 10) || 2) * 1000;
const TIER_COLORS = {provider: "#38bdf8", manufacturer: "#a78bfa", retailer: "#f472b6"};
const PALETTE = ["#38bdf8", "#a78bfa", "#f472b6", "#34d399", "#fbbf24", "#f87171", "#22d3ee", "#c084fc"];
const root = document.getElementById("root");
const badge = document.getElementById("livebadge");

document.querySelectorAll("[data-nav]").forEach(a => {
  if (a.dataset.nav === PAGE) a.classList.add("active");
});

function barClass(stock, cap) {
  if (stock === 0) return "err";
  if (cap && stock <= cap * 0.20) return "warn";
  return "ok";
}
function pct(stock, cap, peak) {
  const max = cap || peak || stock || 1;
  return Math.max(2, Math.min(100, (stock / max) * 100));
}
function fmt(n) { return n == null ? "–" : (Number.isInteger(n) ? n : Number(n).toFixed(1)); }
function statusClass(s) { return "status-" + String(s || "").toLowerCase(); }

async function tick() {
  try {
    const res = await fetch("/api/state");
    const data = await res.json();
    const d = data.day == null ? "–" : data.day;
    const dt = data.day_total ? ` / ${data.day_total}` : "";
    badge.textContent = `● LIVE · ${data.scenario || "no scenario"} · Day ${d}${dt}`;
    badge.classList.remove("down");
    render(data);
  } catch (e) {
    badge.textContent = "● disconnected — is the dashboard server running?";
    badge.classList.add("down");
  }
}

function render(data) {
  if (PAGE === "overview") renderOverview(data);
  else renderDetail(PAGE, data);
}

function renderOverview(data) {
  const k = data.kpis, ev = data.events || {};
  const tierCard = (name, tier) => {
    if (!tier.online) return `<div class="card ${name} offline"><h3>${name.toUpperCase()}</h3><p class="muted">offline</p></div>`;
    if (tier.busy) return `<div class="card ${name}"><h3>${name.toUpperCase()}</h3><p class="muted">busy…</p></div>`;
    const top = tier.items.slice(0, 3).map(i =>
      `<div>${i.name} <b>${fmt(i.stock)}</b></div>`).join("");
    const extra = name === "manufacturer" && tier.extra.utilisation_pct != null
      ? `<div class="muted">util ${fmt(tier.extra.utilisation_pct)}%</div>` : "";
    return `<div class="card ${name}"><h3>${name.toUpperCase()}</h3>${top}${extra}
      <svg class="sparkline" data-spark="${name}"></svg></div>`;
  };
  const arrow = (n) => `<div class="arrow">▶▶<div class="n">${fmt(n)}</div><div class="muted">in transit</div></div>`;
  root.innerHTML = `
    <div class="ov-section-title">Supply Chain Status</div>
    <div class="kpibar">
      <span>fill-rate <b>${fmt(k.fill_rate)}%</b></span>
      <span>backlog <b>${fmt(k.backlog)}</b></span>
      <span>production util <b>${fmt(k.production_util)}%</b></span>
      ${ev.demand_mod != null ? `<span>events <b>×${ev.demand_mod} dmd · ×${ev.supply_mod} sup</b></span>` : ""}
    </div>
    <div class="pipeline">
      ${tierCard("provider", data.tiers.provider)}
      ${arrow(data.tiers.provider.in_transit_out)}
      ${tierCard("manufacturer", data.tiers.manufacturer)}
      ${arrow(data.tiers.manufacturer.in_transit_out)}
      ${tierCard("retailer", data.tiers.retailer)}
    </div>
    <div class="alerts">
      <span class="muted">ALERTS&nbsp;&nbsp;</span>
      ${data.alerts.length ? data.alerts.map(a => `<span class="a ${a.level}">⚠ ${a.text}</span>`).join(" · ")
                            : '<span class="muted">none</span>'}
    <div id="ov-charts"></div>
    </div>`;
  ["provider", "manufacturer", "retailer"].forEach(name => {
    const svg = root.querySelector(`[data-spark="${name}"]`);
    const hist = (data.history[name] || {}).series || {};
    const stockSeries = hist.stock || hist.finished_stock || {};
    const allSeries = Object.values(stockSeries);
    if (svg && allSeries.length) drawSparklineMulti(svg, allSeries, TIER_COLORS[name]);
  });

  // Per-service charts (same as detail pages)
  const ovCharts = document.getElementById("ov-charts");
  if (ovCharts) {
    const TIER_LABELS = {provider: "PROVIDER", manufacturer: "MANUFACTURER", retailer: "RETAILER"};
    ovCharts.innerHTML = `<div class="ov-charts-title"><span>PERFORMANCE CHARTS</span></div>` +
    ["provider", "manufacturer", "retailer"].map(name => {
      const hist = (data.history[name] || {});
      return `<div class="panel ov-tier-panel" data-ovtier="${name}">
        <h3 style="color:var(--${name === 'provider' ? 'accent' : name === 'manufacturer' ? 'mfr' : 'ret'})">${TIER_LABELS[name]}</h3>
        ${chartsBlock(name, hist, data)}
      </div>`;
    }).join("");
    ["provider", "manufacturer", "retailer"].forEach(name => {
      const hist = (data.history[name] || {});
      const panel = ovCharts.querySelector(`[data-ovtier="${name}"]`);
      if (!panel) return;
      drawAllCharts(name, hist, data, panel);
    });
  }
}

function kpiTiles(name, tier) {
  const items = tier.items || [];
  const total = items.reduce((s, i) => s + (i.stock || 0), 0);
  const low = items.filter(i => i.capacity && i.stock <= i.capacity * 0.20).length
            + items.filter(i => i.stock === 0).length;
  const pending = (tier.orders || []).filter(o => /pending|released|shipped|waiting/i.test(o.status)).length;
  if (name === "manufacturer") {
    return tileRow([["finished models", items.filter(i => i.kind === "finished").length],
      ["sales pending", fmt(tier.extra.sales_pending)], ["sales completed", fmt(tier.extra.sales_completed)],
      ["production util %", fmt(tier.extra.utilisation_pct)]]);
  }
  return tileRow([["items", items.length], ["total units", fmt(total)],
    ["low / out", low], ["orders open", pending]]);
}
function tileRow(pairs) {
  return `<div class="tiles">${pairs.map(([l, v]) =>
    `<div class="tile">${l}<div class="big">${v}</div></div>`).join("")}</div>`;
}
function stockPanel(name, tier, hist) {
  const peak = (hist || {}).peak || {};
  const rows = (tier.items || []).map(i => {
    const cls = barClass(i.stock, i.capacity);
    const width = pct(i.stock, i.capacity, peak[i.name]);
    const cap = i.capacity ? `/ ${fmt(i.capacity)}` : (peak[i.name] ? `/ ${fmt(peak[i.name])}` : "");
    return `<div class="stockrow"><span class="name">${i.name}</span>
      <span class="bar"><span class="fill ${cls}" style="width:${width}%"></span>
        <span class="lbl">${fmt(i.stock)} ${cap}</span></span>
      <span class="num">${i.price != null ? "€" + fmt(i.price) : ""}</span>
      <span class="num">${i.lead != null ? i.lead + "d" : ""}</span></div>`;
  }).join("");
  return `<div class="panel"><h3>STOCK · CATALOG · PRICE</h3>${rows || '<p class="muted">no items</p>'}</div>`;
}
function orderPanel(name, tier) {
  if (name === "manufacturer") {
    const e = tier.extra || {};
    return `<div class="panel orderlist"><h3>SALES ORDERS (from Retailer)</h3>
      <div class="o"><span>pending</span><span class="status-pending">${fmt(e.sales_pending)}</span></div>
      <div class="o"><span>completed</span><span class="status-completed">${fmt(e.sales_completed)}</span></div>
      <p class="muted">counts from daily metrics</p></div>`;
  }
  const title = {provider: "ORDERS (from Manufacturer)", retailer: "CUSTOMER ORDERS"}[name];
  const rows = (tier.orders || []).slice(0, 25).map(o => {
    const eta = o.eta != null ? ` · ${name === "retailer" ? "fulfilled d" : "ETA d"}${o.eta}` : "";
    return `<div class="o"><span><b>#${o.id}</b> &nbsp; ${o.label} ×${fmt(o.qty)}</span>
      <span class="${statusClass(o.status)}">${(o.status || "").toUpperCase()}${eta}</span></div>`;
  }).join("");
  return `<div class="panel orderlist"><h3>${title}</h3>${rows || '<p class="muted">no orders</p>'}</div>`;
}
function renderDetail(name, data) {
  const tier = data.tiers[name];
  if (!tier || !tier.online) {
    root.innerHTML = `<p class="muted">${name} is offline — start the service with: scripts/start_all.sh</p>`;
    return;
  }
  if (tier.busy) {
    root.innerHTML = `<p class="muted">${name} is busy (simulation running) — data will refresh shortly.</p>`;
    return;
  }
  const hist = data.history[name] || {};
  root.innerHTML = kpiTiles(name, tier) + stockPanel(name, tier, hist)
    + orderPanel(name, tier) + chartsBlock(name, hist, data);
  drawAllCharts(name, hist, data);
}

function _bounds(seriesMap) {
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  Object.values(seriesMap).forEach(pts => pts.forEach(([x, y]) => {
    minX = Math.min(minX, x); maxX = Math.max(maxX, x); minY = Math.min(minY, y); maxY = Math.max(maxY, y);
  }));
  if (!isFinite(minX)) return null;
  if (minY > 0) minY = 0;
  if (maxY === minY) maxY = minY + 1;
  return {minX, maxX, minY, maxY};
}
function _lineChart(svg, seriesMap, yUnit = "units") {
  const W = svg.clientWidth || 600, H = svg.clientHeight || 200, pad = {l: 44, r: 10, t: 18, b: 30};
  const b = _bounds(seriesMap);
  svg.innerHTML = "";
  if (!b) { svg.innerHTML = `<text x="10" y="20" fill="#64748b">no history yet</text>`; return []; }
  const sx = x => pad.l + ((x - b.minX) / Math.max(1, b.maxX - b.minX)) * (W - pad.l - pad.r);
  const sy = y => H - pad.b - ((y - b.minY) / (b.maxY - b.minY)) * (H - pad.t - pad.b);
  const ns = "http://www.w3.org/2000/svg";

  // Y-axis label
  const yl = document.createElementNS(ns, "text");
  yl.setAttribute("x", 10); yl.setAttribute("y", pad.t + (H - pad.t - pad.b) / 2);
  yl.setAttribute("fill", "#475569"); yl.setAttribute("font-size", "10");
  yl.setAttribute("text-anchor", "middle"); yl.setAttribute("transform", `rotate(-90, 10, ${pad.t + (H - pad.t - pad.b) / 2})`);
  yl.textContent = yUnit; svg.appendChild(yl);

  // Y-axis ticks
  [b.minY, (b.minY + b.maxY) / 2, b.maxY].forEach(v => {
    const t = document.createElementNS(ns, "text"); t.setAttribute("x", pad.l - 4); t.setAttribute("y", sy(v) + 4);
    t.setAttribute("fill", "#475569"); t.setAttribute("font-size", "10"); t.setAttribute("text-anchor", "end");
    t.textContent = Math.round(v); svg.appendChild(t);
    const g = document.createElementNS(ns, "line"); g.setAttribute("x1", pad.l); g.setAttribute("x2", W - pad.r);
    g.setAttribute("y1", sy(v)); g.setAttribute("y2", sy(v)); g.setAttribute("stroke", "#1e293b"); svg.appendChild(g);
  });

  // X-axis label
  const xl = document.createElementNS(ns, "text");
  xl.setAttribute("x", pad.l + (W - pad.l - pad.r) / 2); xl.setAttribute("y", H - 2);
  xl.setAttribute("fill", "#475569"); xl.setAttribute("font-size", "10"); xl.setAttribute("text-anchor", "middle");
  xl.textContent = "Day"; svg.appendChild(xl);

  // X-axis ticks
  const xTicks = Math.min(6, b.maxX - b.minX + 1);
  for (let i = 0; i <= xTicks; i++) {
    const v = Math.round(b.minX + (i / xTicks) * (b.maxX - b.minX));
    const t = document.createElementNS(ns, "text"); t.setAttribute("x", sx(v)); t.setAttribute("y", H - pad.b + 14);
    t.setAttribute("fill", "#475569"); t.setAttribute("font-size", "10"); t.setAttribute("text-anchor", "middle");
    t.textContent = v; svg.appendChild(t);
  }

  const legend = [];
  Object.entries(seriesMap).forEach(([key, pts], idx) => {
    const color = PALETTE[idx % PALETTE.length]; legend.push([key, color]);
    const d = pts.map(([x, y], i) => `${i ? "L" : "M"}${sx(x).toFixed(1)},${sy(y).toFixed(1)}`).join(" ");
    const pl = document.createElementNS(ns, "path"); pl.setAttribute("d", d); pl.setAttribute("fill", "none");
    pl.setAttribute("stroke", color); pl.setAttribute("stroke-width", "1.8"); svg.appendChild(pl);
  });
  return legend;
}
function drawSparklineMulti(svg, seriesArr, baseColor) {
  const W = svg.clientWidth || 160, H = svg.clientHeight || 24;
  const allPts = seriesArr.flat();
  if (!allPts.length) return;
  const xs = allPts.map(p => p[0]), ys = allPts.map(p => p[1]);
  const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys, minY + 1);
  const sx = x => ((x - minX) / Math.max(1, maxX - minX)) * W;
  const sy = y => H - ((y - minY) / (maxY - minY)) * H;
  svg.innerHTML = seriesArr.map((pts, i) => {
    const color = i === 0 ? baseColor : PALETTE[i % PALETTE.length];
    const d = pts.map((p, j) => `${j ? "L" : "M"}${sx(p[0]).toFixed(1)},${sy(p[1]).toFixed(1)}`).join(" ");
    return `<path d="${d}" fill="none" stroke="${color}" stroke-width="1.5" opacity="0.85"/>`;
  }).join("");
}
function drawSparkline(svg, pts, color) {
  const W = svg.clientWidth || 160, H = svg.clientHeight || 24;
  const xs = pts.map(p => p[0]), ys = pts.map(p => p[1]);
  const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys, minY + 1);
  const sx = x => ((x - minX) / Math.max(1, maxX - minX)) * W, sy = y => H - ((y - minY) / (maxY - minY)) * H;
  const d = pts.map((p, i) => `${i ? "L" : "M"}${sx(p[0]).toFixed(1)},${sy(p[1]).toFixed(1)}`).join(" ");
  svg.innerHTML = `<path d="${d}" fill="none" stroke="${color}" stroke-width="1.5"/>`;
}
function _chartDefs(name, data) {
  if (name === "provider") return [["Stock over time (per part)", "stock", "units"], ["Tier-1 price over time", "price", "€"]];
  if (name === "manufacturer") return [["Finished stock", "finished_stock", "units"], ["Wholesale price", "wholesale_price", "€"],
    ["Production utilisation %", "utilisation", "%"]];
  return [["Stock over time (per SKU)", "stock", "units"], ["Retail price over time", "retail_price", "€"], ["__fill__", "fill", "%"]];
}
function chartsBlock(name, hist, data) {
  const defs = _chartDefs(name, data);
  return `<div class="charts">` + defs.map(([title], i) =>
    `<div class="chart"><h4>${title === "__fill__" ? "Fill-rate % over time" : title}</h4>
      <svg data-chart="${i}"></svg><div class="legend" data-legend="${i}"></div></div>`).join("") + `</div>`;
}
function drawAllCharts(name, hist, data, container = root) {
  const defs = _chartDefs(name, data);
  defs.forEach(([title, metric, yUnit], i) => {
    const svg = container.querySelector(`[data-chart="${i}"]`); if (!svg) return;
    let seriesMap;
    if (metric === "fill") seriesMap = data.fill_rate_series.length ? {"fill-rate": data.fill_rate_series} : {};
    else seriesMap = (hist.series || {})[metric] || {};
    const legend = _lineChart(svg, seriesMap, yUnit);
    const box = container.querySelector(`[data-legend="${i}"]`);
    if (box) box.innerHTML = legend.map(([k, c]) => `<span style="color:${c}">${k}</span>`).join("");
  });
}

if (PAGE !== "simulation") {
  setInterval(tick, REFRESH);
  tick();
} else {
  initSimPage();
}

// ── Simulation page ────────────────────────────────────────────────────────────

async function initSimPage() {
  badge.textContent = "● Simulation Control";
  badge.classList.remove("down");

  let scenarios = [], models = [], eventSource = null;

  // Persist terminal state across page navigations via sessionStorage
  const _SS_RUN  = "sim_current_run_id";
  const _SS_LINES = "sim_term_lines";
  let currentRunId = sessionStorage.getItem(_SS_RUN) || null;
  let _termLines = JSON.parse(sessionStorage.getItem(_SS_LINES) || "[]");

  function _saveLines() {
    sessionStorage.setItem(_SS_LINES, JSON.stringify(_termLines.slice(-2000)));
  }

  try {
    [scenarios, models] = await Promise.all([
      fetch("/api/sim/scenarios").then(r => r.json()),
      fetch("/api/sim/models").then(r => r.json()),
    ]);
  } catch(e) {
    root.innerHTML = `<p class="muted" style="color:var(--err)">Cannot reach api_server on :8000 — run: venv/bin/python api_server.py</p>`;
    return;
  }

  root.innerHTML = `
    <div class="sim-layout">

      <div class="sim-controls">
        <div class="sim-controls-header">
          <h3>Run Simulation</h3>
          <div class="sim-actions">
            <button class="sim-btn start" id="sc-start">▶ Start</button>
            <button class="sim-btn stop" id="sc-stop" disabled>■ Stop</button>
            <button class="sim-btn" id="sc-reset" style="background:#334155;color:var(--text)">↺ Reset</button>
            <div id="sc-status" class="run-status" style="display:none"></div>
          </div>
        </div>
        <div class="sim-advice">💡 Always <b>Reset</b> before starting a new run — services carry state between runs. Skip reset only when resuming a paused scenario with <i>Start day &gt; 1</i>.</div>
        <div class="sim-fields">
          <div class="sim-field">
            <label>Scenario</label>
            <select id="sc-scenario">${scenarios.map(s =>
              `<option value="${s.name}">${s.name}</option>`).join("")}</select>
          </div>
          <div class="sim-field">
            <label>Model</label>
            <select id="sc-model">${models.map(m =>
              `<option value="${m.id}"${m.default?" selected":""}>${m.label}</option>`).join("")}</select>
          </div>
          <div class="sim-field" style="max-width:100px">
            <label>Start Day</label>
            <input type="number" id="sc-startday" value="1" min="1" max="50">
          </div>
          <div class="sim-field" style="max-width:100px">
            <label>End Day</label>
            <input type="number" id="sc-days" value="15" min="1" max="50">
          </div>
        </div>
      </div>

      <div class="sim-runs">
        <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:8px">
          <h3 style="margin:0">Recent Runs</h3>
          <div style="display:flex;gap:6px">
            <button class="sim-btn sim-btn-del-sel" id="sc-del-selected" disabled>Delete Selected</button>
            <button class="sim-btn sim-btn-del-all" id="sc-del-all">Delete All</button>
          </div>
        </div>
        <div class="runs-list" id="sc-runs"><span class="muted">No runs yet.</span></div>
      </div>

      <div class="sim-terminal">
        <div class="sim-terminal-header">Terminal output</div>
        <div id="sc-term-body" style="flex:1;min-height:0"></div>
      </div>

      <div class="sim-logs-row">
        <div class="sim-logs">
          <h3>Agent logs</h3>
          <select id="sc-log-filter" style="width:100%;background:#1e293b;border:1px solid var(--line);color:var(--text);padding:5px 8px;border-radius:5px;font-family:inherit;font-size:12px;margin-bottom:8px">
            <option value="">— pick a scenario —</option>
          </select>
          <ul class="log-list" id="sc-loglist"></ul>
        </div>
        <div class="sim-logs">
          <h3>Log content</h3>
          <div class="log-content" id="sc-logcontent" style="display:block;max-height:300px">
            <span class="muted">Select a log file on the left.</span>
          </div>
        </div>
      </div>

      <div class="sim-logs">
        <h3>Run summaries</h3>
        <div id="sc-summaries" style="display:flex;gap:8px;flex-wrap:wrap;margin-bottom:10px"></div>
        <div class="log-content" id="sc-summarycontent" style="display:block;max-height:400px">
          <span class="muted">Select a summary above.</span>
        </div>
      </div>

    </div>`;

  const elScenario  = document.getElementById("sc-scenario");
  const elModel     = document.getElementById("sc-model");
  const elDays      = document.getElementById("sc-days");
  const elStartDay  = document.getElementById("sc-startday");
  const elStart     = document.getElementById("sc-start");
  const elStop      = document.getElementById("sc-stop");
  const elReset     = document.getElementById("sc-reset");
  const elStatus    = document.getElementById("sc-status");
  const elTermBody  = document.getElementById("sc-term-body");

  // xterm.js terminal instance
  const _term = new Terminal({
    theme: { background: "#020817", foreground: "#94a3b8", cursor: "#60a5fa" },
    fontFamily: '"Menlo","Monaco","Consolas","Courier New",monospace',
    fontSize: 12,
    lineHeight: 1.4,
    scrollback: 5000,
    convertEol: true,
  });
  const _fitAddon = new FitAddon.FitAddon();
  _term.loadAddon(_fitAddon);
  _term.open(elTermBody);
  _fitAddon.fit();
  new ResizeObserver(() => _fitAddon.fit()).observe(elTermBody);

  // Replay buffered lines from previous visit
  if (_termLines.length) {
    _termLines.forEach(l => _term.writeln(l));
  }

  // Reconnect stream if a run was active when user navigated away
  if (currentRunId) {
    fetch(`/api/sim/run/${currentRunId}/status`).then(r => r.json()).then(s => {
      if (s.status === "running") {
        setRunning(true);
        showStatus(`Run ${currentRunId.slice(0,8)}… running`, "running");
        startStream(currentRunId);
      } else if (s.status === "done") {
        showStatus("Done ✓", "done");
      } else if (s.status) {
        showStatus(s.status, "error");
      }
    }).catch(() => {});
  }

  const elRuns       = document.getElementById("sc-runs");
  const elDelSelected= document.getElementById("sc-del-selected");
  const elDelAll     = document.getElementById("sc-del-all");
  const elLogList   = document.getElementById("sc-loglist");
  const elLogContent= document.getElementById("sc-logcontent");

  const SCENARIO_DAYS = {"calm-market": 15, "holiday-rush": 25};
  elScenario.addEventListener("change", () => {
    const days = SCENARIO_DAYS[elScenario.value];
    if (days) elDays.value = days;
  });

  let _allLogs = [];

  function renderLogList(filter) {
    const filtered = filter ? _allLogs.filter(l => l.path.startsWith(filter + "/")) : _allLogs;
    elLogList.innerHTML = filtered.map(l =>
      `<li data-path="${l.path}" title="${l.path}">${l.path.split("/").pop()}</li>`).join("");
    elLogList.querySelectorAll("li").forEach(li => {
      li.addEventListener("click", async () => {
        elLogList.querySelectorAll("li").forEach(x => x.classList.remove("active"));
        li.classList.add("active");
        elLogContent.textContent = "Loading…";
        const res = await fetch(`/api/sim/log?path=${encodeURIComponent(li.dataset.path)}`).then(r => r.json());
        elLogContent.textContent = res.content || res.error;
        elLogContent.scrollTop = 0;
      });
    });
  }

  async function loadLogs() {
    try {
      _allLogs = await fetch("/api/sim/logs").then(r => r.json());
      const scenariosWithLogs = [...new Set(_allLogs.map(l => l.path.split("/")[0]))].filter(Boolean);
      const elFilter = document.getElementById("sc-log-filter");
      if (elFilter) {
        const current = elFilter.value;
        elFilter.innerHTML = `<option value="">— pick a scenario —</option>` +
          scenariosWithLogs.map(s => `<option value="${s}"${s===current?" selected":""}>${s}</option>`).join("");
        renderLogList(elFilter.value);
      }
    } catch(e) {}
  }

  async function loadSummaries() {
    try {
      const summaries = await fetch("/api/sim/summaries").then(r => r.json());
      const elSummaries = document.getElementById("sc-summaries");
      const elSummaryContent = document.getElementById("sc-summarycontent");
      if (!elSummaries) return;
      elSummaries.innerHTML = summaries.map(s =>
        `<div class="run-chip done" data-path="${s.path}" title="${s.name}">${s.name}</div>`
      ).join("") || '<span class="muted">No summaries yet.</span>';
      elSummaries.querySelectorAll("[data-path]").forEach(el => {
        el.addEventListener("click", async () => {
          elSummaries.querySelectorAll("[data-path]").forEach(x => x.style.borderColor = "");
          el.style.borderColor = "var(--accent)";
          elSummaryContent.textContent = "Loading…";
          const res = await fetch(`/api/sim/log?path=${encodeURIComponent(el.dataset.path)}`).then(r => r.json());
          elSummaryContent.textContent = res.content || res.error;
          elSummaryContent.scrollTop = 0;
        });
      });
    } catch(e) {}
  }

  async function loadRuns() {
    try {
      const runs = await fetch("/api/sim/runs").then(r => r.json());
      if (!runs.length) { elRuns.innerHTML = '<span class="muted">No runs yet.</span>'; elDelSelected.disabled = true; return; }
      elRuns.innerHTML = runs.slice(0, 20).map(r => {
        const cls = r.status === "running" ? "running" : r.status === "done" ? "done" : "error";
        const model = (r.model || "").split("-").slice(0,2).join("-");
        const canDelete = r.status !== "running";
        return `<label class="run-chip ${cls}" title="${r.run_id}" style="display:flex;align-items:center;gap:6px;cursor:${canDelete ? "pointer" : "default"}">
          <input type="checkbox" class="run-check" data-id="${r.run_id}" ${canDelete ? "" : "disabled"} style="accent-color:#60a5fa">
          <span>${r.scenario} · ${r.days}d · ${model} · ${r.status}</span>
        </label>`;
      }).join("");
      elRuns.addEventListener("change", updateDelSelected);
      updateDelSelected();
    } catch(e) {}
  }

  function updateDelSelected() {
    const checked = elRuns.querySelectorAll(".run-check:checked").length;
    elDelSelected.disabled = checked === 0;
  }

  async function deleteRuns(ids) {
    const url = ids ? `/api/sim/runs?ids=${ids.join(",")}` : "/api/sim/runs";
    try {
      await fetch(url, { method: "DELETE" });
      await loadRuns();
    } catch(e) {}
  }

  elDelSelected.addEventListener("click", () => {
    const ids = [...elRuns.querySelectorAll(".run-check:checked")].map(cb => cb.dataset.id);
    if (ids.length) deleteRuns(ids);
  });

  elDelAll.addEventListener("click", () => {
    if (confirm("Remove all finished runs from the list?")) deleteRuns(null);
  });

  // Disable Start if any run is already active
  async function checkActiveRun() {
    try {
      const runs = await fetch("/api/sim/runs").then(r => r.json());
      const active = runs.find(r => r.status === "running");
      if (active) {
        setRunning(true);
        if (active.run_id !== currentRunId) {
          currentRunId = active.run_id;
          sessionStorage.setItem(_SS_RUN, currentRunId);
        }
      }
    } catch(e) {}
  }
  checkActiveRun();

  // Resume reset polling if a reset was in progress
  (async () => {
    try {
      const s = await fetch("/api/sim/reset/status").then(r => r.json());
      if (s.status === "running") {
        showStatus("Resetting…", "running");
        elReset.disabled = true;
        for (let i = 0; i < 60; i++) {
          await new Promise(r => setTimeout(r, 2000));
          const s2 = await fetch("/api/sim/reset/status").then(r => r.json());
          if (s2.status === "done") {
            (s2.output || "").split("\n").forEach(l => l.trim() && appendLine(l));
            showStatus("Reset complete ✓", "done");
            appendLine("✓ All services reset to Day 0.");
            loadRuns(); loadLogs(); loadSummaries();
            break;
          } else if (s2.status === "error") {
            showStatus("Reset failed", "error");
            appendLine("ERROR: " + s2.output);
            break;
          }
        }
        elReset.disabled = false;
      }
    } catch(e) {}
  })();

  function appendLine(text) {
    _termLines.push(text);
    _saveLines();
    _term.writeln(text);
  }

  function setRunning(running) {
    elStart.disabled = running;
    elStop.disabled = !running;
  }

  function showStatus(msg, cls) {
    elStatus.textContent = msg;
    elStatus.className = "run-status " + cls;
    elStatus.style.display = "block";
  }

  function startStream(runId) {
    if (eventSource) eventSource.close();
    eventSource = new EventSource(`/api/sim/run/${runId}/stream`);
    eventSource.onmessage = e => {
      const text = e.data;
      if (!text || text === "KEEPALIVE") return;
      if (text === "STREAM_END") {
        eventSource.close(); eventSource = null;
        pollUntilDone(runId);
        return;
      }
      appendLine(text);
    };
    eventSource.onerror = () => {
      eventSource.close();
      eventSource = null;
      pollUntilDone(runId);
    };
  }

  async function pollUntilDone(runId) {
    for (let i = 0; i < 120; i++) {
      await new Promise(r => setTimeout(r, 2000));
      try {
        const s = await fetch(`/api/sim/run/${runId}/status`).then(r => r.json());
        if (s.status === "done") { showStatus("Done ✓", "done"); setRunning(false); loadRuns(); loadLogs(); loadSummaries(); return; }
        if (s.status === "error") { showStatus("Error: " + (s.error || ""), "error"); setRunning(false); loadRuns(); return; }
      } catch(e) { break; }
    }
    setRunning(false);
  }

  elStart.addEventListener("click", async () => {
    _term.clear();
    _termLines = [];
    _saveLines();
    sessionStorage.removeItem(_SS_RUN);
    elLogContent.style.display = "none";
    setRunning(true);
    showStatus("Starting…", "running");
    try {
      const resp = await fetch("/api/sim/run", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({
          scenario: elScenario.value,
          model: elModel.value,
          days: parseInt(elDays.value),
          start_day: parseInt(elStartDay.value),
        })
      });
      if (resp.status === 409) { const e = await resp.json(); showStatus(e.detail, "error"); setRunning(false); return; }
      const res = await resp.json();
      if (!res.run_id) { showStatus("Failed: " + JSON.stringify(res), "error"); setRunning(false); return; }
      currentRunId = res.run_id;
      sessionStorage.setItem(_SS_RUN, currentRunId);
      showStatus(`Run ${currentRunId.slice(0,8)}… running`, "running");
      startStream(currentRunId);
      loadRuns();
      startRunsPoller();
    } catch(e) {
      showStatus("Error: " + e, "error");
      setRunning(false);
    }
  });

  elReset.addEventListener("click", async () => {
    if (!confirm("Reset all services to Day 0? This deletes all databases and run.csv.")) return;
    elReset.disabled = true;
    _term.clear();
    _termLines = [];
    _saveLines();
    sessionStorage.removeItem(_SS_RUN);
    showStatus("Resetting…", "running");
    appendLine("↺ Running reset_all.sh…");
    try {
      await fetch("/api/sim/reset", { method: "POST" });
      // Poll until done — survives page navigation
      for (let i = 0; i < 60; i++) {
        await new Promise(r => setTimeout(r, 2000));
        const s = await fetch("/api/sim/reset/status").then(r => r.json());
        if (s.status === "done") {
          (s.output || "").split("\n").forEach(l => l.trim() && appendLine(l));
          showStatus("Reset complete ✓", "done");
          appendLine("✓ All services reset to Day 0.");
          elLogContent.style.display = "none";
          elLogContent.textContent = "";
          const elSC = document.getElementById("sc-summarycontent");
          if (elSC) { elSC.style.display = "none"; elSC.textContent = ""; }
          loadRuns(); loadLogs(); loadSummaries();
          break;
        } else if (s.status === "error") {
          showStatus("Reset failed", "error");
          appendLine("ERROR: " + s.output);
          break;
        }
      }
    } catch(e) {
      showStatus("Reset error: " + e, "error");
      appendLine("ERROR: " + e);
    }
    elReset.disabled = false;
  });

  elStop.addEventListener("click", async () => {
    if (!currentRunId) return;
    await fetch(`/api/sim/run/${currentRunId}`, {method: "DELETE"});
    showStatus("Cancelling…", "running");
  });

  document.addEventListener("change", e => {
    if (e.target.id === "sc-log-filter") renderLogList(e.target.value);
  });

  loadRuns();
  loadLogs();
  loadSummaries();

  // Only poll runs while a simulation is active; stop when all are terminal
  let _runsPoller = null;
  function startRunsPoller() {
    if (_runsPoller) return;
    _runsPoller = setInterval(async () => {
      await loadRuns();
      const chips = document.querySelectorAll("#sc-runs .run-chip.running");
      if (!chips.length) { clearInterval(_runsPoller); _runsPoller = null; }
    }, 5000);
  }
  // Kick off poller only when there's actually a running run
  loadRuns().then(() => {
    if (document.querySelector("#sc-runs .run-chip.running")) startRunsPoller();
  });
}
