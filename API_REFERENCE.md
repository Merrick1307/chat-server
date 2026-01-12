# API Reference

Complete API documentation for the Punch Chat Server.

---

## Table of Contents

1. [Response Format](#response-format)
2. [Authentication](#authentication)
3. [Messages](#messages)
4. [Groups](#groups)
5. [WebSocket](#websocket)

---

## Response Format

All REST API endpoints return responses in a standardized format.

### APIResponse

Standard wrapper for all successful responses.

```json
{
  "success": true,
  "data": { ... },
  "message": "Optional status message",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

| Field | Type | Description |
|-------|------|-------------|
| success | boolean | Always `true` for successful responses |
| data | any | Response payload (object, array, or null) |
| message | string | Optional human-readable status message |
| timestamp | string | ISO 8601 UTC timestamp |

### ErrorResponse

Wrapper for error responses.

```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid input provided",
    "details": [
      {
        "code": "FIELD_REQUIRED",
        "message": "This field is required",
        "field": "username"
      }
    ],
    "path": "/api/v1/auth/signup",
    "method": "POST"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

| Field | Type | Description |
|-------|------|-------------|
| success | boolean | Always `false` for errors |
| error.code | string | Machine-readable error code |
| error.message | string | Human-readable error description |
| error.details | array | Optional field-level error details |
| error.path | string | Request path that caused the error |
| error.method | string | HTTP method used |

### PaginatedResponse

Used for list endpoints with pagination.

```json
{
  "success": true,
  "data": [ ... ],
  "pagination": {
    "page": 1,
    "page_size": 20,
    "total_items": 150,
    "total_pages": 8
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

## Authentication

Base path: `/api/v1/auth`

All endpoints except signup and login require a valid JWT access token in the Authorization header:
```
Authorization: Bearer <access_token>
```

### POST /signup

Register a new user account.

**Request Body:**

```json
{
  "username": "johndoe",
  "email": "john@example.com",
  "password": "securepass123",
  "first_name": "John",
  "last_name": "Doe"
}
```

| Field | Type | Required | Constraints |
|-------|------|----------|-------------|
| username | string | Yes | 3-50 characters, unique |
| email | string | Yes | Valid email format, unique |
| password | string | Yes | Minimum 8 characters |
| first_name | string | Yes | 1-255 characters |
| last_name | string | Yes | 1-255 characters |

**Response (201 Created):**

```json
{
  "success": true,
  "data": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 900
  },
  "message": "User registered successfully",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Errors:**
- `400 Bad Request`: Username or email already exists

---

### POST /login

Authenticate and receive access tokens.

**Request Body:**

```json
{
  "username": "johndoe",
  "password": "securepass123"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| username | string | Yes | Username or email address |
| password | string | Yes | User's password |

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 900
  },
  "message": "Login successful",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Errors:**
- `401 Unauthorized`: Invalid credentials

---

### POST /logout

Invalidate the refresh token.

**Request Body:**

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "success": true
  },
  "message": "Logged out successfully",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

### POST /session/refresh

Exchange refresh token for new token pair.

**Request Body:**

```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "bearer",
    "expires_in": 900
  },
  "message": "Token refreshed",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Errors:**
- `401 Unauthorized`: Invalid or expired refresh token

---

### GET /session/check

Verify session validity and get user info.

**Headers:** Requires Authorization

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "valid": true,
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "username": "johndoe",
    "email": "john@example.com"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

### GET /users/lookup/{username}

Look up a user by username to get their user_id.

**Headers:** Requires Authorization

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| username | string | Username to search for |

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "user_id": "550e8400-e29b-41d4-a716-446655440000",
    "display_name": "John Doe"
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Errors:**
- `404 Not Found`: User not found

---

## Messages

Base path: `/api/v1/messages`

All endpoints require Authorization header.

### POST /send

Send a direct message to another user.

**Request Body:**

```json
{
  "recipient_id": "550e8400-e29b-41d4-a716-446655440000",
  "content": "Hello, how are you?",
  "message_type": "text"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| recipient_id | UUID | Yes | Recipient's user ID |
| content | string | Yes | Message content (1-10000 chars) |
| message_type | string | No | Message type (default: "text") |

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "message_id": "660e8400-e29b-41d4-a716-446655440000",
    "sender_id": "550e8400-e29b-41d4-a716-446655440000",
    "recipient_id": "550e8400-e29b-41d4-a716-446655440001",
    "content": "Hello, how are you?",
    "message_type": "text",
    "created_at": "2024-01-15T10:30:00Z",
    "delivered_at": null,
    "read_at": null
  },
  "message": "Message sent",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

### GET /conversations

Get list of all conversation partners with last message and unread count.

**Response (200 OK):**

```json
{
  "success": true,
  "data": [
    {
      "partner_id": "550e8400-e29b-41d4-a716-446655440001",
      "username": "janedoe",
      "display_name": "Jane Doe",
      "last_message": "See you tomorrow!",
      "last_message_at": "2024-01-15T10:30:00Z",
      "unread_count": 3
    }
  ],
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

### GET /conversation/{user_id}

Get paginated message history with a specific user.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| user_id | UUID | Other user's ID |

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| limit | integer | 50 | Messages to retrieve (1-100) |
| offset | integer | 0 | Messages to skip |

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "messages": [
      {
        "message_id": "660e8400-e29b-41d4-a716-446655440000",
        "sender_id": "550e8400-e29b-41d4-a716-446655440000",
        "recipient_id": "550e8400-e29b-41d4-a716-446655440001",
        "content": "Hello!",
        "message_type": "text",
        "created_at": "2024-01-15T10:30:00Z",
        "delivered_at": "2024-01-15T10:30:01Z",
        "read_at": "2024-01-15T10:31:00Z"
      }
    ],
    "total": 150,
    "has_more": true
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

### GET /unread

Get all unread messages across all conversations.

**Response (200 OK):**

```json
{
  "success": true,
  "data": [
    {
      "message_id": "660e8400-e29b-41d4-a716-446655440000",
      "sender_id": "550e8400-e29b-41d4-a716-446655440001",
      "sender_username": "janedoe",
      "recipient_id": "550e8400-e29b-41d4-a716-446655440000",
      "content": "Are you there?",
      "message_type": "text",
      "created_at": "2024-01-15T10:30:00Z"
    }
  ],
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

### POST /{message_id}/read

Mark a message as read.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| message_id | UUID | Message to mark as read |

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "success": true
  },
  "message": "Message marked as read",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

## Groups

Base path: `/api/v1/groups`

All endpoints require Authorization header.

### POST /

Create a new group chat.

**Request Body:**

```json
{
  "group_name": "Project Team",
  "member_ids": [
    "550e8400-e29b-41d4-a716-446655440001",
    "550e8400-e29b-41d4-a716-446655440002"
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| group_name | string | Yes | Group name (1-100 chars) |
| member_ids | UUID[] | Yes | Initial member UUIDs |

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "group_id": "770e8400-e29b-41d4-a716-446655440000",
    "group_name": "Project Team",
    "creator_id": "550e8400-e29b-41d4-a716-446655440000",
    "created_at": "2024-01-15T10:30:00Z",
    "member_count": 3
  },
  "message": "Group created",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

### GET /my

Get all groups the current user belongs to.

**Response (200 OK):**

```json
{
  "success": true,
  "data": [
    {
      "group_id": "770e8400-e29b-41d4-a716-446655440000",
      "group_name": "Project Team",
      "creator_id": "550e8400-e29b-41d4-a716-446655440000",
      "created_at": "2024-01-15T10:30:00Z",
      "member_count": 5
    }
  ],
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

### GET /{group_id}

Get details of a specific group.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| group_id | UUID | Group ID |

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "group_id": "770e8400-e29b-41d4-a716-446655440000",
    "group_name": "Project Team",
    "creator_id": "550e8400-e29b-41d4-a716-446655440000",
    "created_at": "2024-01-15T10:30:00Z",
    "member_count": 5
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Errors:**
- `403 Forbidden`: Not a member of this group
- `404 Not Found`: Group not found

---

### GET /{group_id}/members

Get all members of a group.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| group_id | UUID | Group ID |

**Response (200 OK):**

```json
{
  "success": true,
  "data": [
    {
      "user_id": "550e8400-e29b-41d4-a716-446655440000",
      "username": "johndoe",
      "display_name": "John Doe",
      "role": "admin",
      "joined_at": "2024-01-15T10:30:00Z"
    }
  ],
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

### POST /{group_id}/members

Add members to a group.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| group_id | UUID | Group ID |

**Request Body:**

```json
{
  "user_ids": [
    "550e8400-e29b-41d4-a716-446655440003"
  ]
}
```

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "success": true,
    "added_count": 1
  },
  "message": "Members added",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

**Errors:**
- `403 Forbidden`: Not authorized to add members

---

### DELETE /{group_id}/members/{user_id}

Remove a member from a group.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| group_id | UUID | Group ID |
| user_id | UUID | User ID to remove |

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "success": true
  },
  "message": "Member removed",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

### GET /{group_id}/messages

Get paginated message history for a group.

**Path Parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| group_id | UUID | Group ID |

**Query Parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| limit | integer | 50 | Messages to retrieve (1-100) |
| offset | integer | 0 | Messages to skip |

**Response (200 OK):**

```json
{
  "success": true,
  "data": {
    "messages": [
      {
        "message_id": "880e8400-e29b-41d4-a716-446655440000",
        "group_id": "770e8400-e29b-41d4-a716-446655440000",
        "sender_id": "550e8400-e29b-41d4-a716-446655440000",
        "content": "Welcome everyone!",
        "message_type": "text",
        "created_at": "2024-01-15T10:30:00Z"
      }
    ],
    "total": 50,
    "has_more": false
  },
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

## WebSocket

### Connection

**Endpoint:** `ws://host/message?token=<access_token>`

Authentication is done via query parameter since browsers do not support custom headers during WebSocket handshake.

Upon successful connection, the server delivers any offline messages accumulated while the user was disconnected.

---

### Client to Server Messages

#### message.send

Send a direct message to another user.

```json
{
  "type": "message.send",
  "recipient_id": "550e8400-e29b-41d4-a716-446655440001",
  "content": "Hello!",
  "message_type": "text"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| type | string | Yes | Must be "message.send" |
| recipient_id | string | Yes | Recipient's user ID (UUID) |
| content | string | Yes | Message content |
| message_type | string | No | Default: "text" |

---

#### message.group.send

Send a message to a group.

```json
{
  "type": "message.group.send",
  "group_id": "770e8400-e29b-41d4-a716-446655440000",
  "content": "Hello team!",
  "message_type": "text"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| type | string | Yes | Must be "message.group.send" |
| group_id | string | Yes | Group ID (UUID) |
| content | string | Yes | Message content |
| message_type | string | No | Default: "text" |

---

#### message.read

Mark a message as read and notify the sender.

```json
{
  "type": "message.read",
  "message_id": "660e8400-e29b-41d4-a716-446655440000"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| type | string | Yes | Must be "message.read" |
| message_id | string | Yes | Message ID (UUID) |

---

#### typing

Send typing indicator to recipient or group.

```json
{
  "type": "typing",
  "recipient_id": "550e8400-e29b-41d4-a716-446655440001"
}
```

Or for groups:

```json
{
  "type": "typing",
  "group_id": "770e8400-e29b-41d4-a716-446655440000"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| type | string | Yes | Must be "typing" |
| recipient_id | string | No | For direct message typing |
| group_id | string | No | For group typing |

---

#### ping

Heartbeat to maintain connection and online status.

```json
{
  "type": "ping"
}
```

Send every 30 seconds to keep the connection alive and maintain online status in Redis.

---

### Server to Client Messages

#### message.new

New direct message received.

```json
{
  "type": "message.new",
  "message_id": "660e8400-e29b-41d4-a716-446655440000",
  "sender_id": "550e8400-e29b-41d4-a716-446655440001",
  "sender_username": "janedoe",
  "recipient_id": "550e8400-e29b-41d4-a716-446655440000",
  "content": "Hi there!",
  "message_type": "text",
  "created_at": "2024-01-15T10:30:00Z"
}
```

---

#### message.group.new

New group message received.

```json
{
  "type": "message.group.new",
  "message_id": "880e8400-e29b-41d4-a716-446655440000",
  "group_id": "770e8400-e29b-41d4-a716-446655440000",
  "sender_id": "550e8400-e29b-41d4-a716-446655440001",
  "content": "Hello everyone!",
  "message_type": "text",
  "created_at": "2024-01-15T10:30:00Z"
}
```

---

#### messages.offline

Batch of messages received while offline. Sent immediately after connection.

```json
{
  "type": "messages.offline",
  "messages": [
    {
      "message_id": "660e8400-e29b-41d4-a716-446655440000",
      "sender_id": "550e8400-e29b-41d4-a716-446655440001",
      "content": "Are you there?",
      "message_type": "text",
      "created_at": "2024-01-15T09:00:00Z"
    }
  ],
  "count": 1
}
```

---

#### message.ack

Acknowledgment that a sent message was processed.

```json
{
  "type": "message.ack",
  "message_id": "660e8400-e29b-41d4-a716-446655440000",
  "status": "delivered",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

| Status | Description |
|--------|-------------|
| delivered | Message delivered to recipient |
| queued | Recipient offline, message queued |
| saved | Message saved to database |

---

#### message.read

Notification that a message was read by the recipient.

```json
{
  "type": "message.read",
  "message_id": "660e8400-e29b-41d4-a716-446655440000",
  "reader_id": "550e8400-e29b-41d4-a716-446655440001",
  "read_at": "2024-01-15T10:31:00Z"
}
```

---

#### typing

Typing indicator from another user.

```json
{
  "type": "typing",
  "user_id": "550e8400-e29b-41d4-a716-446655440001",
  "recipient_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

Or for groups:

```json
{
  "type": "typing",
  "user_id": "550e8400-e29b-41d4-a716-446655440001",
  "group_id": "770e8400-e29b-41d4-a716-446655440000"
}
```

---

#### pong

Response to ping heartbeat.

```json
{
  "type": "pong",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

---

#### error

Error message for failed operations.

```json
{
  "type": "error",
  "code": "MISSING_RECIPIENT",
  "error": "recipient_id is required"
}
```

Common error codes:
- `MISSING_RECIPIENT`: recipient_id not provided
- `MISSING_GROUP`: group_id not provided
- `NOT_GROUP_MEMBER`: User is not a member of the specified group
- `INVALID_MESSAGE_TYPE`: Unknown message type
- `PARSE_ERROR`: Failed to parse JSON message

---

## WebSocket Status Endpoint

### GET /message/status

Get WebSocket server connection statistics.

**Response (200 OK):**

```json
{
  "connected_users": 42,
  "total_connections": 58
}
```

| Field | Type | Description |
|-------|------|-------------|
| connected_users | integer | Number of unique users connected |
| total_connections | integer | Total WebSocket connections (users may have multiple) |
