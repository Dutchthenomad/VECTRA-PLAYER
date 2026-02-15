#!/usr/bin/env python3
"""Generate refined Nexus UI layout Excalidraw diagram v2."""

import json
import sys

# Color scheme (GitHub Dark)
BG = "#0d1117"
CARD = "#161b22"
BORDER = "#30363d"
BORDER_DIM = "#21262d"
TEXT = "#c9d1d9"
TEXT2 = "#8b949e"
MUTED = "#484f58"
BLUE = "#58a6ff"
GREEN = "#3fb950"
ORANGE = "#f0883e"
GRAY = "#484f58"
RED = "#c92a2a"
PURPLE = "#7048e8"
TEAL = "#2f9e44"
AMBER = "#f08c00"
PIPE_ORANGE = "#e8590c"

seed_counter = 1


def next_seed():
    global seed_counter
    seed_counter += 1
    return seed_counter


def rect(id, x, y, w, h, stroke=BORDER, bg="transparent", groups=[], roundness=3, sw=1):
    r = {"type": 3} if roundness else None
    return {
        "id": id,
        "type": "rectangle",
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "strokeColor": stroke,
        "backgroundColor": bg,
        "fillStyle": "solid",
        "strokeWidth": sw,
        "roughness": 0,
        "opacity": 100,
        "angle": 0,
        "seed": next_seed(),
        "version": 1,
        "versionNonce": next_seed(),
        "isDeleted": False,
        "boundElements": None,
        "updated": 1,
        "link": None,
        "locked": False,
        "groupIds": groups,
        "roundness": r,
    }


def text(id, x, y, w, h, txt, size=12, family=3, align="left", color=TEXT, groups=[]):
    return {
        "id": id,
        "type": "text",
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "text": txt,
        "fontSize": size,
        "fontFamily": family,
        "textAlign": align,
        "strokeColor": color,
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": 1,
        "roughness": 0,
        "opacity": 100,
        "angle": 0,
        "seed": next_seed(),
        "version": 1,
        "versionNonce": next_seed(),
        "isDeleted": False,
        "boundElements": None,
        "updated": 1,
        "link": None,
        "locked": False,
        "groupIds": groups,
    }


def dot(id, x, y, color, groups=[]):
    return {
        "id": id,
        "type": "ellipse",
        "x": x,
        "y": y,
        "width": 8,
        "height": 8,
        "strokeColor": "transparent",
        "backgroundColor": color,
        "fillStyle": "solid",
        "strokeWidth": 1,
        "roughness": 0,
        "opacity": 100,
        "angle": 0,
        "seed": next_seed(),
        "version": 1,
        "versionNonce": next_seed(),
        "isDeleted": False,
        "boundElements": None,
        "updated": 1,
        "link": None,
        "locked": False,
        "groupIds": groups,
    }


def line(id, x, y, dx, dy, color=BORDER, sw=1, groups=[]):
    return {
        "id": id,
        "type": "line",
        "x": x,
        "y": y,
        "width": abs(dx),
        "height": abs(dy),
        "strokeColor": color,
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": sw,
        "roughness": 0,
        "opacity": 100,
        "angle": 0,
        "seed": next_seed(),
        "version": 1,
        "versionNonce": next_seed(),
        "isDeleted": False,
        "boundElements": None,
        "updated": 1,
        "link": None,
        "locked": False,
        "groupIds": groups,
        "points": [[0, 0], [dx, dy]],
    }


def arrow(id, x, y, dx, dy, color=MUTED, sw=1, groups=[]):
    return {
        "id": id,
        "type": "arrow",
        "x": x,
        "y": y,
        "width": abs(dx),
        "height": abs(dy),
        "strokeColor": color,
        "backgroundColor": "transparent",
        "fillStyle": "solid",
        "strokeWidth": sw,
        "roughness": 0,
        "opacity": 100,
        "angle": 0,
        "seed": next_seed(),
        "version": 1,
        "versionNonce": next_seed(),
        "isDeleted": False,
        "boundElements": None,
        "updated": 1,
        "link": None,
        "locked": False,
        "groupIds": groups,
        "points": [[0, 0], [dx, dy]],
        "startArrowhead": None,
        "endArrowhead": "arrow",
    }


elements = []

# ═══════════════════════════════════════════════════════════════
# ZONE 1: TITLE + LEGEND (y: 0-65)
# ═══════════════════════════════════════════════════════════════
elements.append(
    text(
        "z1-title",
        10,
        10,
        1200,
        35,
        "NEXUS UI - System Layout & Service Mapping (v2)",
        28,
        1,
        "left",
        TEXT,
    )
)
elements.append(
    text(
        "z1-sub",
        10,
        50,
        1200,
        16,
        "VECTRA-BOILERPLATE  |  February 2026  |  6 sections x 6 items = 36 total  |  19 services mapped in services.ts",
        11,
        3,
        "left",
        TEXT2,
    )
)

