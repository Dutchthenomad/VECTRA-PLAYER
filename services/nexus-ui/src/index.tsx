
/**
 * @license
 * SPDX-License-Identifier: Apache-2.0
 *
 * Nexus UI — Unified control panel for VECTRA microservices.
 * Based on Flash UI by Google AI Studio, adapted for service orchestration.
 */

import React, { useState, useCallback, useMemo, useRef, useLayoutEffect, useEffect } from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';

import { Artifact, Session } from './types';
import { generateId } from './utils';
import { getServiceUrl } from './services';

import DottedGlowBackground from './components/DottedGlowBackground';
import {
    ThinkingIcon,
    ArrowUpIcon,
    WorkflowIcon,
    MonitorIcon,
    SettingsIcon,
    SearchIcon,
    ChevronDownIcon,
    DashboardIcon,
    WorkbenchIcon,
    LiveIcon,
    HistoryIcon
} from './components/Icons';

type ViewMode = 'dashboard' | 'pipeline' | 'workbench' | 'live' | 'history' | 'system';

interface ViewContext {
    selectedItem: string | null;
    expandedGroups: Set<number>;
    scrollPosition: number;
}

function App() {
  const [activeView, setActiveView] = useState<ViewMode>('dashboard');
  const [sessions, setSessions] = useState<Session[]>([]);
  const [currentSessionIndex, setCurrentSessionIndex] = useState<number>(-1);
  const [inputValue, setInputValue] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isSidebarCollapsed, setIsSidebarCollapsed] = useState(false);
  const [iframeKey, setIframeKey] = useState(0);

  const sidebarScrollRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  const [viewContexts, setViewContexts] = useState<Record<ViewMode, ViewContext>>({
    dashboard: { selectedItem: 'Bankroll Summary', expandedGroups: new Set([0, 1]), scrollPosition: 0 },
    pipeline: { selectedItem: 'Flow Builder', expandedGroups: new Set([0, 1]), scrollPosition: 0 },
    workbench: { selectedItem: 'Trace Explorer', expandedGroups: new Set([0, 1]), scrollPosition: 0 },
    live: { selectedItem: 'Active Feeds', expandedGroups: new Set([0, 1]), scrollPosition: 0 },
    history: { selectedItem: 'Game Archive', expandedGroups: new Set([0, 1]), scrollPosition: 0 },
    system: { selectedItem: 'Node Health', expandedGroups: new Set([0, 1]), scrollPosition: 0 },
  });

  const navigation = useMemo(() => [
    { id: 'dashboard', icon: <DashboardIcon />, label: 'Dashboard' },
    { id: 'pipeline', icon: <WorkflowIcon />, label: 'Pipeline' },
    { id: 'workbench', icon: <WorkbenchIcon />, label: 'Workbench' },
    { id: 'live', icon: <LiveIcon />, label: 'Live' },
    { id: 'history', icon: <HistoryIcon />, label: 'History' },
    { id: 'system', icon: <SettingsIcon />, label: 'System' },
  ], []);

  const secondaryMenuData = useMemo(() => ({
    dashboard: [
      { label: 'Overview', items: ['System Status', 'Active Game', 'Bankroll Summary'] },
      { label: 'Activity', items: ['Session Logs', 'Recent Alerts', 'Telemetry Feed'] }
    ],
    pipeline: [
      { label: 'Design', items: ['Flow Builder', 'Module Registry', 'Node Designer'] },
      { label: 'Management', items: ['Saved Configs', 'Environment Variables', 'Deployment Keys'] }
    ],
    workbench: [
      { label: 'Explorer', items: ['Replay Lab', 'Simulation', 'Parameter Tuning'] },
      { label: 'Debug', items: ['Trace Explorer', 'State Inspector', 'Log Parser'] }
    ],
    live: [
      { label: 'Monitoring', items: ['Active Feeds', 'Sanitizer Log', 'Risk Profile'] },
      { label: 'Controls', items: ['Bet Controls', 'Trading Panel', 'Emergency Stop'] }
    ],
    history: [
      { label: 'Archives', items: ['Game Archive', 'Past Replays', 'Audit Trails'] },
      { label: 'Analytics', items: ['Performance Metrics', 'ROI Analysis', 'ML Backtesting'] }
    ],
    system: [
      { label: 'Infrastructure', items: ['Node Health', 'Service Mesh', 'Network Topology'] },
      { label: 'Configuration', items: ['General Settings', 'Profiles', 'Security Matrix'] }
    ]
  }), []);

  useLayoutEffect(() => {
    if (sidebarScrollRef.current) {
        sidebarScrollRef.current.scrollTop = viewContexts[activeView].scrollPosition;
    }
  }, [activeView]);

  const handleScroll = useCallback(() => {
    if (sidebarScrollRef.current) {
        const scrollTop = sidebarScrollRef.current.scrollTop;
        setViewContexts(prev => {
            if (prev[activeView].scrollPosition === scrollTop) return prev;
            return {
                ...prev,
                [activeView]: { ...prev[activeView], scrollPosition: scrollTop }
            };
        });
    }
  }, [activeView]);

  const handleViewChange = (newView: ViewMode) => {
    setActiveView(newView);
    setIframeKey(k => k + 1);
  };

  const handleSecondaryItemClick = (item: string) => {
    setViewContexts(prev => ({
        ...prev,
        [activeView]: { ...prev[activeView], selectedItem: item }
    }));
    setIframeKey(k => k + 1);
  };

  const toggleGroup = (groupIdx: number) => {
    setViewContexts(prev => {
        const newSet = new Set(prev[activeView].expandedGroups);
        if (newSet.has(groupIdx)) newSet.delete(groupIdx);
        else newSet.add(groupIdx);
        return {
            ...prev,
            [activeView]: { ...prev[activeView], expandedGroups: newSet }
        };
    });
  };

  const handleSendMessage = useCallback(async () => {
    if (!inputValue.trim() || isLoading) return;

    const prompt = inputValue.trim();
    setInputValue('');
    setIsLoading(true);

    const sessionId = generateId();
    const newSession: Session = {
        id: sessionId,
        prompt: prompt,
        timestamp: Date.now(),
        artifacts: [{
            id: generateId(),
            styleName: 'AI Generated Module',
            html: '',
            status: 'streaming'
        }]
    };

    setSessions(prev => [...prev, newSession]);
    setCurrentSessionIndex(sessions.length);

    try {
        const { GoogleGenAI } = await import('@google/genai');
        const apiKey = process.env.API_KEY;
        if (!apiKey || apiKey === 'PLACEHOLDER_API_KEY') {
            throw new Error('Set GEMINI_API_KEY in .env.local to enable AI generation');
        }
        const ai = new GoogleGenAI({ apiKey });

        const responseStream = await ai.models.generateContentStream({
            model: 'gemini-3-flash-preview',
            contents: [{
                role: 'user',
                parts: [{
                    text: `Create a professional, high-density dashboard module for: "${prompt}".
                    Context: VECTRA Pipeline System - view: ${activeView}, section: ${viewContexts[activeView].selectedItem}.
                    Style: Technical, dark-mode, using clean CSS with JetBrains Mono font.
                    Dark background (#0d1117), green (#3fb950) for positive, red (#f85149) for negative.
                    No external deps. Return ONLY the complete HTML.`
                }]
            }],
        });

        let accumulatedHtml = '';
        for await (const chunk of responseStream) {
            accumulatedHtml += chunk.text;
            setSessions(prev => prev.map(s => s.id === sessionId ? {
                ...s,
                artifacts: s.artifacts.map(a => ({ ...a, html: accumulatedHtml }))
            } : s));
        }

        setSessions(prev => prev.map(s => s.id === sessionId ? {
            ...s,
            artifacts: s.artifacts.map(a => ({ ...a, status: 'complete' }))
        } : s));

    } catch (e: any) {
        const errorHtml = `<html><body style="background:#0d1117;color:#f85149;font-family:monospace;padding:40px;">
            <h2>Generation Error</h2><p>${e.message || 'Unknown error'}</p>
            <p style="color:#8b949e;margin-top:20px;">Tip: Set GEMINI_API_KEY in .env.local to enable AI module generation.</p>
        </body></html>`;
        setSessions(prev => prev.map(s => s.id === sessionId ? {
            ...s,
            artifacts: s.artifacts.map(a => ({ ...a, html: errorHtml, status: 'complete' }))
        } : s));
    } finally {
        setIsLoading(false);
    }
  }, [inputValue, isLoading, sessions, activeView, viewContexts]);

  const currentArtifact = sessions[currentSessionIndex]?.artifacts[0];
  const currentContext = viewContexts[activeView];
  const activeService = currentContext.selectedItem ? getServiceUrl(currentContext.selectedItem) : null;

  return (
    <div className="nexus-app">
        {/* Primary Sidebar - Icon Rail */}
        <nav className="primary-sidebar">
            <div className="brand-logo" title="VECTRA Nexus">
                <div className="logo-text">V</div>
            </div>
            <div className="nav-icons">
                {navigation.map(item => (
                    <button
                        key={item.id}
                        className={`nav-btn ${activeView === item.id ? 'active' : ''}`}
                        onClick={() => handleViewChange(item.id as ViewMode)}
                        title={item.label}
                    >
                        {item.icon}
                        <span className="nav-tooltip">{item.label}</span>
                    </button>
                ))}
            </div>
            <div className="user-profile">
                <div className="avatar-placeholder" />
            </div>
        </nav>

        {/* Secondary Sidebar - Contextual Menu */}
        <aside className={`secondary-sidebar ${isSidebarCollapsed ? 'collapsed' : ''}`}>
            <div className="secondary-sidebar-inner">
                <div className="sidebar-header">
                    <div className="header-view-visual">
                        <div className="view-title-wrap">
                            <span className="context-label">Context</span>
                            <h3>{navigation.find(n => n.id === activeView)?.label}</h3>
                        </div>
                    </div>
                    <div className="search-bar">
                        <SearchIcon />
                        <input type="text" placeholder={`Search ${activeView}...`} />
                    </div>
                </div>

                <div
                    className="sidebar-content"
                    ref={sidebarScrollRef}
                    onScroll={handleScroll}
                >
                    {secondaryMenuData[activeView].map((group, idx) => (
                        <div className="menu-group" key={idx}>
                            <div
                                className="group-label clickable"
                                onClick={() => toggleGroup(idx)}
                            >
                                {group.label}
                                <ChevronDownIcon style={{ transform: currentContext.expandedGroups.has(idx) ? 'rotate(0deg)' : 'rotate(-90deg)', transition: 'transform 0.2s' }} />
                            </div>
                            {currentContext.expandedGroups.has(idx) && (
                                <div className="menu-items">
                                    {group.items.map((item, i) => {
                                        const svc = getServiceUrl(item);
                                        return (
                                            <div
                                                key={i}
                                                className={`menu-item ${currentContext.selectedItem === item ? 'active' : ''}`}
                                                onClick={() => handleSecondaryItemClick(item)}
                                                title={svc?.description || item}
                                            >
                                                <span className="item-text">{item}</span>
                                                {svc ? (
                                                    <span className="status running" />
                                                ) : (
                                                    <span className="status-placeholder" />
                                                )}
                                            </div>
                                        );
                                    })}
                                </div>
                            )}
                        </div>
                    ))}
                </div>
            </div>

            <button
                className={`collapse-toggle ${isSidebarCollapsed ? 'is-collapsed' : ''}`}
                onClick={() => setIsSidebarCollapsed(!isSidebarCollapsed)}
                title={isSidebarCollapsed ? "Expand Sub-Menu" : "Collapse Sub-Menu"}
            >
                {isSidebarCollapsed ? '\u2192' : '\u2190'}
            </button>
        </aside>

        {/* Main Workspace */}
        <main className="main-workspace">
            <header className="workspace-header">
                <div className="header-left">
                    <button
                        className={`sidebar-open-btn ${isSidebarCollapsed ? 'visible' : ''}`}
                        onClick={() => setIsSidebarCollapsed(false)}
                        title="Restore Navigator"
                    >
                        <WorkflowIcon />
                    </button>
                    <div className="breadcrumb">
                        <span className="root-node">Nexus</span> / <span className="view-name">{activeView}</span> / <span className="active">{currentContext.selectedItem || 'Overview'}</span>
                        {activeService && <span className="service-badge">{activeService.label}</span>}
                    </div>
                </div>
                <div className="header-actions">
                    {activeService && (
                        <a
                            className="btn-open-external"
                            href={activeService.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            title="Open in new tab"
                        >
                            Open External
                        </a>
                    )}
                    <div className="system-health">
                        <span className="health-label">VPS:</span>
                        <span className="health-val">72.62.160.2</span>
                        <div className="health-dot" />
                    </div>
                </div>
            </header>

            <section className="workspace-content">
                <DottedGlowBackground gap={32} radius={1.2} color="rgba(255,255,255,0.025)" glowColor="rgba(59, 130, 246, 0.4)" />

                {activeService && activeService.externalOnly ? (
                    /* External-only service — can't be iframed */
                    <div className="welcome-hero">
                        <h1 className="hero-title">{activeService.label || currentContext.selectedItem}</h1>
                        <p className="hero-desc">
                            This service doesn't support embedded viewing. Open it in a new tab to access the full interface.
                        </p>
                        <div className="quick-stats">
                            <div className="stat-card">
                                <span className="label">Service</span>
                                <span className="val">{activeService.label}</span>
                            </div>
                            <div className="stat-card">
                                <span className="label">Host</span>
                                <span className="val">72.62.160.2</span>
                            </div>
                            <div className="stat-card">
                                <span className="label">Status</span>
                                <span className="val" style={{color:'#3fb950'}}>Online</span>
                            </div>
                        </div>
                        <a
                            className="btn-open-external"
                            href={activeService.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            style={{display:'inline-block', marginTop:'24px', fontSize:'15px', padding:'10px 28px'}}
                        >
                            Open {activeService.label} &rarr;
                        </a>
                    </div>
                ) : activeService ? (
                    /* Service iframe — the core feature */
                    <div className="service-frame-container">
                        <iframe
                            key={iframeKey}
                            src={activeService.url}
                            title={activeService.label || currentContext.selectedItem || ''}
                            className="service-iframe"
                            sandbox="allow-scripts allow-same-origin allow-forms allow-popups allow-modals"
                            allow="clipboard-read; clipboard-write"
                        />
                    </div>
                ) : currentArtifact ? (
                    /* AI-generated module */
                    <div className="artifact-container">
                        <div className="artifact-frame">
                            {currentArtifact.status === 'streaming' && (
                                <div className="streaming-indicator">
                                    <div className="thinking-dot-wrap">
                                        <div className="dot" />
                                        <div className="dot" />
                                        <div className="dot" />
                                    </div>
                                    <span>Generating module...</span>
                                </div>
                            )}
                            <iframe
                                srcDoc={currentArtifact.html}
                                title="Generated Module"
                                sandbox="allow-scripts allow-same-origin"
                            />
                        </div>
                    </div>
                ) : (
                    /* Empty state — no service mapped */
                    <div className="welcome-hero">
                        <h1 className="hero-title">{currentContext.selectedItem || navigation.find(n => n.id === activeView)?.label}</h1>
                        <p className="hero-desc">
                            No service wired to this panel yet. Use the command bar below to generate a placeholder module with AI,
                            or add a service URL in <code>src/services.ts</code>.
                        </p>
                        <div className="quick-stats">
                            <div className="stat-card">
                                <span className="label">View</span>
                                <span className="val">{activeView}</span>
                            </div>
                            <div className="stat-card">
                                <span className="label">Panel</span>
                                <span className="val">{currentContext.selectedItem || '—'}</span>
                            </div>
                            <div className="stat-card">
                                <span className="label">Status</span>
                                <span className="val">Scaffold</span>
                            </div>
                        </div>
                    </div>
                )}
            </section>

            {/* Generative Assistant Bar */}
            <footer className="footer-assistant">
                <div className="input-container">
                    <div className="input-glow" />
                    <div className="input-field">
                        <div className="input-prefix">
                            <span className="input-prompt-symbol">/</span>
                        </div>
                        <input
                            ref={inputRef}
                            value={inputValue}
                            onChange={(e) => setInputValue(e.target.value)}
                            onKeyDown={(e) => e.key === 'Enter' && handleSendMessage()}
                            placeholder={`Generate module for ${currentContext.selectedItem || activeView}...`}
                            disabled={isLoading}
                        />
                        <button className="send-btn" onClick={handleSendMessage} disabled={isLoading || !inputValue.trim()}>
                            {isLoading ? <ThinkingIcon /> : <ArrowUpIcon />}
                        </button>
                    </div>
                </div>
            </footer>
        </main>
    </div>
  );
}

const rootElement = document.getElementById('root');
if (rootElement) {
  const root = ReactDOM.createRoot(rootElement);
  root.render(<App />);
}
