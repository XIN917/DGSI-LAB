# DGSI Interface Design System

## Direction
Dark industrial dashboard. Factory floor aesthetic — no decoration, only data.
The simulation planner is making operational decisions. Every pixel earns its place.

## Palette
- `--bg-base: #0F172A` — deep slate base
- `--bg-card: #1E293B` — card surfaces  
- `--bg-muted: #1A1E2F` — inputs/insets (slightly darker = "receive content here")
- `--border: #334155` — borders-only depth, no shadows
- `--accent: #F59E0B` — amber (filament + industrial alert)
- `--success: #22C55E` — running/delivered
- `--danger: #EF4444` — fault/critical
- `--info: #3B82F6` — released/in-progress
- `--fg-primary: #F8FAFC` | `--fg-secondary: #CBD5E1` | `--fg-tertiary: #94A3B8` | `--fg-muted: #64748B`

## Depth Strategy
**Borders-only.** No box-shadows anywhere. Cards use `border: 1px solid #334155`.

## Typography
- Headings/labels: `Fira Sans` (weights 300/400/500/600)
- All numbers/data: `Fira Code` (monospace, tabular figures)
- Section labels: 10px, UPPERCASE, letter-spacing 0.08em, color `--fg-muted`

## Spacing
Base unit 4px. Component padding: 12–16px. Section gaps: 24px.

## Components
- **Inventory bins**: horizontal fill bar (6px height) + avail/total in Fira Code + CRIT/LOW/OK badge
- **Order rows**: compact flex row — id | model | qty | progress bar 3px | status badge
- **Status badges**: 9px uppercase, colored bg at 15% opacity, colored text
- **Event rows**: date | type chip (colored) | detail text
- **Day strip**: full-width header — app title left, day counter center (Fira Code 32px), capacity right
