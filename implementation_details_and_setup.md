# Implementation Details

This document covers the architectural decisions, design patterns, and technical rationale behind this project (server) implementation. Have a great read

---

## Table of Contents

1. [Setup Instructions](#setup-instructions)
2. [Architecture Overview](#architecture-overview)
3. [Authentication and Authorization](#authentication-and-authorization)
4. [WebSocket Design](#websocket-design)
5. [Database Layer](#database-layer)
6. [Caching Strategy](#caching-strategy)
7. [Response Standardization](#response-standardization)
8. [Serialization](#serialization)
9. [Error Handling](#error-handling)
10. [Message Routing](#message-routing)
11. [Offline Message Delivery](#offline-message-delivery)
12. [Admin Panel](#admin-panel)
13. [Password Reset Flow](#password-reset-flow)
14. [Design Decisions & Caveats](#design-decisions--caveats)

---

## Setup Instructions

### Prerequisites

- Python 3.12+
- PostgreSQL 14+
- Redis 7+
- Docker and Docker Compose (recommended)

### Environment Configuration

1. Copy the example environment file:
   ```bash
   cp .env.example .env
   ```

2. Update `.env` with your configuration:
   ```
   DATABASE_USER=postgres
   DATABASE_PASSWORD=your_secure_password
   DATABASE_NAME=punch-chat-server
   DATABASE_URL=localhost:5432/punch-chat-server

   REDIS_HOST=localhost
   REDIS_PORT=6379
   REDIS_PASSWORD=your_redis_password
   REDIS_USER=default
   REDIS_DB=0

   JWT_SECRET=your_jwt_secret_min_32_characters
   
   # Email configuration (optional - for password reset)
   MAIL_USERNAME=your_email@gmail.com
   MAIL_PASSWORD=your_app_password
   MAIL_FROM=your_email@gmail.com
   MAIL_PORT=587
   MAIL_SERVER=smtp.gmail.com
   MAIL_STARTTLS=True
   MAIL_SSL_TLS=False
   
   # Application URLs
   APP_BASE_URL=http://localhost:8500
   CLIENT_BASE_URL=http://localhost:3005
   ```

3. For Redis ACL (if using authentication):
   ```bash
   cp users.acl.example users.acl
   ```

### Database Setup

**When using Docker Compose:** The database is automatically created by the `postgres-db` service. Migrations are run automatically on application startup via the lifespan function in `app/database/__init__.py` using [yoyo-migrations](https://ollycope.com/software/yoyo/latest/).

**When using a managed database (e.g., AWS RDS, Supabase):**

1. Create the PostgreSQL database:
   ```sql
   CREATE DATABASE "punch-chat-server";
   ```

2. Ensure your `.env` points to the managed database. Migrations will run automatically on first startup.

**Migration system:** The application uses yoyo-migrations with migration files located in `app/database/migrations/`. On each startup, the lifespan function checks for pending migrations and applies them automatically. This ensures schema consistency across all environments without manual intervention.

### Running with Docker Compose

The recommended approach for local development:

```bash
docker-compose up -d
```

This starts PostgreSQL, Redis, and the application server.

### Running Locally (Development)

1. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Start the server:
   ```bash
   uvicorn app.main:app --host 0.0.0.0 --port 8500 --reload
   ```

### Accessing the Application

- **API Documentation:** http://localhost:8500/docs
- **WebSocket Endpoint:** ws://localhost:8500/ws?token={access_token}
- **Client Interface:** Open `client/index.html` in a browser

### Health Check

Verify the server is running:
```bash
curl http://localhost:8500/health
```

---

## Architecture Overview

The application follows a layered architecture separating concerns across distinct modules:

```
Controllers (HTTP/WS endpoints)
     |
     v
Services (Business logic)
     |
     v
Database (asyncpg) / Cache (Redis)
```

**Rationale:** This separation allows each layer to evolve independently. Controllers handle request validation and response formatting. Services encapsulate business rules and can be reused across different transport mechanisms (REST, WebSocket). The data layer abstracts storage concerns.

The project uses FastAPI for its native async support and automatic OpenAPI documentation. WebSocket handling is integrated directly rather than using a separate service, reducing operational complexity for the expected scale.

---

## Authentication and Authorization

### JWT Token Structure

Access tokens contain:
- `sub`: User email (standard JWT claim)
- `user_id`: UUID as string (primary identifier for database operations)
- `username`: Display identifier
- `exp`/`iat`: Standard expiration and issued-at claims

**Design Decision:** The `user_id` field uses UUID strings rather than auto-increment integers. UUIDs prevent enumeration attacks and allow distributed ID generation without coordination. The trade-off is slightly larger storage and less human-readable identifiers.

### Token Flow

1. Login returns both access token (15 min) and refresh token (7 days)
2. Refresh tokens are hashed (SHA-256) before storage, preventing token theft from database compromise
3. Token rotation: each refresh invalidates the old token and issues new pair

### WebSocket Authentication

WebSocket connections authenticate via query parameter (`?token=...`) rather than headers because the WebSocket API in browsers does not support custom headers during the handshake. The token is validated before the connection is accepted.

```python
async def verify_and_return_jwt_payload_ws(websocket: WebSocket) -> VerifiedTokenData:
    token = websocket.query_params.get("token")
    # Validation proceeds synchronously to avoid blocking the event loop
```

---

## WebSocket Design

### Connection Management

The `WebSocketManager` maintains an in-memory mapping of user IDs to active WebSocket connections:

```python
active_connections: Dict[str, Set[WebSocket]]
```

**Multi-device Support:** Each user can have up to 5 concurrent connections (configurable via `MAX_CONNECTIONS_PER_USER`). This accommodates users on multiple devices while preventing resource exhaustion from runaway reconnection loops.

### Message Routing

Messages are routed by user UUID, not username. This was a deliberate change from an earlier design where usernames were used. UUIDs ensure:
- Consistent routing regardless of username changes
- No ambiguity from case sensitivity or special characters
- Direct database foreign key compatibility

The handler dispatches messages based on type:

```python
handlers = {
    "message.send": self._handle_direct_message,
    "message.group.send": self._handle_group_message,
    "message.read": self._handle_read_receipt,
    "typing": self._handle_typing,
    "ping": self._handle_ping,
}
```

### Heartbeat Mechanism

Clients send `ping` messages every 30 seconds. The server responds with `pong` and refreshes the user's online status in Redis. If no ping is received within the TTL window, the user is considered offline.

---

## Database Layer

### Connection Pooling

The application uses `asyncpg` with connection pooling configured at startup:

```python
pool = await asyncpg.create_pool(
    dsn=DATABASE_URL,
    min_size=5,
    max_size=20
)
```

**Pool Sizing Rationale:** The minimum of 5 connections ensures fast response for typical load without cold-start delays. The maximum of 20 prevents overwhelming the database under spike conditions while allowing reasonable concurrency.

### UUID Handling

PostgreSQL stores UUIDs natively, but they must be cast to text for JSON serialization:

```sql
SELECT message_id::text AS message_id, sender_id::text AS sender_id ...
```

This casting happens at the query level rather than in Python to:
- Reduce serialization overhead
- Ensure consistent format across all code paths
- Leverage database-level optimization

### Query Patterns

Queries use parameterized statements exclusively (`$1`, `$2`, etc.) to prevent SQL injection. The `::uuid` cast validates input format at the database level, providing defense in depth.

---

## Caching Strategy

### Redis Usage

Redis serves three primary functions:

1. **Online Status Tracking**
   - Key: `user:online:{user_id}`
   - TTL: 60 seconds (refreshed by heartbeat)
   - Enables O(1) online checks without database queries

2. **Offline Message Queue**
   - Key: `user:offline:{user_id}`
   - Structure: List of message references (not full messages)
   - TTL: 7 days
   - Stores message IDs and type, not content (content fetched from DB on delivery)

3. **Session/Rate Limiting** (future)
   - Infrastructure in place for expansion

**Why message references instead of full messages:** Storing only references reduces Redis memory usage and ensures message content is always fetched fresh from the authoritative source (PostgreSQL). This prevents stale data if messages are edited or deleted.

---

## Response Standardization

All API endpoints return a consistent response structure using dataclasses:

```python
@dataclass(slots=True)
class APIResponse:
    success: bool = True
    data: Any = None
    message: Optional[str] = None
    timestamp: str = field(default_factory=_now)
```

**Benefits:**
- Clients can rely on consistent structure for error handling
- The `success` field provides explicit status beyond HTTP codes
- Timestamps aid debugging and audit trails
- `slots=True` reduces memory footprint and improves attribute access speed

### Error Responses

Errors use a structured format:

```python
@dataclass(slots=True)
class ErrorResponse:
    error: ErrorBody  # Contains code, message, optional details
    success: bool = False
    timestamp: str = field(default_factory=_now)
```

Error codes are machine-readable strings (e.g., `VALIDATION_ERROR`, `NOT_FOUND`) while messages are human-readable.

---

## Serialization

### orjson Over stdlib json

The project uses `orjson` throughout for JSON serialization:

```python
import orjson
from fastapi.responses import JSONResponse
from typing import Any

class OrjsonResponse(JSONResponse):
    def render(self, content: Any) -> bytes:
        return orjson.dumps(
            content,
            option=orjson.OPT_SERIALIZE_NUMPY | orjson.OPT_UTC_Z | orjson.OPT_SERIALIZE_DATACLASS
        )
```

**Performance Justification:**
- orjson is 3-10x faster than stdlib json for encoding
- Native dataclass serialization eliminates manual `to_dict()` calls
- `OPT_UTC_Z` ensures consistent timezone formatting
- Returns bytes directly, avoiding intermediate string allocation

This is set as the default response class for the FastAPI application, ensuring all endpoints benefit without per-route configuration.

---

## Error Handling

### Layered Exception Strategy

1. **Service Layer:** Raises `ValueError` for business rule violations
2. **Controller Layer:** Catches service exceptions and converts to `HTTPException`
3. **Framework Layer:** FastAPI's exception handlers format the response

```python
# Service
if not user:
    raise ValueError("Invalid credentials")

# Controller
except ValueError as e:
    raise HTTPException(status_code=401, detail=str(e))
```

**Rationale:** Services remain framework-agnostic. They could be reused in a CLI tool or background worker without modification. Controllers handle HTTP-specific concerns.

### WebSocket Errors

WebSocket errors are sent as typed messages rather than closing the connection:

```python
await websocket.send_text(orjson.dumps({
    "type": "error",
    "code": "MISSING_RECIPIENT",
    "message": "recipient_id is required"
}).decode())
```

This allows clients to handle errors gracefully without reconnection overhead.

---

## Message Routing

### Direct Messages

1. Sender submits message via WebSocket with `recipient_id` (UUID)
2. Handler generates `message_id`, timestamps the message
3. Checks recipient online status via Redis
4. If online: delivers immediately, saves to DB with `delivered_at`
5. If offline: saves to DB, queues reference in Redis
6. Sends acknowledgment to sender with delivery status

### Group Messages

1. Sender submits with `group_id`
2. Handler verifies sender is a group member
3. Retrieves member list from database
4. Partitions members into online/offline via Redis
5. Delivers to online members, queues for offline
6. Saves single message record with `group_id`

**Efficiency Note:** Group messages are stored once, not duplicated per recipient. Read status is tracked in a separate `group_message_reads` junction table.

---

## Offline Message Delivery

When a user connects:

1. `deliver_offline_messages` retrieves queued message references from Redis
2. For each reference, fetches full message from database
3. Batches messages into single delivery payload
4. Marks direct messages as delivered
5. Clears the Redis queue

**Why batch delivery:** Reduces WebSocket frame overhead and allows clients to process all missed messages atomically. The batch includes a count for client-side progress indication.

### Read Receipt Handling

Read receipts were identified as a point of confusion in initial implementation. The current flow:

1. When user opens a conversation, client iterates loaded messages
2. For each unread message (where sender is not current user), calls `markAsRead` API
3. Backend updates `read_at` timestamp
4. Optionally notifies original sender via WebSocket

This ensures messages are marked read in the database, not just in client state.

---

## Performance Considerations

### Async Throughout

All I/O operations are async:
- Database queries via asyncpg
- Redis operations via redis.asyncio
- WebSocket send/receive

This maximizes throughput on a single process by avoiding thread-blocking operations.

### Memory Efficiency

- Dataclasses with `slots=True` reduce per-instance memory
- Message content is not cached in Redis (only references)
- Connection limits prevent memory exhaustion from misbehaving clients

### Potential Improvements

1. **Message pagination cursors:** Current offset-based pagination has O(n) skip cost. Cursor-based (keyset) pagination would improve for large conversations.

2. **Connection sharding:** For horizontal scaling, WebSocket connections could be distributed across nodes with Redis Pub/Sub for cross-node message routing.

3. **Read receipt batching:** Currently each message triggers an individual API call. A bulk endpoint would reduce HTTP overhead.

---

## Security Notes

- Passwords hashed with bcrypt (cost factor 12)
- Refresh tokens stored as SHA-256 hashes
- All user input parameterized in SQL queries
- WebSocket authentication required before any operations
- CORS configured (currently permissive for development)

---

## Testing Considerations

The layered architecture facilitates testing:
- Services can be unit tested with mocked database connections
- Controllers can be integration tested via FastAPI's TestClient
- WebSocket handlers can be tested with mock WebSocket objects

Database queries use explicit column selection rather than `SELECT *`, making schema changes more predictable in terms of test impact.

---

## Admin Panel

### Role-Based Access Control

The application implements role-based access control with a `role` field in the users table:

```sql
role VARCHAR(20) DEFAULT 'user'
```

Roles:
- `user`: Standard user with messaging capabilities
- `admin`: Full administrative access

### Admin Guard

Admin endpoints are protected using a FastAPI dependency:

```python
async def require_admin(auth: VerifiedTokenData = Depends(verify_jwt)) -> VerifiedTokenData:
    if auth.role != 'admin':
        raise HTTPException(status_code=403, detail="Admin access required")
    return auth
```

This pattern ensures consistent authorization across all admin endpoints without repetitive code.

### Admin Capabilities

1. **User Management**
   - View all users with pagination and search
   - View detailed user info (message count, group count)
   - Delete users
   - Promote/demote user roles

2. **Group Management**
   - View all groups
   - Create groups with any members
   - Delete groups
   - View group details with member list

3. **Online User Monitoring**
   - View currently connected users
   - Connection statistics

4. **Token Introspection**
   - View active password reset tokens
   - Manually invalidate tokens
   - Monitor TTL and expiration

---

## Password Reset Flow

### Security Architecture

Password reset uses Redis-backed tokens rather than JWT-only approach:

```
User Request → Generate Token → Store in Redis (TTL 1hr) → Send Email
                                      ↓
User Clicks Link → Validate Token (Redis) → Update Password → Invalidate Token
```

**Why Redis over JWT-only:**
- **Replay Protection**: Tokens are invalidated after use
- **Revocation**: Admins can manually invalidate tokens
- **Introspection**: Ability to view active tokens for monitoring
- **Single Use**: Guaranteed one-time use, preventing token sharing

### Token Storage

```python
class TokenCacheService:
    async def store_reset_token(self, token: str, user_id: str) -> None:
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        key = f"pwd_reset:{token_hash}"
        await self.redis.setex(key, 3600, user_id)  # 1 hour TTL
```

Tokens are hashed before storage to prevent exposure if Redis is compromised.

### Email Templates

Email templates are stored in `app/templates/` and loaded at runtime:

```
app/templates/
└── password_reset.html
```

This separation allows template customization without code changes.

---

## Design Decisions & Caveats

### Why No ORM (SQLAlchemy/Tortoise)

This project uses raw SQL with `asyncpg` instead of an ORM. Rationale:

1. **Performance**: Direct asyncpg queries have lower overhead than ORM abstraction
2. **Transparency**: SQL is explicit; no "magic" query generation
3. **Assessment Scope**: For a test/assessment project, ORM adds complexity without proportional benefit
4. **Learning Value**: Demonstrates understanding of SQL rather than ORM API

**Consequence**: The `app/models/` directory is sparse, containing only Pydantic validation models rather than ORM entities. This is intentional.

### Hard Delete vs Soft Delete

User and group deletion performs **hard delete** (permanent removal):

```sql
DELETE FROM users WHERE user_id = $1
```

**Why not soft delete:**
- This is a test/assessment project, not production
- Simplifies implementation and queries
- No regulatory requirements for data retention
- Demonstrates the functionality without added complexity

**Production Recommendation**: Implement soft delete with `deleted_at` timestamp and filter queries accordingly.

### Request/Response Models in Views

Pydantic request models (e.g., `LoginRequest`, `UpdateRoleRequest`) are placed in `app/views/` alongside response dataclasses:

```
app/views/
├── auth.py      # SignupRequest, LoginRequest, TokenResponse...
├── admin.py     # UpdateRoleRequest, CreateGroupRequest...
├── messaging.py # MessageData, GroupData...
└── responses.py # APIResponse, ErrorResponse...
```

**Rationale**: Views define the API contract (both input and output). This differs from frameworks where "views" are templates, but aligns with the REST interpretation where views represent data serialization.

### Single-Process Architecture

The application runs as a single process with in-memory WebSocket connection tracking:

```python
active_connections: Dict[str, Set[WebSocket]]
```

**Limitation**: Does not support horizontal scaling without additional infrastructure (Redis Pub/Sub for cross-node messaging).

**Why acceptable**: For assessment purposes, single-process demonstrates all concepts. Horizontal scaling would require:
- Redis Pub/Sub for WebSocket message routing
- Sticky sessions or connection state externalization
- Load balancer with WebSocket support

### No Message Encryption

Messages are stored in plaintext in PostgreSQL:

```sql
content TEXT NOT NULL
```

**Why**: End-to-end encryption adds significant complexity (key exchange, client-side encryption) beyond assessment scope.

**Production Recommendation**: Implement E2E encryption with client-managed keys.

### Test Users in Seed Data

Development mode seeds test users with known passwords:

```python
# Admin: admin / admin123
# Users: alice, bob, charlie, diana / password123
```

**Security Note**: DEV_MODE should not be enabled in production. The seed function checks `DEV_MODE` environment variable before inserting test data.
