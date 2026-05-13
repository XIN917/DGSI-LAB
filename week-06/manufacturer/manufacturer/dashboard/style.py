"""Design system CSS injector for the DGSI dashboard.

Design tokens (from ui-ux-pro-max, style: Data-Dense Dashboard + Dark Mode):
  --bg-base:     #0F172A  (deep slate — factory floor concrete at night)
  --bg-card:     #1E293B  (card surface — slightly lighter)
  --bg-muted:    #1A1E2F  (input/inset — darker than card, signals "type here")
  --border:      #334155  (standard border — low contrast, structural only)
  --fg-primary:  #F8FAFC  (primary text)
  --fg-secondary:#CBD5E1  (supporting text)
  --fg-tertiary: #94A3B8  (metadata)
  --fg-muted:    #64748B  (disabled/placeholder)
  --accent:      #F59E0B  (amber — industrial alert + filament color)
  --success:     #22C55E  (running/delivered/completed)
  --danger:      #EF4444  (fault/cancelled/critical)
  --info:        #3B82F6  (released/in-progress)
  Depth: borders-only (no box-shadows)
  Typography: Fira Code (numbers/mono), Fira Sans (labels/body)
"""
import streamlit as st

_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Fira+Code:wght@400;500;600;700&family=Fira+Sans:wght@300;400;500;600;700&display=swap');

:root {
  --bg-base: #0F172A;
  --bg-card: #1E293B;
  --bg-muted: #1A1E2F;
  --border: #334155;
  --border-soft: rgba(51,65,85,0.45);
  --fg-primary: #F8FAFC;
  --fg-secondary: #CBD5E1;
  --fg-tertiary: #94A3B8;
  --fg-muted: #64748B;
  --accent: #F59E0B;
  --accent-muted: rgba(245,158,11,0.12);
  --success: #22C55E;
  --success-muted: rgba(34,197,94,0.12);
  --danger: #EF4444;
  --danger-muted: rgba(239,68,68,0.12);
  --info: #3B82F6;
  --info-muted: rgba(59,130,246,0.12);
  --warning: #F59E0B;
  --warning-muted: rgba(245,158,11,0.12);
  --r-sm: 4px;
  --r-md: 6px;
  --r-lg: 10px;
}

/* ── Global typography ── */
html, body, .stApp, [data-testid="stAppViewContainer"],
.stMarkdown, .stText, p, li, span, label {
  font-family: 'Fira Sans', sans-serif !important;
}

[data-testid="stMetricValue"],
[data-testid="stMetricDelta"],
code, pre, .stCode {
  font-family: 'Fira Code', monospace !important;
}

/* ── App background ── */
.stApp, [data-testid="stAppViewContainer"] {
  background-color: var(--bg-base) !important;
}

[data-testid="stHeader"] {
  background: var(--bg-base) !important;
  border-bottom: 1px solid var(--border) !important;
}

/* ── Dividers ── */
hr { border-color: var(--border) !important; opacity: 0.6 !important; }

/* ── Headings ── */
h1, h2, h3, h4 {
  font-family: 'Fira Sans', sans-serif !important;
  color: var(--fg-primary) !important;
  letter-spacing: -0.01em;
}
h1 { font-size: 20px !important; font-weight: 600 !important; }
h2 { font-size: 14px !important; font-weight: 600 !important;
     text-transform: uppercase; letter-spacing: 0.06em !important;
     color: var(--fg-tertiary) !important; }
h3 { font-size: 13px !important; font-weight: 600 !important; }

/* ── Metrics ── */
[data-testid="stMetric"] {
  background: var(--bg-card) !important;
  border: 1px solid var(--border) !important;
  border-radius: var(--r-md) !important;
  padding: 12px 16px !important;
}
[data-testid="stMetricValue"] {
  font-size: 24px !important;
  color: var(--fg-primary) !important;
}
[data-testid="stMetricLabel"] {
  font-size: 10px !important;
  font-weight: 600 !important;
  letter-spacing: 0.08em !important;
  text-transform: uppercase !important;
  color: var(--fg-muted) !important;
}