# Legend dots
elements.append(dot("z1-leg-g", 10, 76, GREEN))
elements.append(text("z1-leg-gt", 22, 74, 60, 12, "Wired", 10, 3, "left", GREEN))
elements.append(dot("z1-leg-o", 80, 76, ORANGE))
elements.append(text("z1-leg-ot", 92, 74, 80, 12, "External Only", 10, 3, "left", ORANGE))
elements.append(dot("z1-leg-x", 180, 76, GRAY))
elements.append(text("z1-leg-xt", 192, 74, 60, 12, "Scaffold", 10, 3, "left", GRAY))
elements.append(
    text(
        "z1-leg-note",
        270,
        74,
        400,
        12,
        "(External = opens new tab, cannot iframe  |  Scaffold = menu item with no backend yet)",
        10,
        3,
        "left",
        MUTED,
    )
)

# ═══════════════════════════════════════════════════════════════
# ZONE 2: UI MOCKUP (y: 100-820)
# ═══════════════════════════════════════════════════════════════
G_UI = ["ui"]

# App frame
elements.append(rect("ui-frame", 10, 100, 1280, 720, BORDER, BG, G_UI, sw=2))

# Icon rail
elements.append(rect("ui-rail", 10, 100, 56, 720, BORDER_DIM, CARD, G_UI, roundness=0))
elements.append(text("ui-brand", 22, 112, 30, 28, "V", 22, 1, "center", BLUE, G_UI))

rail_items = [
    ("DSH", BLUE, True),
    ("PIP", TEXT2, False),
    ("WRK", TEXT2, False),
    ("LIV", TEXT2, False),
    ("HST", TEXT2, False),
    ("SYS", TEXT2, False),
]
for i, (label, color, active) in enumerate(rail_items):
    ry = 152 + i * 48
    bg = "#1f6feb33" if active else "transparent"
    stroke = BLUE if active else MUTED
    elements.append(rect(f"ui-rail-{i}", 17, ry, 42, 38, stroke, bg, G_UI))
    elements.append(text(f"ui-rail-t{i}", 21, ry + 12, 34, 12, label, 10, 3, "center", color, G_UI))

# Full labels next to rail
rail_labels = ["Dashboard", "Pipeline", "Workbench", "Live", "History", "System"]
for i, lbl in enumerate(rail_labels):
    ry = 152 + i * 48
    color = BLUE if i == 0 else MUTED
    elements.append(text(f"ui-rail-l{i}", 62, ry + 14, 55, 10, lbl, 8, 3, "left", color, G_UI))

# Sidebar
elements.append(rect("ui-side", 66, 100, 250, 720, BORDER_DIM, CARD, G_UI, roundness=0))

# Sidebar header
elements.append(text("ui-side-ctx", 80, 108, 60, 10, "Context", 9, 3, "left", MUTED, G_UI))
elements.append(text("ui-side-title", 80, 122, 200, 22, "Dashboard", 18, 1, "left", TEXT, G_UI))

# Search box
elements.append(rect("ui-side-search", 80, 152, 224, 28, BORDER, BG, G_UI))
elements.append(
    text("ui-side-search-t", 92, 158, 200, 14, "Search dashboard...", 11, 3, "left", MUTED, G_UI)
)

# Group 1: OVERVIEW
elements.append(text("ui-g1", 80, 194, 200, 14, "OVERVIEW", 10, 1, "left", TEXT2, G_UI))

sidebar_items = [
    ("System Status", ORANGE, False, "Uptime Kuma"),
    ("Active Game", GREEN, False, "Foundation :9001"),
    ("Bankroll Summary", GREEN, True, "Grafana Dashboard"),
]
for i, (name, dcolor, selected, svc) in enumerate(sidebar_items):
    iy = 216 + i * 24
    if selected:
        elements.append(rect(f"ui-i{i}-hl", 74, iy - 2, 234, 22, "transparent", "#1f6feb33", G_UI))
        tc = BLUE
        ff = 1
    else:
        tc = TEXT
        ff = 3
    elements.append(dot(f"ui-i{i}-d", 84, iy + 3, dcolor, G_UI))
    elements.append(text(f"ui-i{i}", 98, iy, 200, 14, name, 12, ff, "left", tc, G_UI))

# Group 2: ACTIVITY
elements.append(text("ui-g2", 80, 292, 200, 14, "ACTIVITY", 10, 1, "left", TEXT2, G_UI))

