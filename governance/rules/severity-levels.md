# Error Severity Levels

All hooks, CI gates, and conflict detection use these levels.

| Level | Action | Example |
|-------|--------|---------|
| **INFO** | Log only, continue | "New file created in services/" |
| **WARN** | Log + notify, continue | "Test coverage dropped below 70%" |
| **BLOCK** | Prevent action, require fix | "Branch name missing project ID" |
| **REJECT** | Prevent action, log conflict | "Port 9017 already allocated" |
| **CRITICAL** | Prevent action, alert messenger bot | "Force push to main attempted" |

## Notification Routing

| Severity | Conflict Log | Apprise Alert | Session Halt |
|----------|-------------|---------------|-------------|
| INFO | Yes | No | No |
| WARN | Yes | No | No |
| BLOCK | Yes | Yes | No |
| REJECT | Yes | Yes | No |
| CRITICAL | Yes | Yes | Yes |

## Apprise Endpoint

VPS: `http://72.62.160.2:8901/notify`