/* ── Buttons ── */
.stButton > button {
  background-color: var(--accent) !important;
  color: #0F172A !important;
  border: none !important;
  border-radius: var(--r-md) !important;
  font-family: 'Fira Sans', sans-serif !important;
  font-weight: 600 !important;
  font-size: 12px !important;
  letter-spacing: 0.02em !important;
  transition: background 150ms ease-out !important;
}
.stButton > button:hover {
  background-color: #D97706 !important;
}
.stButton > button[kind="secondary"] {
  background-color: var(--bg-card) !important;
  color: var(--fg-secondary) !important;
  border: 1px solid var(--border) !important;
}
.stButton > button[kind="secondary"]:hover {
  background-color: #263347 !important;
}

/* ── Inputs ── */
.stTextInput > div > div > input,
.stNumberInput > div > div > input,
.stTextArea textarea {
  background-color: var(--bg-muted) !important;
  border: 1px solid var(--border) !important;
  color: var(--fg-primary) !important;
  border-radius: var(--r-sm) !important;
  font-family: 'Fira Sans', sans-serif !important;
  font-size: 13px !important;
}
.stTextInput > div > div > input:focus,
.stNumberInput > div > div > input:focus {
  border-color: var(--accent) !important;
  box-shadow: 0 0 0 1px var(--accent) !important;
}

/* ── Selectbox ── */
.stSelectbox > div > div {
  background-color: var(--bg-muted) !important;
  border: 1px solid var(--border) !important;
  color: var(--fg-primary) !important;
  border-radius: var(--r-sm) !important;
}

/* ── Progress bars ── */
.stProgress > div {
  background: #1A2234 !important;
  border-radius: 2px !important;
  height: 4px !important;
}
.stProgress > div > div > div > div {
  background: var(--accent) !important;
  border-radius: 2px !important;
}

/* ── Expanders ── */
.stExpander {
  border: 1px solid var(--border) !important;
  border-radius: var(--r-md) !important;
  background: var(--bg-card) !important;
}
.stExpander summary {
  color: var(--fg-secondary) !important;
  font-size: 13px !important;
}

/* ── Alert / info ── */
.stSuccess { background: var(--success-muted) !important; border-left-color: var(--success) !important; }
.stError   { background: var(--danger-muted) !important;  border-left-color: var(--danger) !important; }
.stInfo    { background: var(--info-muted) !important;    border-left-color: var(--info) !important; }
.stWarning { background: var(--warning-muted) !important; border-left-color: var(--warning) !important; }

/* ── Sidebar (collapsed) ── */
.stSidebar [data-testid="stSidebar"] {
  background: var(--bg-base) !important;
  border-right: 1px solid var(--border) !important;
}

/* ── Remove "press enter to submit" hint ── */
[data-testid="stFormSubmitButton"] + div,
[data-testid="stFormSubmitButton"] + p,
[data-testid="stForm"] div[data-testid="stMarkdownContainer"] p small,
.stForm p {
  display: none !important;
}

div.stFormSubmitButton + div {
  display: none !important;
}

/* ── Custom HTML components ── */