sidebar_items2 = [
    ("Session Logs", ORANGE, "Dozzle"),
    ("Recent Alerts", GREEN, "Grafana Alerts"),
    ("Telemetry Feed", GREEN, "Grafana Explore"),
]
for i, (name, dcolor, svc) in enumerate(sidebar_items2):
    iy = 314 + i * 24
    elements.append(dot(f"ui-i{i + 3}-d", 84, iy + 3, dcolor, G_UI))
    elements.append(text(f"ui-i{i + 3}", 98, iy, 200, 14, name, 12, 3, "left", TEXT, G_UI))

# Sidebar divider
elements.append(line("ui-side-div", 80, 388, 224, 0, BORDER, 1, G_UI))

# Sidebar footer showing counts
elements.append(
    text(
        "ui-side-count",
        80,
        396,
        220,
        10,
        "4 wired  |  2 external  |  0 scaffold",
        9,
        3,
        "left",
        GREEN,
        G_UI,
    )
)

# Header bar
elements.append(rect("ui-header", 316, 100, 974, 44, BORDER_DIM, CARD, G_UI, roundness=0))
elements.append(
    text(
        "ui-bread",
        330,
        114,
        400,
        16,
        "Nexus  /  Dashboard  /  Bankroll Summary",
        12,
        3,
        "left",
        TEXT2,
        G_UI,
    )
)

# Source badge
elements.append(rect("ui-badge", 600, 110, 130, 22, BLUE, "#1f6feb22", G_UI))
elements.append(
    text("ui-badge-t", 610, 114, 110, 14, "Grafana Dashboard", 10, 3, "center", BLUE, G_UI)
)

# Open External button
elements.append(rect("ui-ext-btn", 1160, 110, 100, 24, BORDER, BORDER_DIM, G_UI))
elements.append(
    text("ui-ext-btn-t", 1168, 115, 80, 12, "Open External", 9, 3, "center", TEXT2, G_UI)
)

# Content area (iframe)
elements.append(rect("ui-content", 316, 144, 974, 636, BORDER, BG, G_UI, roundness=0))

# Mock Grafana panels inside iframe
elements.append(rect("ui-mock-p1", 336, 164, 460, 180, BORDER, "#161b2288", G_UI))
elements.append(
    text("ui-mock-p1t", 350, 174, 200, 14, "Bankroll Over Time", 12, 1, "left", TEXT2, G_UI)
)
# Fake chart line
elements.append(line("ui-mock-chart", 350, 310, 430, -80, GREEN, 2, G_UI))

elements.append(rect("ui-mock-p2", 816, 164, 454, 180, BORDER, "#161b2288", G_UI))
elements.append(text("ui-mock-p2t", 830, 174, 200, 14, "Win Rate", 12, 1, "left", TEXT2, G_UI))
elements.append(text("ui-mock-p2v", 900, 240, 200, 40, "68.4%", 36, 1, "center", GREEN, G_UI))

elements.append(rect("ui-mock-p3", 336, 364, 460, 180, BORDER, "#161b2288", G_UI))
elements.append(text("ui-mock-p3t", 350, 374, 200, 14, "Recent Trades", 12, 1, "left", TEXT2, G_UI))

elements.append(rect("ui-mock-p4", 816, 364, 454, 180, BORDER, "#161b2288", G_UI))
elements.append(text("ui-mock-p4t", 830, 374, 200, 14, "Risk Exposure", 12, 1, "left", TEXT2, G_UI))

# Watermark in iframe
elements.append(
    text(
        "ui-watermark",
        540,
        600,
        300,
        20,
        "[ Grafana iframe at /proxy/grafana/... ]",
        14,
        3,
        "center",
        MUTED,
        G_UI,
    )
)

# Footer / Command bar
elements.append(rect("ui-footer", 316, 780, 974, 40, BORDER_DIM, CARD, G_UI, roundness=0))
elements.append(rect("ui-cmd", 336, 788, 940, 26, BORDER, BG, G_UI))
elements.append(text("ui-cmd-slash", 344, 794, 10, 14, "/", 12, 3, "left", BLUE, G_UI))
elements.append(
    text(
        "ui-cmd-ph",
        358,
        794,
        400,
        14,
        "Type a command or search services...",
        11,
        3,
        "left",
        MUTED,
        G_UI,
    )
)

# ═══════════════════════════════════════════════════════════════
# ZONE 3: SERVICE ARCHITECTURE TOPOLOGY (y: 860-1280)
# ═══════════════════════════════════════════════════════════════

elements.append(text("z3-title", 10, 860, 1200, 25, "SERVICE ARCHITECTURE", 20, 1, "left", TEXT))
elements.append(
    text(
        "z3-sub",
        10,
        886,
        1200,
        14,
        "Local machine services, nginx reverse proxy, VPS services — showing port allocations and proxy routes",
        11,
        3,
        "left",
        TEXT2,
    )
)

