---
name: chrome-agent
description: Use when you need to complete any browser-based task agentically - navigating websites, interacting with rugs.fun, filling forms, extracting data, debugging web apps, or any task requiring a real Chrome browser with the user's logged-in sessions and extensions (Phantom wallet). Automatically handles session initialization, tab management, and multi-step browser workflows.
allowed-tools: mcp__claude-in-chrome__tabs_context_mcp, mcp__claude-in-chrome__tabs_create_mcp, mcp__claude-in-chrome__navigate, mcp__claude-in-chrome__read_page, mcp__claude-in-chrome__find, mcp__claude-in-chrome__computer, mcp__claude-in-chrome__javascript_tool, mcp__claude-in-chrome__form_input, mcp__claude-in-chrome__get_page_text, mcp__claude-in-chrome__read_console_messages, mcp__claude-in-chrome__read_network_requests, mcp__claude-in-chrome__gif_creator, mcp__claude-in-chrome__upload_image, mcp__claude-in-chrome__update_plan, mcp__claude-in-chrome__shortcuts_list, mcp__claude-in-chrome__shortcuts_execute, mcp__plugin_superpowers-chrome_chrome__use_browser
---

# Chrome Agent - Agentic Browser Automation

## Overview

Complete browser-based tasks autonomously using the user's real Chrome browser. This skill gives you full control over Chrome including access to logged-in sessions, extensions (Phantom wallet), and the ability to interact with any web page via mouse, keyboard, DOM inspection, and JavaScript execution.

**Announce:** "I'm launching Chrome to handle this browser task."

## When to Use

**Use this skill when:**
- Any task requires interacting with a website
- You need to navigate to, read, or interact with web pages
- Working with rugs.fun (wallet is connected in the browser)
- Filling forms, clicking buttons, extracting web data
- Debugging web applications (console logs, network requests)
- Taking screenshots or recording GIF demos
- Any task that would benefit from a real browser with real sessions

**Do NOT use for:**
- Reading local files (use Read tool)
- API calls that don't need a browser (use Bash with curl)
- Tasks that can be done entirely in the terminal

## Session Initialization (MANDATORY)

**Every browser session MUST start with these steps in order:**

### Step 1: Get tab context
```
mcp__claude-in-chrome__tabs_context_mcp(createIfEmpty: true)
```
This returns existing tabs in the MCP group. You need this to get valid tab IDs.

### Step 2: Create a new tab (unless reusing an existing one the user pointed to)
```
mcp__claude-in-chrome__tabs_create_mcp()
```
This creates a fresh tab in the MCP group and returns its tab ID.

### Step 3: Navigate to target
```
mcp__claude-in-chrome__navigate(url: "https://target.com", tabId: <tab_id>)
```

**CRITICAL:** Never skip Step 1. Never reuse tab IDs from previous sessions. If any tool returns a tab error, call `tabs_context_mcp` again to get fresh IDs.

## Core Tools Reference

### Navigation & Page Reading

| Tool | Purpose | When to use |
|------|---------|-------------|
| `navigate` | Go to URL, back, forward | Starting point for any page |
| `read_page` | Get accessibility tree (DOM structure) | Understanding page layout, finding interactive elements |
| `find` | Natural language element search | When you know what you want but not the selector |
| `get_page_text` | Extract raw text content | Reading articles, getting page content |
| `computer(screenshot)` | Take screenshot | Visual verification, debugging layout |

### Interaction

| Tool | Purpose | When to use |
|------|---------|-------------|
| `computer(left_click)` | Click at coordinates | Clicking buttons, links, elements |
| `computer(type)` | Type text | Filling text fields |
| `computer(key)` | Press keys | Enter, Tab, Escape, keyboard shortcuts |
| `computer(scroll)` | Scroll page | Reaching content below the fold |
| `form_input` | Set form values by ref | Filling forms (checkboxes, selects, inputs) |
| `javascript_tool` | Execute JS on page | Complex interactions, reading page state |

### Debugging

| Tool | Purpose | When to use |
|------|---------|-------------|
| `read_console_messages` | Read browser console | Debugging JS errors, checking logs |
| `read_network_requests` | Read XHR/Fetch requests | Debugging API calls, checking responses |

