#!/usr/bin/env python3
"""Generate dependency-free SVG visuals for scalping optimization outcomes."""

from __future__ import annotations

import html
import json
import math
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path


def _escape(text: str) -> str:
    return html.escape(text, quote=True)


def _fmt(value: float, digits: int = 2) -> str:
    return f"{value:.{digits}f}"


def _color_blend(c1: tuple[int, int, int], c2: tuple[int, int, int], t: float) -> str:
    t = max(0.0, min(1.0, t))
    r = round(c1[0] + (c2[0] - c1[0]) * t)
    g = round(c1[1] + (c2[1] - c1[1]) * t)
    b = round(c1[2] + (c2[2] - c1[2]) * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def _value_to_heat_color(value: float, min_value: float, max_value: float) -> str:
    if max_value <= min_value:
        return "#5aa469"
    t = (value - min_value) / (max_value - min_value)
    # low->mid->high : red -> amber -> green
    if t <= 0.5:
        return _color_blend((192, 57, 43), (241, 196, 15), t / 0.5)
    return _color_blend((241, 196, 15), (39, 174, 96), (t - 0.5) / 0.5)


def _svg_doc(width: int, height: int, body: list[str], title: str) -> str:
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
        f'viewBox="0 0 {width} {height}" role="img" aria-label="{_escape(title)}">\n'
        + "\n".join(body)
        + "\n</svg>\n"
    )