# LOCAL MACHINE box
elements.append(rect("arch-local", 10, 920, 480, 340, BLUE, "#161b2244", ["arch"], sw=2))
elements.append(
    text("arch-local-t", 20, 928, 200, 18, "LOCAL MACHINE", 14, 1, "left", BLUE, ["arch"])
)

# Foundation
elements.append(rect("arch-found", 24, 958, 220, 44, GREEN, "#3fb95011", ["arch"]))
elements.append(
    text("arch-found-t", 34, 963, 200, 14, "Foundation Service", 11, 1, "left", GREEN, ["arch"])
)
elements.append(
    text(
        "arch-found-p", 34, 980, 200, 12, "WS :9000  |  HTTP :9001", 10, 3, "left", TEXT2, ["arch"]
    )
)

# v2-explorer
elements.append(rect("arch-expl", 258, 958, 220, 44, GREEN, "#3fb95011", ["arch"]))
elements.append(
    text("arch-expl-t", 268, 963, 200, 14, "v2-explorer (Docker)", 11, 1, "left", GREEN, ["arch"])
)
elements.append(
    text("arch-expl-p", 268, 980, 200, 12, "HTTP :9040", 10, 3, "left", TEXT2, ["arch"])
)

# Pipeline services header
elements.append(
    text(
        "arch-pipe-h",
        24,
        1016,
        450,
        14,
        "PIPELINE SERVICES (Hot Path Chain)",
        10,
        1,
        "left",
        PIPE_ORANGE,
        ["arch"],
    )
)

pipe_services = [
    ("rugs-feed", "9016"),
    ("sanitizer", "9017"),
    ("feature-ext", "9018"),
    ("decision-eng", "9019"),
    ("execution", "9020"),
    ("monitoring", "9021"),
]
for i, (name, port) in enumerate(pipe_services):
    col = i % 3
    row = i // 3
    px = 24 + col * 155
    py = 1036 + row * 50
    elements.append(rect(f"arch-p{i}", px, py, 145, 40, PIPE_ORANGE, "#e8590c11", ["arch"]))
    elements.append(
        text(f"arch-p{i}t", px + 6, py + 5, 130, 12, name, 10, 3, "left", TEXT, ["arch"])
    )
    elements.append(
        text(f"arch-p{i}p", px + 6, py + 20, 130, 12, f":{port}", 10, 3, "left", TEXT2, ["arch"])
    )

# Chrome CDP
elements.append(rect("arch-cdp", 24, 1138, 220, 34, MUTED, "transparent", ["arch"]))
elements.append(
    text("arch-cdp-t", 34, 1143, 200, 12, "Chrome CDP :9222", 10, 3, "left", TEXT2, ["arch"])
)
elements.append(
    text(
        "arch-cdp-p",
        34,
        1158,
        200,
        10,
        "rugs_bot profile + Phantom wallet",
        8,
        3,
        "left",
        MUTED,
        ["arch"],
    )
)

# NEXUS + NGINX box (middle)
elements.append(rect("arch-nginx", 520, 920, 200, 340, AMBER, "#f08c0022", ["arch"], sw=2))
elements.append(
    text("arch-nginx-t", 530, 928, 180, 18, "NEXUS UI (Docker)", 13, 1, "left", AMBER, ["arch"])
)
elements.append(
    text(
        "arch-nginx-p", 530, 948, 180, 12, "nginx :80 -> host :3000", 10, 3, "left", TEXT2, ["arch"]
    )
)

# Proxy routes
nginx_routes = [
    ("/proxy/explorer/", ":9040"),
    ("/proxy/foundation/", ":9001"),
    ("/proxy/foundation/ws", ":9000"),
    ("/proxy/rugs-feed/", ":9020*"),
    ("/proxy/grafana/", "VPS Grafana"),
    ("/proxy/grafana/ws", "VPS Grafana WS"),
]
elements.append(
    text("arch-nginx-rh", 530, 972, 180, 12, "PROXY ROUTES:", 9, 1, "left", AMBER, ["arch"])
)
for i, (route, target) in enumerate(nginx_routes):
    ry = 990 + i * 18
    elements.append(
        text(f"arch-nr{i}", 534, ry, 180, 12, f"{route}", 8, 3, "left", TEXT2, ["arch"])
    )
    elements.append(
        text(f"arch-nt{i}", 534, ry + 10, 180, 10, f"  -> {target}", 7, 3, "left", MUTED, ["arch"])
    )