/* Inventory bin bars */
.bins-container { margin-top: 8px; }
.bin-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 0;
  border-bottom: 1px solid rgba(51,65,85,0.3);
}
.bin-row:last-child { border-bottom: none; }
.bin-name {
  font-family: 'Fira Code', monospace;
  font-size: 10px;
  color: #94A3B8;
  width: 120px;
  flex-shrink: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.bin-track {
  flex: 1;
  height: 5px;
  background: #1A2234;
  border-radius: 2px;
  overflow: hidden;
}
.bin-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 300ms ease-out;
}
.bin-avail {
  font-family: 'Fira Code', monospace;
  font-size: 11px;
  color: #F8FAFC;
  font-weight: 600;
  width: 36px;
  text-align: right;
}
.bin-total {
  font-family: 'Fira Code', monospace;
  font-size: 10px;
  color: #475569;
  width: 36px;
}
.bin-badge {
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.07em;
  padding: 1px 5px;
  border-radius: 3px;
  width: 52px;
  text-align: center;
}
.badge-ok       { background: rgba(34,197,94,0.15);  color: #22C55E; }
.badge-low      { background: rgba(245,158,11,0.15); color: #F59E0B; }
.badge-critical { background: rgba(239,68,68,0.15);  color: #EF4444; }

/* Warehouse header bar */
.warehouse-header {
  display: flex;
  justify-content: space-between;
  align-items: baseline;
  margin-bottom: 6px;
}
.warehouse-label {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #64748B;
}
.warehouse-pct {
  font-family: 'Fira Code', monospace;
  font-size: 12px;
  font-weight: 600;
  color: #F8FAFC;
}
.warehouse-track {
  height: 3px;
  background: #1A2234;
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 14px;
}
.warehouse-fill {
  height: 100%;
  border-radius: 2px;
  transition: width 300ms ease-out;
}

/* Order rows */
.order-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 10px;
  border-radius: 5px;
  margin-bottom: 3px;
  background: rgba(30,41,59,0.6);
  border: 1px solid var(--border-soft);
  transition: background 150ms;
  cursor: default;
}
.order-row:hover { background: rgba(30,41,59,1); }
.order-id {
  font-family: 'Fira Code', monospace;
  font-size: 10px;
  color: #475569;
  width: 36px;
  flex-shrink: 0;
}
.order-model {
  font-size: 12px;
  font-weight: 500;
  color: #CBD5E1;
  flex: 1;
}
.order-qty {
  font-family: 'Fira Code', monospace;
  font-size: 11px;
  color: #94A3B8;
  width: 32px;
  text-align: right;
  flex-shrink: 0;
}
.order-prog-track {
  width: 50px;
  height: 3px;
  background: #1A2234;
  border-radius: 2px;
  flex-shrink: 0;
}
.order-prog-fill {
  height: 100%;
  border-radius: 2px;
  background: #3B82F6;
}
.order-status {
  font-size: 9px;
  font-weight: 700;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  padding: 2px 6px;
  border-radius: 3px;
  width: 88px;
  text-align: center;
  flex-shrink: 0;
}
.status-pending          { background: rgba(245,158,11,0.15); color: #F59E0B; }
.status-released         { background: rgba(59,130,246,0.15); color: #3B82F6; }
.status-waiting_materials{ background: rgba(239,68,68,0.15);  color: #EF4444; }
.status-completed        { background: rgba(34,197,94,0.15);  color: #22C55E; }
.status-cancelled        { background: rgba(100,116,139,0.15);color: #64748B; }
.status-failed           { background: rgba(239,68,68,0.15);  color: #EF4444; }

/* Order counter bar */
.order-counts {
  display: flex;
  gap: 8px;
  margin-bottom: 10px;
}
.order-count-chip {
  flex: 1;
  text-align: center;
  padding: 8px 4px;
  border-radius: var(--r-md);
  border: 1px solid var(--border-soft);
  background: var(--bg-card);
}
.count-number {
  font-family: 'Fira Code', monospace;
  font-size: 18px;
  font-weight: 700;
  display: block;
  line-height: 1;
  margin-bottom: 3px;
}
.count-label {
  font-size: 9px;
  font-weight: 600;
  letter-spacing: 0.07em;
  text-transform: uppercase;
  color: #64748B;
}

/* Event log rows */
.event-row {
  display: flex;
  align-items: baseline;
  gap: 10px;
  padding: 5px 0;
  border-bottom: 1px solid rgba(51,65,85,0.25);
  font-size: 11px;
}
.event-row:last-child { border-bottom: none; }
.event-date {
  font-family: 'Fira Code', monospace;
  font-size: 9px;
  color: #334155;
  width: 68px;
  flex-shrink: 0;
}
.event-type-chip {
  font-family: 'Fira Code', monospace;
  font-size: 9px;
  font-weight: 700;
  padding: 1px 6px;
  border-radius: 3px;
  width: 160px;
  flex-shrink: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.event-detail {
  color: #475569;
  font-size: 10px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}

/* Day advance header */
.day-strip {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0 16px;
  border-bottom: 1px solid var(--border);
  margin-bottom: 16px;
}
.day-label {
  font-size: 10px;
  font-weight: 600;
  letter-spacing: 0.10em;
  text-transform: uppercase;
  color: #475569;
  margin-bottom: 2px;
}
.day-number {
  font-family: 'Fira Code', monospace;
  font-size: 32px;
  font-weight: 700;
  color: #F8FAFC;
  line-height: 1;
}
.day-date {
  font-family: 'Fira Code', monospace;
  font-size: 11px;
  color: #64748B;
  margin-top: 3px;
}
.app-title {
  font-size: 13px;
  font-weight: 600;
  letter-spacing: 0.03em;
  color: #F8FAFC;
}
.app-subtitle {
  font-size: 10px;
  color: #475569;
  margin-top: 2px;
}
"""


def inject_styles() -> None:
    """Inject the full CSS design system. Call once at the top of every page."""
    st.markdown(f"<style>{_CSS}</style>", unsafe_allow_html=True)