### Recording

| Tool | Purpose | When to use |
|------|---------|-------------|
| `gif_creator(start_recording)` | Begin recording | Before a multi-step workflow |
| `gif_creator(stop_recording)` | Stop recording | After completing the workflow |
| `gif_creator(export)` | Export as GIF | Creating shareable demos |

## Interaction Patterns

### Pattern 1: Click by Coordinates (Most Reliable)

```
1. computer(screenshot, tabId)           -- See the page
2. computer(left_click, coordinate, tabId)  -- Click target
```

Always take a screenshot first to find the exact coordinates. Click the CENTER of elements, not edges.

### Pattern 2: Click by Element Reference

```
1. read_page(tabId)                      -- Get accessibility tree with refs
2. computer(left_click, ref: "ref_42", tabId)  -- Click by reference
```

Or use `find` for natural language:
```
1. find(query: "submit button", tabId)   -- Find element
2. computer(left_click, ref: "ref_12", tabId)  -- Click the found element
```

### Pattern 3: Fill a Form

```
1. read_page(tabId, filter: "interactive")  -- Get form fields with refs
2. form_input(ref: "ref_5", value: "text", tabId)  -- Fill each field
3. computer(left_click, ref: "ref_submit", tabId)  -- Submit
```

### Pattern 4: Extract Structured Data

```
1. navigate(url, tabId)
2. javascript_tool(tabId, text: "JSON.stringify(Array.from(document.querySelectorAll('.item')).map(el => ({title: el.querySelector('h2').textContent, price: el.querySelector('.price').textContent})))")
```

### Pattern 5: Debug a Web App

```
1. navigate(url, tabId)
2. read_console_messages(tabId, pattern: "error|Error")  -- Check for errors
3. read_network_requests(tabId, urlPattern: "/api/")     -- Check API calls
4. computer(screenshot, tabId)                           -- Visual state
```

### Pattern 6: Record a GIF Demo

```
1. gif_creator(action: "start_recording", tabId)
2. computer(screenshot, tabId)           -- Capture initial frame
3. ... perform actions ...
4. computer(screenshot, tabId)           -- Capture final frame
5. gif_creator(action: "stop_recording", tabId)
6. gif_creator(action: "export", tabId, download: true, filename: "demo.gif")
```

## rugs.fun Specific

The user's Chrome has Phantom wallet connected to rugs.fun. Key pages:

- `https://rugs.fun` - Main game page (WebSocket feed active)
- Game state updates via WebSocket at `wss://api.rugs.fun/socket.io/`

When interacting with rugs.fun:
- The wallet extension is available in the browser
- Game state is real-time; take screenshots to see current state
- Use `read_network_requests` with pattern `socket.io` to monitor WebSocket traffic
- Use `read_console_messages` to see game logs

## Error Recovery

**Tab not found / invalid tab ID:**
1. Call `tabs_context_mcp()` to get fresh tab list
2. Create new tab if needed with `tabs_create_mcp()`

**Element not found:**
1. Take a screenshot to see current page state
2. Try `read_page` to get the accessibility tree
3. Try `find` with natural language description
4. Page may not have loaded - wait and retry

**Click missed the target:**
1. Take a screenshot and zoom into the area: `computer(zoom, region: [x1,y1,x2,y2])`
2. Recalculate coordinates from the zoomed view
3. Click the center of the element, not edges

**Page not loading:**
1. Check if URL is correct
2. Try `read_network_requests` for failed requests
3. Try `read_console_messages` for JS errors

## Tips

- **Always screenshot before clicking** - coordinates change as pages load/scroll
- **Use `read_page(filter: "interactive")`** to see only clickable/fillable elements
- **Use `find` for natural language** - "login button", "search bar", "cart icon"
- **Zoom to inspect small elements** - `computer(zoom, region: [100,200,300,400])`
- **Use `scroll_to` with ref** - more reliable than coordinate-based scrolling
- **Filter console messages** - always provide a `pattern` to avoid noise
- **GIF recording** - capture extra screenshots before/after actions for smooth playback
- **Parallel calls** - `tabs_context_mcp` and `tabs_create_mcp` can't be parallelized (sequential dependency), but multiple `read_page` calls on different tabs can