# Note about rugs-feed port mismatch
elements.append(rect("arch-note", 524, 1108, 190, 46, RED, "#c92a2a11", ["arch"]))
elements.append(
    text(
        "arch-note-t", 530, 1112, 180, 12, "* BUG: nginx targets :9020", 8, 1, "left", RED, ["arch"]
    )
)
elements.append(
    text(
        "arch-note-t2",
        530,
        1126,
        180,
        12,
        "  but rugs-feed is on :9016",
        8,
        3,
        "left",
        RED,
        ["arch"],
    )
)
elements.append(
    text(
        "arch-note-t3",
        530,
        1140,
        180,
        10,
        "  Fix planned in infra plan",
        7,
        3,
        "left",
        MUTED,
        ["arch"],
    )
)

# Nginx note about Grafana port
elements.append(rect("arch-note2", 524, 1160, 190, 34, RED, "#c92a2a11", ["arch"]))
elements.append(
    text(
        "arch-note2-t",
        530,
        1164,
        180,
        12,
        "* BUG: Grafana proxy -> :32775",
        8,
        1,
        "left",
        RED,
        ["arch"],
    )
)
elements.append(
    text(
        "arch-note2-t2", 530, 1178, 180, 12, "  needs pinning to :3100", 8, 3, "left", RED, ["arch"]
    )
)

# VPS box
elements.append(rect("arch-vps", 750, 920, 540, 340, PURPLE, "#161b2244", ["arch"], sw=2))
elements.append(
    text("arch-vps-t", 760, 928, 300, 18, "VPS (72.62.160.2)", 14, 1, "left", PURPLE, ["arch"])
)
elements.append(
    text(
        "arch-vps-tail",
        920,
        932,
        200,
        12,
        "Tailscale: 100.113.138.27",
        9,
        3,
        "left",
        TEXT2,
        ["arch"],
    )
)

# VPS services - Fixed ports
elements.append(
    text("arch-vps-fh", 760, 955, 200, 12, "FIXED PORTS", 9, 1, "left", GREEN, ["arch"])
)

vps_fixed = [
    ("TimescaleDB", "5433", "PG15, service_metrics"),
    ("RabbitMQ", "5672/15672", "AMQP + Management UI"),
    ("Qdrant", "6333", "Vector search"),
    ("n8n", "5678", "Workflow automation"),
    ("RAG API", "8000", "Knowledge retrieval"),
    ("MCP Server", "8001", "Claude Code tools"),
]
for i, (name, port, desc) in enumerate(vps_fixed):
    col = i % 2
    row = i // 2
    vx = 760 + col * 265
    vy = 974 + row * 44
    elements.append(rect(f"arch-vf{i}", vx, vy, 255, 36, GREEN, "#3fb95008", ["arch"]))
    elements.append(
        text(
            f"arch-vf{i}t",
            vx + 6,
            vy + 4,
            240,
            12,
            f"{name} :{port}",
            10,
            3,
            "left",
            TEXT,
            ["arch"],
        )
    )
    elements.append(
        text(f"arch-vf{i}d", vx + 6, vy + 18, 240, 12, desc, 8, 3, "left", MUTED, ["arch"])
    )

# VPS services - Dynamic ports (need pinning)
elements.append(
    text(
        "arch-vps-dh",
        760,
        1110,
        300,
        12,
        "DYNAMIC PORTS (need pinning!)",
        9,
        1,
        "left",
        ORANGE,
        ["arch"],
    )
)

vps_dynamic = [
    ("Grafana", "32775 -> 3100", "Dashboard viz"),
    ("Metabase", "32768 -> 3101", "SQL analytics"),
    ("Uptime Kuma", "32769 -> 3102", "Health monitoring"),
    ("Dozzle", "32770 -> 8900", "Container logs"),
    ("Apprise", "32771 -> 8901", "Notifications"),
]
for i, (name, port, desc) in enumerate(vps_dynamic):
    col = i % 2
    row = i // 2
    vx = 760 + col * 265
    vy = 1130 + row * 38
    elements.append(rect(f"arch-vd{i}", vx, vy, 255, 30, ORANGE, "#f0883e08", ["arch"]))
    elements.append(
        text(
            f"arch-vd{i}t",
            vx + 6,
            vy + 3,
            240,
            12,
            f"{name}  :{port}",
            10,
            3,
            "left",
            ORANGE,
            ["arch"],
        )
    )
    elements.append(
        text(f"arch-vd{i}d", vx + 6, vy + 16, 240, 10, desc, 8, 3, "left", MUTED, ["arch"])
    )

# ═══════════════════════════════════════════════════════════════
# ZONE 4: ALL 6 SECTIONS - SERVICE MAPPING (y: 1300-1900)
# ═══════════════════════════════════════════════════════════════