def _write_text(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _draw_axes(
    body: list[str],
    left: int,
    top: int,
    width: int,
    height: int,
    y_ticks: int,
    y_max: float,
) -> None:
    body.append(
        f'<rect x="{left}" y="{top}" width="{width}" height="{height}" fill="#111827" stroke="#334155"/>'
    )
    for i in range(y_ticks + 1):
        y = top + height - (height * i / y_ticks)
        label_val = y_max * i / y_ticks
        body.append(
            f'<line x1="{left}" y1="{y:.2f}" x2="{left + width}" y2="{y:.2f}" stroke="#1f2937"/>'
        )
        body.append(
            f'<text x="{left - 10}" y="{y + 4:.2f}" text-anchor="end" '
            f'font-size="12" fill="#94a3b8">{_fmt(label_val, 1)}</text>'
        )
    body.append(
        f'<line x1="{left}" y1="{top + height}" x2="{left + width}" y2="{top + height}" stroke="#64748b"/>'
    )
    body.append(f'<line x1="{left}" y1="{top}" x2="{left}" y2="{top + height}" stroke="#64748b"/>')


def _grouped_bar_chart_svg(
    title: str,
    subtitle: str,
    categories: list[str],
    series: list[tuple[str, list[float], str]],
    y_label: str,
    width: int = 1200,
    height: int = 760,
) -> str:
    left, right, top, bottom = 100, 40, 110, 140
    plot_w = width - left - right
    plot_h = height - top - bottom

    values = [v for _, vals, _ in series for v in vals]
    y_max = max(values) if values else 1.0
    y_max = max(1.0, y_max * 1.12)

    body: list[str] = []
    body.append(f'<rect x="0" y="0" width="{width}" height="{height}" fill="#0b1220"/>')
    body.append(
        f'<text x="{left}" y="52" font-size="28" fill="#e2e8f0" font-weight="700">{_escape(title)}</text>'
    )
    body.append(f'<text x="{left}" y="80" font-size="16" fill="#93c5fd">{_escape(subtitle)}</text>')

    _draw_axes(body, left, top, plot_w, plot_h, y_ticks=5, y_max=y_max)
    body.append(
        f'<text x="24" y="{top + 18}" font-size="14" fill="#94a3b8" transform="rotate(-90 24 {top + 18})">{_escape(y_label)}</text>'
    )

    n = max(1, len(categories))
    m = max(1, len(series))
    group_w = plot_w / n
    gap = 4
    bar_w = min(52, max(8.0, (group_w * 0.8 - gap * (m - 1)) / m))

    for i, cat in enumerate(categories):
        group_left = left + i * group_w
        bars_w = m * bar_w + (m - 1) * gap
        bar_left0 = group_left + (group_w - bars_w) / 2

        for s_idx, (name, vals, color) in enumerate(series):
            val = vals[i]
            h = 0 if y_max == 0 else (val / y_max) * plot_h
            x = bar_left0 + s_idx * (bar_w + gap)
            y = top + plot_h - h
            body.append(
                f'<rect x="{x:.2f}" y="{y:.2f}" width="{bar_w:.2f}" height="{h:.2f}" fill="{color}"/>'
            )

        x_center = group_left + group_w / 2
        body.append(
            f'<text x="{x_center:.2f}" y="{top + plot_h + 26}" text-anchor="middle" '
            f'font-size="12" fill="#cbd5e1">{_escape(cat)}</text>'
        )

    # Legend
    legend_x = left
    legend_y = height - 58
    for name, _, color in series:
        body.append(
            f'<rect x="{legend_x}" y="{legend_y - 11}" width="18" height="18" fill="{color}"/>'
        )
        body.append(
            f'<text x="{legend_x + 24}" y="{legend_y + 3}" font-size="14" fill="#cbd5e1">{_escape(name)}</text>'
        )
        legend_x += 220

    return _svg_doc(width, height, body, title)


def _histogram_svg(
    title: str,
    subtitle: str,
    values: list[float],
    bins: int = 24,
    width: int = 1200,
    height: int = 760,
) -> str:
    if not values:
        return _grouped_bar_chart_svg(
            title, subtitle, ["empty"], [("count", [0], "#60a5fa")], "Count", width, height
        )

    min_v = min(values)
    max_v = max(values)
    if math.isclose(min_v, max_v):
        min_v -= 0.5
        max_v += 0.5

    bin_w = (max_v - min_v) / bins
    counts = [0] * bins
    for v in values:
        idx = int((v - min_v) / bin_w)
        idx = max(0, min(bins - 1, idx))
        counts[idx] += 1

    labels = []
    for i in range(bins):
        lo = min_v + i * bin_w
        hi = lo + bin_w
        labels.append(f"{_fmt(lo, 1)}-{_fmt(hi, 1)}")

    left, right, top, bottom = 100, 40, 110, 170
    plot_w = width - left - right
    plot_h = height - top - bottom
    y_max = max(1, max(counts) * 1.12)

    body: list[str] = []
    body.append(f'<rect x="0" y="0" width="{width}" height="{height}" fill="#0b1220"/>')
    body.append(
        f'<text x="{left}" y="52" font-size="28" fill="#e2e8f0" font-weight="700">{_escape(title)}</text>'
    )
    body.append(f'<text x="{left}" y="80" font-size="16" fill="#93c5fd">{_escape(subtitle)}</text>')

    _draw_axes(body, left, top, plot_w, plot_h, y_ticks=5, y_max=y_max)

    bar_w = plot_w / bins
    for i, c in enumerate(counts):
        h = (c / y_max) * plot_h
        x = left + i * bar_w
        y = top + plot_h - h
        body.append(
            f'<rect x="{x:.2f}" y="{y:.2f}" width="{max(1.0, bar_w - 1):.2f}" height="{h:.2f}" fill="#38bdf8"/>'
        )
        if i % 3 == 0:
            body.append(
                f'<text x="{x + bar_w / 2:.2f}" y="{top + plot_h + 22}" text-anchor="middle" '
                f'font-size="10" fill="#cbd5e1" transform="rotate(35 {x + bar_w / 2:.2f} {top + plot_h + 22})">{_escape(labels[i])}</text>'
            )

    body.append(
        f'<text x="{left + plot_w / 2:.2f}" y="{height - 18}" text-anchor="middle" font-size="14" fill="#94a3b8">Net SOL bins</text>'
    )
    body.append(
        f'<text x="26" y="{top + 18}" font-size="14" fill="#94a3b8" transform="rotate(-90 26 {top + 18})">Config count</text>'
    )

    return _svg_doc(width, height, body, title)


def _heatmap_svg(
    title: str,
    subtitle: str,
    xs: list[int],
    ys: list[int],
    values: dict[tuple[int, int], float],
    width: int = 1200,
    height: int = 760,
) -> str:
    left, right, top, bottom = 160, 140, 110, 110
    plot_w = width - left - right
    plot_h = height - top - bottom

    all_vals = list(values.values())
    vmin = min(all_vals) if all_vals else 0.0
    vmax = max(all_vals) if all_vals else 1.0

    cell_w = plot_w / max(1, len(xs))
    cell_h = plot_h / max(1, len(ys))

    body: list[str] = []
    body.append(f'<rect x="0" y="0" width="{width}" height="{height}" fill="#0b1220"/>')
    body.append(
        f'<text x="{left}" y="52" font-size="28" fill="#e2e8f0" font-weight="700">{_escape(title)}</text>'
    )
    body.append(f'<text x="{left}" y="80" font-size="16" fill="#93c5fd">{_escape(subtitle)}</text>')

    body.append(
        f'<rect x="{left}" y="{top}" width="{plot_w}" height="{plot_h}" fill="#111827" stroke="#334155"/>'
    )

    for y_idx, yv in enumerate(ys):
        for x_idx, xv in enumerate(xs):
            val = values.get((xv, yv), 0.0)
            color = _value_to_heat_color(val, vmin, vmax)
            x = left + x_idx * cell_w
            y = top + y_idx * cell_h
            body.append(
                f'<rect x="{x:.2f}" y="{y:.2f}" width="{cell_w:.2f}" height="{cell_h:.2f}" fill="{color}" stroke="#0f172a"/>'
            )
            body.append(
                f'<text x="{x + cell_w / 2:.2f}" y="{y + cell_h / 2 + 5:.2f}" text-anchor="middle" '
                f'font-size="13" fill="#0f172a" font-weight="700">{_fmt(val, 1)}</text>'
            )

    for x_idx, xv in enumerate(xs):
        x = left + x_idx * cell_w + cell_w / 2
        body.append(
            f'<text x="{x:.2f}" y="{top + plot_h + 28}" text-anchor="middle" font-size="12" fill="#cbd5e1">{xv}</text>'
        )
    body.append(
        f'<text x="{left + plot_w / 2:.2f}" y="{height - 18}" text-anchor="middle" font-size="14" fill="#94a3b8">Entry cutoff tick</text>'
    )

    for y_idx, yv in enumerate(ys):
        y = top + y_idx * cell_h + cell_h / 2 + 4
        body.append(
            f'<text x="{left - 14}" y="{y:.2f}" text-anchor="end" font-size="12" fill="#cbd5e1">{yv}</text>'
        )
    body.append(
        f'<text x="40" y="{top + plot_h / 2:.2f}" font-size="14" fill="#94a3b8" '
        f'transform="rotate(-90 40 {top + plot_h / 2:.2f})">Classification ticks</text>'
    )

    # Legend
    leg_x = width - 94
    leg_y = top
    leg_h = plot_h
    for i in range(120):
        t = i / 119
        color = _value_to_heat_color(vmin + (vmax - vmin) * t, vmin, vmax)
        y = leg_y + leg_h - (i + 1) * (leg_h / 120)
        body.append(
            f'<rect x="{leg_x}" y="{y:.2f}" width="20" height="{leg_h / 120 + 0.6:.2f}" fill="{color}"/>'
        )
    body.append(
        f'<text x="{leg_x + 26}" y="{leg_y + 12}" font-size="12" fill="#cbd5e1">{_fmt(vmax, 2)}</text>'
    )
    body.append(
        f'<text x="{leg_x + 26}" y="{leg_y + leg_h}" font-size="12" fill="#cbd5e1">{_fmt(vmin, 2)}</text>'
    )
    body.append(
        f'<text x="{leg_x - 6}" y="{leg_y - 10}" font-size="12" fill="#94a3b8">Mean Net SOL</text>'
    )

    return _svg_doc(width, height, body, title)


def _build_index_html(figures: list[tuple[str, str, str]], generated_at: str) -> str:
    cards = []
    for filename, title, note in figures:
        cards.append(
            f"""
            <section class=\"card\">
              <h2>{_escape(title)}</h2>
              <p>{_escape(note)}</p>
              <img src=\"{_escape(filename)}\" alt=\"{_escape(title)}\" />
            </section>
            """
        )

    return f"""<!doctype html>
<html lang=\"en\">
<head>
  <meta charset=\"utf-8\" />
  <meta name=\"viewport\" content=\"width=device-width, initial-scale=1\" />
  <title>Scalping Outcomes Visual Report</title>
  <style>
    :root {{
      --bg: #060b16;
      --panel: #0f172a;
      --edge: #334155;
      --text: #e2e8f0;
      --muted: #93c5fd;
    }}
    body {{
      margin: 0;
      font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, sans-serif;
      background: radial-gradient(circle at top, #0f1b36 0%, var(--bg) 55%);
      color: var(--text);
    }}
    main {{
      max-width: 1280px;
      margin: 0 auto;
      padding: 24px 16px 40px;
    }}
    h1 {{ margin: 0 0 8px; font-size: 30px; }}
    .meta {{ margin: 0 0 20px; color: var(--muted); }}
    .grid {{
      display: grid;
      gap: 16px;
    }}
    .card {{
      background: color-mix(in srgb, var(--panel) 92%, black);
      border: 1px solid var(--edge);
      border-radius: 12px;
      padding: 14px;
    }}
    .card h2 {{ margin: 0 0 6px; font-size: 20px; }}
    .card p {{ margin: 0 0 12px; color: #cbd5e1; }}
    img {{ width: 100%; height: auto; border: 1px solid #1f2937; border-radius: 8px; background: #0b1220; }}
  </style>
</head>
<body>
  <main>
    <h1>Scalping Outcomes Visual Report</h1>
    <p class=\"meta\">Generated: {_escape(generated_at)} | Source: checkpoints/scalping_opt_sweep_2026-02-08.json + checkpoints/scalping_opt_fullgrid_envelope_2026-02-08.json</p>
    <div class=\"grid\">{"".join(cards)}</div>
  </main>
</body>
</html>
"""


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    research_dir = root / "docs" / "SCALP TRADING RESEARCH"
    checkpoints_dir = research_dir / "checkpoints"
    figure_dir = research_dir / "figures"

    sweep_path = checkpoints_dir / "scalping_opt_sweep_2026-02-08.json"
    full_path = checkpoints_dir / "scalping_opt_fullgrid_envelope_2026-02-08.json"

    sweep = json.loads(sweep_path.read_text(encoding="utf-8"))
    full = json.loads(full_path.read_text(encoding="utf-8"))

    rows = full["full_grid_rows"]
    top50 = full["top50"]

    # 1) PnL envelope percentiles
    net = full["net_sol"]
    end = full["end_sol"]
    percentile_labels = ["min", "p10", "median", "p90", "max"]
    pnl_svg = _grouped_bar_chart_svg(
        title="PnL Envelope Across All 2,100 Configurations",
        subtitle="Net SOL and End SOL percentiles from full-grid run on 1,772-game dataset.",
        categories=percentile_labels,
        series=[
            ("Net SOL", [net[k] for k in percentile_labels], "#38bdf8"),
            ("End SOL", [end[k] for k in percentile_labels], "#34d399"),
        ],
        y_label="SOL",
    )
    _write_text(figure_dir / "01_pnl_percentiles.svg", pnl_svg)

    # 2) Net SOL histogram
    histogram_svg = _histogram_svg(
        title="Net SOL Distribution (Full Grid)",
        subtitle="How often each net-SOL band appears across 2,100 parameter combinations.",
        values=[r["net_sol"] for r in rows],
        bins=24,
    )
    _write_text(figure_dir / "02_net_sol_histogram.svg", histogram_svg)

    # 3) Mode ranking
    mode_groups: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        mode_groups[r["playbook_mode"]].append(r["net_sol"])
    modes = sorted(mode_groups)
    best_vals = [max(mode_groups[m]) for m in modes]
    med_vals = [sorted(mode_groups[m])[len(mode_groups[m]) // 2] for m in modes]
    mode_svg = _grouped_bar_chart_svg(
        title="Playbook Mode Performance",
        subtitle="Best and median net SOL by mode over full grid.",
        categories=modes,
        series=[
            ("Best Net SOL", best_vals, "#f59e0b"),
            ("Median Net SOL", med_vals, "#60a5fa"),
        ],
        y_label="Net SOL",
    )
    _write_text(figure_dir / "03_playbook_mode_performance.svg", mode_svg)

    # 4) Drift ranking
    drift_groups: dict[str, list[float]] = defaultdict(list)
    for r in rows:
        drift_groups[r["drift_reference"]].append(r["net_sol"])
    drifts = sorted(drift_groups)
    drift_best = [max(drift_groups[d]) for d in drifts]
    drift_med = [sorted(drift_groups[d])[len(drift_groups[d]) // 2] for d in drifts]
    drift_svg = _grouped_bar_chart_svg(
        title="Drift Reference Performance",
        subtitle="Best and median net SOL by drift anchor.",
        categories=drifts,
        series=[
            ("Best Net SOL", drift_best, "#f97316"),
            ("Median Net SOL", drift_med, "#22d3ee"),
        ],
        y_label="Net SOL",
    )
    _write_text(figure_dir / "04_drift_reference_performance.svg", drift_svg)

    # 5) Top-50 concentration by classification ticks
    classification_counts = Counter(r["classification_ticks"] for r in top50)
    c_keys = [str(k) for k in sorted(classification_counts)]
    c_vals = [classification_counts[int(k)] for k in c_keys]
    top50_class_svg = _grouped_bar_chart_svg(
        title="Top-50 Concentration: Classification Ticks",
        subtitle="How often each classification window appears in top-50 net-SOL configs.",
        categories=c_keys,
        series=[("Count", c_vals, "#a78bfa")],
        y_label="Top-50 count",
    )
    _write_text(figure_dir / "05_top50_classification_counts.svg", top50_class_svg)

    # 6) Top-50 concentration by entry cutoff
    cutoff_counts = Counter(r["entry_cutoff_tick"] for r in top50)
    e_keys = [str(k) for k in sorted(cutoff_counts)]
    e_vals = [cutoff_counts[int(k)] for k in e_keys]
    top50_cutoff_svg = _grouped_bar_chart_svg(
        title="Top-50 Concentration: Entry Cutoff Tick",
        subtitle="Late cutoff windows dominate the highest-return cluster.",
        categories=e_keys,
        series=[("Count", e_vals, "#34d399")],
        y_label="Top-50 count",
    )
    _write_text(figure_dir / "06_top50_entry_cutoff_counts.svg", top50_cutoff_svg)

    # 7) Top-50 concentration by max hold
    hold_counts = Counter(r["max_hold_ticks"] for r in top50)
    h_keys = [str(k) for k in sorted(hold_counts)]
    h_vals = [hold_counts[int(k)] for k in h_keys]
    top50_hold_svg = _grouped_bar_chart_svg(
        title="Top-50 Concentration: Max Hold Ticks",
        subtitle="Higher hold windows (7-9) are most represented in top configs.",
        categories=h_keys,
        series=[("Count", h_vals, "#f472b6")],
        y_label="Top-50 count",
    )
    _write_text(figure_dir / "07_top50_hold_counts.svg", top50_hold_svg)

    # 8) Heatmap: classification vs cutoff (mean net over other dimensions)
    class_ticks = sorted({int(r["classification_ticks"]) for r in rows})
    cutoffs = sorted({int(r["entry_cutoff_tick"]) for r in rows})
    pair_vals: dict[tuple[int, int], list[float]] = defaultdict(list)
    for r in rows:
        key = (int(r["entry_cutoff_tick"]), int(r["classification_ticks"]))
        pair_vals[key].append(float(r["net_sol"]))

    mean_map: dict[tuple[int, int], float] = {}
    for c in class_ticks:
        for e in cutoffs:
            vals = pair_vals.get((e, c), [])
            mean_map[(e, c)] = (sum(vals) / len(vals)) if vals else 0.0

    heat_svg = _heatmap_svg(
        title="Mean Net SOL Heatmap (Classification vs Entry Cutoff)",
        subtitle="Each cell averages net SOL over hold/drift/mode/TP-SL combinations.",
        xs=cutoffs,
        ys=class_ticks,
        values=mean_map,
    )
    _write_text(figure_dir / "08_heatmap_classification_vs_cutoff_mean_net.svg", heat_svg)

    generated_at = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    figures = [
        (
            "01_pnl_percentiles.svg",
            "PnL Envelope Percentiles",
            "Fast read of downside/median/upside bounds in SOL.",
        ),
        (
            "02_net_sol_histogram.svg",
            "Net SOL Distribution",
            "Shows how much of the grid is high-return, low-return, or dead-zone.",
        ),
        (
            "03_playbook_mode_performance.svg",
            "Playbook Mode Performance",
            "Compares best vs typical outcomes for each entry logic family.",
        ),
        (
            "04_drift_reference_performance.svg",
            "Drift Reference Performance",
            "Compares P50/P75/P90 anchors under same grid.",
        ),
        (
            "05_top50_classification_counts.svg",
            "Top-50: Classification Window",
            "Where high performers concentrate by baseline ticks.",
        ),
        (
            "06_top50_entry_cutoff_counts.svg",
            "Top-50: Entry Cutoff",
            "Where high performers concentrate by allowed entry horizon.",
        ),
        (
            "07_top50_hold_counts.svg",
            "Top-50: Max Hold",
            "Where high performers concentrate by hold duration.",
        ),
        (
            "08_heatmap_classification_vs_cutoff_mean_net.svg",
            "Heatmap: Classification x Cutoff",
            "Averaged surface to spot broad plateaus before rigid thresholds.",
        ),
    ]
    index_html = _build_index_html(figures, generated_at)
    _write_text(figure_dir / "index.html", index_html)

    print(f"wrote visuals to: {figure_dir}")
    for filename, _, _ in figures:
        print(f" - {filename}")
    print(" - index.html")


if __name__ == "__main__":
    main()
