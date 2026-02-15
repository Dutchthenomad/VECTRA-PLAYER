/**
 * Service Registry — maps menu items to live service URLs.
 *
 * URL patterns:
 *   - Relative paths (/proxy/...) route through the nginx reverse proxy (same-origin)
 *   - Absolute URLs (http://...) load directly in the iframe
 *
 * Grafana is proxied for sub-path serving (assets + cookies need same-origin).
 * Other VPS services use direct URLs — if they block iframes, the app shows a fallback.
 */

export interface ServiceEntry {
    url: string;
    label?: string;
    health?: string;
    description?: string;
    /** If true, open directly in a new tab instead of trying iframe */
    externalOnly?: boolean;
}

// VPS host
const VPS = 'http://72.62.160.2';

const SERVICE_MAP: Record<string, ServiceEntry> = {
    // ─── Dashboard ─────────────────────────────────────────
    'System Status': {
        url: `${VPS}:32769`,
        label: 'Uptime Kuma',
        description: 'Service health monitoring',
        externalOnly: true,     // blocks iframes (X-Frame-Options)
    },
    'Active Game': {
        url: '/proxy/foundation/',
        label: 'Foundation Monitor',
        description: 'Live game state from Foundation HTTP (port 9001)',
    },
    'Bankroll Summary': {
        url: '/proxy/grafana/d/1fed4809-5123-4dfb-9012-3d502c45bf7e/vectra-trading-overview?orgId=1&kiosk',
        label: 'Grafana Dashboard',
        description: 'VECTRA Trading Overview dashboard',
    },
    'Session Logs': {
        url: `${VPS}:32770`,
        label: 'Dozzle',
        description: 'Live Docker container logs',
        externalOnly: true,
    },
    'Recent Alerts': {
        url: '/proxy/grafana/alerting/list?kiosk',
        label: 'Grafana Alerts',
        description: 'Alert rules and notifications',
    },
    'Telemetry Feed': {
        url: '/proxy/grafana/explore?orgId=1&left=%7B%22datasource%22:%22cfcoqm2utet4wb%22%7D&kiosk',
        label: 'Grafana Explore',
        description: 'TimescaleDB query explorer',
    },

    // ─── Pipeline ──────────────────────────────────────────
    'Flow Builder': {
        url: `${VPS}:5678`,
        label: 'n8n',
        description: 'Visual workflow automation',
        externalOnly: true,
    },
    'Module Registry': {
        url: '/proxy/explorer/static/demo-trace.html',
        label: 'Module Registry',
        description: 'Pipeline module configuration',
    },

    // ─── Workbench ─────────────────────────────────────────
    'Replay Lab': {
        url: '/proxy/explorer/',
        label: 'v2-explorer',
        description: 'Sidebet replay engine (Gate 1)',
    },
    'Trace Explorer': {
        url: '/proxy/explorer/static/demo-trace.html',
        label: 'Pipeline Trace Viewer',
        description: 'Per-tick 5-stage pipeline trace (Gate 2)',
    },
    'Parameter Tuning': {
        url: '/proxy/explorer/docs',
        label: 'Explorer API Docs',
        description: 'FastAPI auto-docs for replay endpoints',
    },

    // ─── Live ──────────────────────────────────────────────
    'Active Feeds': {
        url: '/proxy/foundation/',
        label: 'Foundation WebSocket Monitor',
        description: 'Live WebSocket feed from rugs.fun',
    },
    'Risk Profile': {
        url: '/proxy/grafana/d/1fed4809-5123-4dfb-9012-3d502c45bf7e/vectra-trading-overview?orgId=1&viewPanel=2&kiosk',
        label: 'Risk Panel',
        description: 'Risk metrics from Grafana',
    },

    // ─── History ───────────────────────────────────────────
    'Game Archive': {
        url: `${VPS}:32768`,
        label: 'Metabase',
        description: 'SQL analytics on game data',
        externalOnly: true,
    },
    'Performance Metrics': {
        url: '/proxy/grafana/d/1fed4809-5123-4dfb-9012-3d502c45bf7e/vectra-trading-overview?orgId=1&kiosk',
        label: 'Trading Metrics',
        description: 'Grafana performance dashboard',
    },

    // ─── System ────────────────────────────────────────────
    'Node Health': {
        url: `${VPS}:32769`,
        label: 'Uptime Kuma',
        description: 'Infrastructure health checks',
        externalOnly: true,
    },
    'Service Mesh': {
        url: `${VPS}:32770`,
        label: 'Dozzle',
        description: 'Container log viewer',
        externalOnly: true,
    },
    'Network Topology': {
        url: `${VPS}:15672`,
        label: 'RabbitMQ Management',
        description: 'Message broker dashboard',
    },
    'General Settings': {
        url: '/proxy/grafana/admin/settings?kiosk',
        label: 'Grafana Settings',
        description: 'Grafana server configuration',
    },
};

export function getServiceUrl(itemName: string): ServiceEntry | null {
    return SERVICE_MAP[itemName] || null;
}

export function getAllServices(): Record<string, ServiceEntry> {
    return SERVICE_MAP;
}