elements.append(
    text("z4-title", 10, 1300, 1200, 25, "SECTION SERVICE MAPPING", 20, 1, "left", TEXT)
)
elements.append(
    text(
        "z4-sub",
        10,
        1326,
        1200,
        14,
        "All 36 menu items across 6 sections — status from services.ts cross-referenced with nginx routes",
        11,
        3,
        "left",
        TEXT2,
    )
)

sections = [
    {
        "name": "DASHBOARD",
        "color": BLUE,
        "border": "#1971c2",
        "groups": [
            (
                "Overview",
                [
                    ("System Status", ORANGE, "Uptime Kuma (ext)"),
                    ("Active Game", GREEN, "Foundation :9001"),
                    ("Bankroll Summary", GREEN, "Grafana Dashboard"),
                ],
            ),
            (
                "Activity",
                [
                    ("Session Logs", ORANGE, "Dozzle (ext)"),
                    ("Recent Alerts", GREEN, "Grafana Alerts"),
                    ("Telemetry Feed", GREEN, "Grafana Explore"),
                ],
            ),
        ],
        "stats": ("4", "2", "0"),
    },
    {
        "name": "PIPELINE",
        "color": PIPE_ORANGE,
        "border": PIPE_ORANGE,
        "groups": [
            (
                "Design",
                [
                    ("Flow Builder", ORANGE, "n8n :5678 (ext)"),
                    ("Module Registry", GREEN, "Trace Viewer :9040"),
                    ("Node Designer", GRAY, "(not wired)"),
                ],
            ),
            (
                "Management",
                [
                    ("Saved Configs", GRAY, "(not wired)"),
                    ("Environment Variables", GRAY, "(not wired)"),
                    ("Deployment Keys", GRAY, "(not wired)"),
                ],
            ),
        ],
        "stats": ("1", "1", "4"),
    },
    {
        "name": "WORKBENCH",
        "color": TEAL,
        "border": TEAL,
        "groups": [
            (
                "Explorer",
                [
                    ("Replay Lab", GREEN, "v2-explorer :9040"),
                    ("Simulation", GRAY, "(not wired)"),
                    ("Parameter Tuning", GREEN, "Explorer API Docs"),
                ],
            ),
            (
                "Debug",
                [
                    ("Trace Explorer", GREEN, "Pipeline Trace :9040"),
                    ("State Inspector", GRAY, "(not wired)"),
                    ("Log Parser", GRAY, "(not wired)"),
                ],
            ),
        ],
        "stats": ("3", "0", "3"),
    },
    {
        "name": "LIVE",
        "color": AMBER,
        "border": AMBER,
        "groups": [
            (
                "Monitoring",
                [
                    ("Active Feeds", GREEN, "Foundation WS :9001"),
                    ("Sanitizer Log", GRAY, "(not wired)"),
                    ("Risk Profile", GREEN, "Grafana Risk Panel"),
                ],
            ),
            (
                "Controls",
                [
                    ("Bet Controls", GRAY, "(not wired)"),
                    ("Trading Panel", GRAY, "(not wired)"),
                    ("Emergency Stop", GRAY, "(not wired)"),
                ],
            ),
        ],
        "stats": ("2", "0", "4"),
    },
    {
        "name": "HISTORY",
        "color": PURPLE,
        "border": PURPLE,
        "groups": [
            (
                "Archives",
                [
                    ("Game Archive", ORANGE, "Metabase :3101 (ext)"),
                    ("Past Replays", GRAY, "(not wired)"),
                    ("Audit Trails", GRAY, "(not wired)"),
                ],
            ),
            (
                "Analytics",
                [
                    ("Performance Metrics", GREEN, "Grafana Dashboard"),
                    ("ROI Analysis", GRAY, "(not wired)"),
                    ("ML Backtesting", GRAY, "(not wired)"),
                ],
            ),
        ],
        "stats": ("1", "1", "4"),
    },
    {
        "name": "SYSTEM",
        "color": RED,
        "border": RED,
        "groups": [
            (
                "Infrastructure",
                [
                    ("Node Health", ORANGE, "Uptime Kuma :3102 (ext)"),
                    ("Service Mesh", ORANGE, "Dozzle :8900 (ext)"),
                    ("Network Topology", GREEN, "RabbitMQ :15672"),
                ],
            ),
            (
                "Configuration",
                [
                    ("General Settings", GREEN, "Grafana Config"),
                    ("Profiles", GRAY, "(not wired)"),
                    ("Security Matrix", GRAY, "(not wired)"),
                ],
            ),
        ],
        "stats": ("2", "2", "2"),
    },
]

CARD_W = 410
CARD_H = 260
GAP_X = 20
GAP_Y = 20
START_Y = 1350

