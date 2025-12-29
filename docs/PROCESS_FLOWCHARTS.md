# VECTRA-PLAYER Process Flowcharts

**Version:** 1.0.0  
**Date:** December 29, 2025  
**Purpose:** ASCII flowchart documentation of all major codebase processes

This document provides comprehensive ASCII flowcharts mapping the entire codebase's processes and architecture.

---

## Table of Contents

1. [Application Lifecycle](#1-application-lifecycle)
2. [Event-Driven Architecture](#2-event-driven-architecture)
3. [Data Flow Pipeline](#3-data-flow-pipeline)
4. [Live vs Replay Mode](#4-live-vs-replay-mode)
5. [Browser Automation (CDP)](#5-browser-automation-cdp)
6. [Trading & Action Flow](#6-trading--action-flow)
7. [State Management](#7-state-management)
8. [Vector Indexing & RAG](#8-vector-indexing--rag)
9. [Testing & CI/CD](#9-testing--cicd)

---

## 1. Application Lifecycle

### 1.1 Main Application Startup Flow



**Key Initialization Order:**
1. Logging → 2. Config → 3. GameState → 4. EventBus → 5-8. Services & UI → 9. AsyncLoopManager → 10. Tkinter mainloop

---

## 2. Event-Driven Architecture

### 2.1 EventBus Core



**Event Categories:** UI, Game, Trading, Bot, File, Replay, WebSocket

---

## 3. Data Flow Pipeline



**Single Writer Pattern:** EventStoreService is the ONLY writer to Parquet files.

---

## 4. Live vs Replay Mode



**Replay:** Historical analysis, speed control, backtesting  
**Live:** Real-time capture, server-authoritative state, latency tracking

---

## 5. Browser Automation (CDP)



**Fallback:** Direct WebSocket connection if CDP unavailable.

---

## 6. Trading & Action Flow



**Latency Tracking:** client_ts → server_ts → confirmed_ts

---

## 7. State Management



**LiveStateProvider Reconciliation:**  
Server playerUpdate = CANONICAL TRUTH → Compare with local → Reconcile differences

---

## 8. Vector Indexing & RAG



**Rebuildable:** ChromaDB is derived from Parquet, can be regenerated anytime.

---

## 9. Testing & CI/CD



**Pre-commit Hooks:** Ruff linting/formatting, file checks, validation

---

## Summary

**Key Architectural Principles:**
- Event-driven (EventBus backbone)
- Single writer (EventStore → Parquet)
- Server-authoritative state (LiveStateProvider)
- Parquet as canonical truth (vector indexes rebuildable)

**For detailed flowcharts:** See sections above for component-level details.

**Related Documentation:**  
-  - Project overview  
-  - Development context  
-  - CI/CD details  
-  - Workflow automation

---

*Last Updated: December 29, 2025*  
*Version: 1.0.0*
