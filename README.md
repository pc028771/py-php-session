# py-php-session

Pure Python PHP session manager using Redis - compatible with PHP's redis session handler.

This library allows Python and PHP applications to share sessions stored in Redis, with proper distributed locking to prevent race conditions.

## Features

- **PHP Compatible**: Uses the same Redis key format and locking mechanism as PHP's redis session handler
- **Distributed Locking**: Proper session locking prevents concurrent modifications
- **Async Support**: Built on `redis-py` async client for high-performance async applications
- **Type Safe**: Full type hints with PEP 561 support for IDE integration
- **Framework Agnostic**: Core functionality works standalone, with optional Starlette/FastAPI middleware
- **Flexible API**: Use contextvars (via middleware) or explicit session IDs

## Installation

```bash
pip install py-php-session

# With Starlette/FastAPI support
pip install py-php-session[starlette]

# With development dependencies
pip install py-php-session[dev]
```

## Quick Start

### Basic Usage

```python
from redis.asyncio import Redis
from php_session import SessionManager, SessionConfig

# Create Redis client and session manager
redis = Redis.from_url("redis://localhost:6379")
config = SessionConfig(
    session_expire=3600,  # 1 hour
    lock_timeout=10.0,    # 10 seconds
)
manager = SessionManager(redis, config)

# Read session (no lock)
cart = await manager.get("scart_items", session_id="abc123def456...")

# Write with lock (recommended for modifications)
async with manager.lock(session_id="abc123def456...") as session:
    session["cart_count"] = 5
    session["user_id"] = 123
    # Auto-saved when exiting context
```

### With FastAPI

```python
from fastapi import FastAPI, Depends
from redis.asyncio import Redis
from php_session import SessionManager, SessionConfig, get_current_session_id
from php_session.contrib.starlette import PHPSessionMiddleware

app = FastAPI()

# Add middleware to extract PHPSESSID cookie
app.add_middleware(PHPSessionMiddleware)

# Create session manager (typically in lifespan)
redis = Redis.from_url("redis://localhost:6379")
session_manager = SessionManager(redis, SessionConfig())

@app.get("/cart")
async def get_cart():
    # Session ID is automatically available from middleware
    cart = await session_manager.get("scart_items")
    return {"cart": cart}

@app.post("/cart/add")
async def add_to_cart(item_id: int):
    # Use lock for modifications
    async with session_manager.lock() as session:
        cart = session.get("scart_items", [])
        cart.append(item_id)
        session["scart_items"] = cart
    return {"status": "ok"}
```

## Configuration

### SessionConfig

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `session_expire` | `int` | `86400` | Session TTL in seconds (24 hours) |
| `lock_timeout` | `float` | `30.0` | Lock acquisition timeout in seconds |
| `session_prefix` | `str` | `"PHPREDIS_SESSION:"` | Redis key prefix |
| `lock_suffix` | `str` | `"_LOCK"` | Lock key suffix |
| `json_fields` | `frozenset[str]` | See below | Fields containing JSON strings |
| `json_prefix` | `str \| None` | `"trace_list_"` | Prefix for auto-detecting JSON fields |

Default JSON fields that are automatically decoded:
- `scart_items`
- `ga_data`
- `session_view_log`
- `MPIReceive`

### Custom Configuration

```python
config = SessionConfig(
    session_expire=7200,        # 2 hours
    lock_timeout=5.0,           # 5 seconds
    session_prefix="MY_APP:",   # Custom prefix
    json_fields=frozenset({     # Custom JSON fields
        "cart_data",
        "user_preferences",
    }),
    json_prefix=None,           # Disable prefix matching
)
```

## API Reference

### SessionManager

#### `lock(session_id: str | None = None) -> AsyncContextManager[dict]`

Acquire a distributed lock and load session data. Modifications to the returned dict are auto-saved on exit.

```python
async with manager.lock(session_id="...") as session:
    session["key"] = "value"
```

#### `get(key: str | None = None, session_id: str | None = None) -> Any`

Read session data without locking. Returns the entire session dict if no key specified.

```python
# Get entire session
data = await manager.get(session_id="...")

# Get specific key
value = await manager.get("cart_count", session_id="...")
```

#### `set(key: str, value: Any, session_id: str | None = None) -> None`

Set a single session key. Consider using `lock()` for concurrent safety.

```python
await manager.set("cart_count", 5, session_id="...")
```

#### `save(data: dict, session_id: str | None = None) -> None`

Replace entire session data. Consider using `lock()` for concurrent safety.

```python
await manager.save({"user_id": 123, "cart": []}, session_id="...")
```

#### `delete(session_id: str | None = None) -> bool`

Delete a session. Returns `True` if session existed.

```python
deleted = await manager.delete(session_id="...")
```

#### `exists(session_id: str | None = None) -> bool`

Check if a session exists.

```python
if await manager.exists(session_id="..."):
    print("Session exists")
```

### Context Helpers

#### `set_current_session_id(session_id: str | None) -> None`

Set the session ID in contextvars (called by middleware).

#### `get_current_session_id() -> str | None`

Get the session ID from contextvars.

### Middleware

#### `PHPSessionMiddleware`

Starlette/FastAPI middleware that extracts PHPSESSID from cookies.

```python
from php_session.contrib.starlette import PHPSessionMiddleware

# Basic usage
app.add_middleware(PHPSessionMiddleware)

# With custom cookie name
app.add_middleware(PHPSessionMiddleware, cookie_name="MY_SESSION")

# With logging
import logging
logger = logging.getLogger("session")
app.add_middleware(PHPSessionMiddleware, logger=logger)
```

### Exceptions

| Exception | Description |
|-----------|-------------|
| `SessionError` | Base exception for all session errors |
| `SessionLockError` | Lock acquisition timeout |
| `SessionNotFoundError` | Session does not exist |
| `SessionContextError` | No session ID in context |

## PHP Compatibility

This library is designed to be fully compatible with PHP's redis session handler. The key format and locking mechanism match PHP exactly:

- Session key: `PHPREDIS_SESSION:{session_id}`
- Lock key: `PHPREDIS_SESSION:{session_id}_LOCK`
- Lock acquisition: `SET key token NX PX timeout_ms`
- Lock release: Lua script with token validation

### PHP Configuration

Ensure your PHP redis session is configured similarly:

```php
// php.ini
session.save_handler = redis
session.save_path = "tcp://localhost:6379?prefix=PHPREDIS_SESSION:"
```

## Migration from b2e-iopenmall

If you're migrating from the original implementation:

```python
# Before (b2e-iopenmall)
from app.core.session import SessionManager, session_manager
from app.core.config import settings

# After (py-php-session)
from php_session import SessionManager, SessionConfig
from php_session.contrib.starlette import PHPSessionMiddleware

# Create config from settings
config = SessionConfig(
    session_expire=settings.SESSION_EXPIRE,
    lock_timeout=settings.SESSION_LOCK_TIMEOUT,
)

# Create manager with config
session_manager = SessionManager(redis_client, config)
```

## License

MIT License - see LICENSE file for details.