for si, sec in enumerate(sections):
    col = si % 3
    row = si // 3
    bx = 10 + col * (CARD_W + GAP_X)
    by = START_Y + row * (CARD_H + GAP_Y)
    gid = [f"sec-{si}"]

    # Card background
    elements.append(rect(f"s{si}-box", bx, by, CARD_W, CARD_H, sec["border"], BG, gid, sw=2))

    # Section title
    elements.append(
        text(
            f"s{si}-title", bx + 14, by + 8, 300, 20, sec["name"], 16, 1, "left", sec["color"], gid
        )
    )

    # Groups and items
    gy = by + 36
    for gi, (glabel, items) in enumerate(sec["groups"]):
        elements.append(
            text(f"s{si}-g{gi}", bx + 14, gy, 380, 14, glabel, 10, 1, "left", TEXT2, gid)
        )
        gy += 18
        for ii, (iname, icolor, itarget) in enumerate(items):
            elements.append(dot(f"s{si}-g{gi}-d{ii}", bx + 20, gy + 3, icolor, gid))
            tc = MUTED if icolor == GRAY else TEXT
            elements.append(
                text(
                    f"s{si}-g{gi}-i{ii}",
                    bx + 34,
                    gy,
                    370,
                    14,
                    f"{iname}  ->  {itarget}",
                    11,
                    3,
                    "left",
                    tc,
                    gid,
                )
            )
            gy += 20
        gy += 8  # gap between groups

    # Stats footer
    w, e, s = sec["stats"]
    wired = int(w)
    ext = int(e)
    scaffold = int(s)
    total_mapped = wired + ext
    stat_color = GREEN if scaffold == 0 else (ORANGE if total_mapped >= 3 else RED)
    elements.append(
        text(
            f"s{si}-stats",
            bx + 14,
            by + CARD_H - 22,
            380,
            14,
            f"{w}/6 wired  |  {e} external  |  {s} scaffold",
            10,
            3,
            "left",
            stat_color,
            gid,
        )
    )

# ═══════════════════════════════════════════════════════════════
# ZONE 5: PIPELINE DATA FLOW (y: 1920-2120)
# ═══════════════════════════════════════════════════════════════

PY = 1920
elements.append(
    text("z5-title", 10, PY, 1200, 25, "PIPELINE DATA FLOW (Hot Path)", 20, 1, "left", TEXT)
)
elements.append(
    text(
        "z5-sub",
        10,
        PY + 26,
        1200,
        14,
        "Direct WebSocket chain: 250ms tick budget, no LLMs in hot path  |  Cold path via RabbitMQ for analytics",
        11,
        3,
        "left",
        TEXT2,
    )
)

# Source: rugs.fun
elements.append(rect("pipe-src", 10, PY + 56, 110, 50, PURPLE, "#7048e811"))
elements.append(text("pipe-src-t", 20, PY + 64, 90, 14, "rugs.fun", 12, 1, "center", PURPLE))
elements.append(text("pipe-src-p", 20, PY + 82, 90, 10, "WebSocket", 8, 3, "center", TEXT2))

# Arrow from source
elements.append(arrow("pipe-a0", 120, PY + 81, 30, 0, MUTED))

pipeline_boxes = [
    ("rugs-feed", "9016", "WS ingest\nPRNG tracking"),
    ("sanitizer", "9017", "Dedup & validate\n106 tests"),
    ("feature-ext", "9018", "Feature vectors\n69 tests"),
    ("decision-eng", "9019", "Strategy + mode\n362 tests"),
    ("execution", "9020", "Trade execute\n78 tests"),
]

BOX_W = 150
for i, (name, port, desc) in enumerate(pipeline_boxes):
    px = 155 + i * (BOX_W + 30)
    elements.append(rect(f"pipe-b{i}", px, PY + 50, BOX_W, 62, PIPE_ORANGE, "#e8590c08"))
    elements.append(
        text(f"pipe-b{i}t", px + 8, PY + 55, BOX_W - 16, 14, name, 11, 1, "left", PIPE_ORANGE)
    )
    elements.append(
        text(f"pipe-b{i}p", px + 8, PY + 70, BOX_W - 16, 10, f":{port}", 9, 3, "left", TEXT2)
    )
    elements.append(text(f"pipe-b{i}d", px + 8, PY + 84, BOX_W - 16, 20, desc, 8, 3, "left", MUTED))

    # Arrows between boxes
    if i < len(pipeline_boxes) - 1:
        elements.append(arrow(f"pipe-a{i + 1}", px + BOX_W, PY + 81, 30, 0, MUTED))

