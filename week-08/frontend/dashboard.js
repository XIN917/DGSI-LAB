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
    const top = tier.items.slice(0, 3).map(i =>
      `<div>${i.name} <b>${fmt(i.stock)}</b></div>`).join("");
    const extra = name === "manufacturer" && tier.extra.utilisation_pct != null
      ? `<div class="muted">util ${fmt(tier.extra.utilisation_pct)}%</div>` : "";
    return `<div class="card ${name}"><h3>${name.toUpperCase()}</h3>${top}${extra}
      <svg class="sparkline" data-spark="${name}"></svg></div>`;
  };
  const arrow = (n) => `<div class="arrow">▶▶<div class="n">${fmt(n)}</div><div class="muted">in transit</div></div>`;
  root.innerHTML = `
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
    </div>`;
  ["provider", "manufacturer", "retailer"].forEach(name => {
    const svg = root.querySelector(`[data-spark="${name}"]`);
    const hist = (data.history[name] || {}).series || {};
    const stockSeries = hist.stock || hist.finished_stock || {};
    const first = Object.values(stockSeries)[0];
    if (svg && first) drawSparkline(svg, first, TIER_COLORS[name]);
  });
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
    root.innerHTML = `<p class="muted">${name} is offline — start the service and the simulation.</p>`;
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
function _lineChart(svg, seriesMap) {
  const W = svg.clientWidth || 600, H = svg.clientHeight || 200, pad = {l: 38, r: 10, t: 10, b: 22};
  const b = _bounds(seriesMap);
  svg.innerHTML = "";
  if (!b) { svg.innerHTML = `<text x="10" y="20" fill="#64748b">no history yet</text>`; return []; }
  const sx = x => pad.l + ((x - b.minX) / Math.max(1, b.maxX - b.minX)) * (W - pad.l - pad.r);
  const sy = y => H - pad.b - ((y - b.minY) / (b.maxY - b.minY)) * (H - pad.t - pad.b);
  const ns = "http://www.w3.org/2000/svg";
  [b.minY, (b.minY + b.maxY) / 2, b.maxY].forEach(v => {
    const t = document.createElementNS(ns, "text"); t.setAttribute("x", 2); t.setAttribute("y", sy(v) + 4);
    t.setAttribute("fill", "#475569"); t.setAttribute("font-size", "10"); t.textContent = Math.round(v); svg.appendChild(t);
    const g = document.createElementNS(ns, "line"); g.setAttribute("x1", pad.l); g.setAttribute("x2", W - pad.r);
    g.setAttribute("y1", sy(v)); g.setAttribute("y2", sy(v)); g.setAttribute("stroke", "#1e293b"); svg.appendChild(g);
  });
  const legend = [];
  Object.entries(seriesMap).forEach(([key, pts], idx) => {
    const color = PALETTE[idx % PALETTE.length]; legend.push([key, color]);
    const d = pts.map(([x, y], i) => `${i ? "L" : "M"}${sx(x).toFixed(1)},${sy(y).toFixed(1)}`).join(" ");
    const pl = document.createElementNS(ns, "path"); pl.setAttribute("d", d); pl.setAttribute("fill", "none");
    pl.setAttribute("stroke", color); pl.setAttribute("stroke-width", "1.8"); svg.appendChild(pl);
  });
  return legend;
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
  if (name === "provider") return [["Stock over time (per part)", "stock"], ["Tier-1 price over time", "price"]];
  if (name === "manufacturer") return [["Finished stock", "finished_stock"], ["Wholesale price", "wholesale_price"],
    ["Production utilisation %", "utilisation"]];
  return [["Stock over time (per SKU)", "stock"], ["Retail price over time", "retail_price"], ["__fill__", "fill"]];
}
function chartsBlock(name, hist, data) {
  const defs = _chartDefs(name, data);
  return `<div class="charts">` + defs.map(([title], i) =>
    `<div class="chart"><h4>${title === "__fill__" ? "Fill-rate % over time" : title}</h4>
      <svg data-chart="${i}"></svg><div class="legend" data-legend="${i}"></div></div>`).join("") + `</div>`;
}
function drawAllCharts(name, hist, data) {
  const defs = _chartDefs(name, data);
  defs.forEach(([title, metric], i) => {
    const svg = root.querySelector(`[data-chart="${i}"]`); if (!svg) return;
    let seriesMap;
    if (metric === "fill") seriesMap = data.fill_rate_series.length ? {"fill-rate": data.fill_rate_series} : {};
    else seriesMap = (hist.series || {})[metric] || {};
    const legend = _lineChart(svg, seriesMap);
    const box = root.querySelector(`[data-legend="${i}"]`);
    if (box) box.innerHTML = legend.map(([k, c]) => `<span style="color:${c}">${k}</span>`).join("");
  });
}

setInterval(tick, REFRESH);
tick();