# Monitoring (below)
elements.append(rect("pipe-mon", 1065, PY + 50, 150, 62, TEAL, "#2f9e4408"))
elements.append(text("pipe-mon-t", 1073, PY + 55, 130, 14, "monitoring", 11, 1, "left", TEAL))
elements.append(text("pipe-mon-p", 1073, PY + 70, 130, 10, ":9021 (stub)", 9, 3, "left", TEXT2))
elements.append(
    text("pipe-mon-d", 1073, PY + 84, 130, 18, "Health aggregation\nmetrics", 8, 3, "left", MUTED)
)

# Arrow to monitoring
elements.append(arrow("pipe-a-mon", 1050, PY + 81, 15, 0, MUTED))

# Cold path - RabbitMQ
elements.append(rect("pipe-rmq", 400, PY + 132, 180, 36, PURPLE, "#7048e808"))
elements.append(
    text("pipe-rmq-t", 410, PY + 138, 160, 14, "RabbitMQ (VPS :5672)", 10, 3, "left", PURPLE)
)
elements.append(
    text("pipe-rmq-d", 410, PY + 154, 160, 10, "Cold path: fire-and-forget", 8, 3, "left", MUTED)
)

# Dashed line down to RabbitMQ from sanitizer
elements.append(line("pipe-rmq-l", 305, PY + 112, 0, 30, MUTED, 1))
elements.append(arrow("pipe-rmq-a", 305, PY + 142, 95, 0, MUTED))

# TimescaleDB
elements.append(rect("pipe-tsdb", 700, PY + 132, 180, 36, BLUE, "#58a6ff08"))
elements.append(
    text("pipe-tsdb-t", 710, PY + 138, 160, 14, "TimescaleDB (VPS :5433)", 10, 3, "left", BLUE)
)
elements.append(
    text("pipe-tsdb-d", 710, PY + 154, 160, 10, "Analytics storage", 8, 3, "left", MUTED)
)
elements.append(arrow("pipe-tsdb-a", 580, PY + 150, 120, 0, MUTED))

# ═══════════════════════════════════════════════════════════════
# ZONE 6: SUMMARY (y: 2140-2220)
# ═══════════════════════════════════════════════════════════════

SY = 2140
elements.append(rect("sum-box", 10, SY, 1280, 80, BORDER, CARD))
elements.append(text("sum-title", 30, SY + 10, 300, 18, "SUMMARY", 14, 1, "left", TEXT))

elements.append(
    text(
        "sum-stats",
        30,
        SY + 34,
        900,
        14,
        "36 menu items  |  13 wired (iframe)  |  6 external-only (new tab)  |  17 scaffold slots (not wired)",
        12,
        3,
        "left",
        TEXT2,
    )
)
elements.append(
    text(
        "sum-svc",
        30,
        SY + 54,
        1200,
        14,
        "Backend services: Grafana(x4)  v2-explorer(x3)  Foundation(x2)  Uptime Kuma(x2)  Dozzle(x2)  n8n(x1)  Metabase(x1)  RabbitMQ(x1)  |  Pipeline: 5 real + 1 stub",
        10,
        3,
        "left",
        MUTED,
    )
)

# ═══════════════════════════════════════════════════════════════
# ZONE 7: PLANNED CHANGES (y: 2240-2380)
# ═══════════════════════════════════════════════════════════════

PL = 2240
elements.append(
    text("z7-title", 10, PL, 1200, 25, "PLANNED INFRASTRUCTURE CHANGES", 20, 1, "left", TEXT)
)

elements.append(rect("plan-box", 10, PL + 30, 1280, 130, AMBER, "#f08c0008", sw=2))

changes = [
    "1. Pin VPS dynamic ports: Grafana->3100, Metabase->3101, Uptime Kuma->3102, Dozzle->8900, Apprise->8901",
    "2. Fix nginx: Grafana proxy 32775->3100, rugs-feed 9020->9016",
    "3. Add pipeline proxies: /proxy/sanitizer/, /proxy/extractor/, /proxy/engine/, /proxy/monitoring/",
    "4. Wire pipeline services: Sanitizer Log, Node Designer, Bet Controls, Trading Panel into services.ts",
    "5. Add Docker health checks to nexus-ui and v2-explorer containers",
    "6. Update memory files with new fixed port assignments",
]
for i, change in enumerate(changes):
    elements.append(text(f"plan-{i}", 24, PL + 40 + i * 18, 1250, 14, change, 10, 3, "left", TEXT2))

# Build the final document
doc = {
    "type": "excalidraw",
    "version": 2,
    "source": "vectra-boilerplate",
    "elements": elements,
    "appState": {
        "gridSize": None,
        "viewBackgroundColor": BG,
    },
    "files": {},
}

json.dump(doc, sys.stdout, indent=2)
