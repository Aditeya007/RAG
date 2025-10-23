# API Documentation

Complete API reference for the Admin Backend service.

## Base URL

**Development:** `http://localhost:5000`  
**Production:** `https://api.yourdomain.com`

All endpoints are prefixed with `/api`.

## Authentication

Most endpoints require authentication using JWT (JSON Web Tokens).

### How to Authenticate

1. Register or login to obtain a token
2. Include the token in the Authorization header for protected endpoints:

```http
Authorization: Bearer <your-jwt-token>
```

### Token Expiration

Tokens expire after 1 day (configurable via `JWT_EXPIRATION` environment variable).

---

## Endpoints

### 🔓 Public Endpoints (No Authentication Required)

#### Get API Information
```http
GET /
```

Returns basic API information and available endpoints.

**Response:**
```json
{
  "message": "Admin Backend API",
  "version": "1.0.0",
  "endpoints": [
    "POST /api/auth/register",
    "POST /api/auth/login",
    "GET /api/user/me",
    "PUT /api/user/me",
    "POST /api/bot/run",
    "GET /api/health"
  ]
}
```

---

#### Health Check
```http
GET /api/health
```

Returns service health status and MongoDB connection state.

**Response:**
```json
{
  "status": "OK",
  "timestamp": "2025-10-23T12:34:56.789Z",
  "service": "admin-backend",
  "mongodb": "connected"
}
```

**Status Codes:**
- `200 OK` - Service is healthy
- `503 Service Unavailable` - Service is unhealthy

---

### 🔐 Authentication Endpoints

#### Register New User
```http
POST /api/auth/register
```

Create a new user account.

**Rate Limit:** 5 requests per 15 minutes per IP

**Request Body:**
```json
{
  "name": "John Doe",
  "email": "john@example.com",
  "username": "johndoe",
  "password": "securePassword123"
}
```

**Validation Rules:**
- `name`: Required, 2-100 characters
- `email`: Required, valid email format
- `username`: Required, 3-30 characters, alphanumeric + underscore only
- `password`: Required, minimum 6 characters

**Success Response (201 Created):**
```json
{
  "message": "User registered successfully",
  "user": {
    "id": "507f1f77bcf86cd799439011",
    "name": "John Doe",
    "username": "johndoe",
    "email": "john@example.com"
  }
}
```

**Error Responses:**

*400 Bad Request - Validation Error:*
```json
{
  "error": "Email already in use",
  "field": "email"
}
```

*400 Bad Request - Invalid Input:*
```json
{
  "error": "Username must be at least 3 characters"
}
```

*500 Internal Server Error:*
```json
{
  "error": "Server error during registration"
}
```

---

#### Login
```http
POST /api/auth/login
```

Authenticate user and receive JWT token.

**Rate Limit:** 5 requests per 15 minutes per IP

**Request Body:**
```json
{
  "username": "johndoe",
  "password": "securePassword123"
}
```

**Validation Rules:**
- `username`: Required
- `password`: Required

**Success Response (200 OK):**
```json
{
  "message": "Login successful",
  "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOiI1MDdmMWY3N2JjZjg2Y2Q3OTk0MzkwMTEiLCJ1c2VybmFtZSI6ImpvaG5kb2UiLCJlbWFpbCI6ImpvaG5AZXhhbXBsZS5jb20iLCJpYXQiOjE2OTg3NjU0MzIsImV4cCI6MTY5ODg1MTgzMn0.xyz...",
  "user": {
    "id": "507f1f77bcf86cd799439011",
    "name": "John Doe",
    "username": "johndoe",
    "email": "john@example.com"
  }
}
```

**Error Responses:**

*401 Unauthorized - Invalid Credentials:*
```json
{
  "error": "Invalid username or password"
}
```

*400 Bad Request - Missing Fields:*
```json
{
  "error": "Username is required, Password is required"
}
```

*500 Internal Server Error:*
```json
{
  "error": "Server error during login"
}
```

---

### 👤 User Management Endpoints

#### Get Current User Profile
```http
GET /api/user/me
```

Get profile information for the authenticated user.

**Authentication:** Required  
**Rate Limit:** 50 requests per 5 minutes per IP

**Headers:**
```http
Authorization: Bearer <your-jwt-token>
```

**Success Response (200 OK):**
```json
{
  "_id": "507f1f77bcf86cd799439011",
  "name": "John Doe",
  "username": "johndoe",
  "email": "john@example.com",
  "createdAt": "2025-10-20T10:00:00.000Z",
  "updatedAt": "2025-10-23T12:00:00.000Z"
}
```

**Error Responses:**

*401 Unauthorized - No Token:*
```json
{
  "error": "No authorization header provided",
  "message": "Please provide a valid authentication token"
}
```

*401 Unauthorized - Invalid Token:*
```json
{
  "error": "Invalid token",
  "message": "Authentication token is invalid or malformed"
}
```

*401 Unauthorized - Token Expired:*
```json
{
  "error": "Token expired",
  "message": "Your session has expired. Please login again.",
  "expiredAt": "2025-10-23T12:00:00.000Z"
}
```

*404 Not Found:*
```json
{
  "error": "User not found"
}
```

---

#### Update Current User Profile
```http
PUT /api/user/me
```

Update profile information for the authenticated user.

**Authentication:** Required  
**Rate Limit:** 50 requests per 5 minutes per IP

**Headers:**
```http
Authorization: Bearer <your-jwt-token>
```

**Request Body** (all fields optional, at least one required):
```json
{
  "name": "John Updated",
  "email": "john.new@example.com",
  "username": "johnupdated",
  "password": "newSecurePassword123"
}
```

**Validation Rules:**
- `name`: If provided, 2-100 characters
- `email`: If provided, valid email format
- `username`: If provided, 3-30 characters, alphanumeric + underscore only
- `password`: If provided, minimum 6 characters

**Success Response (200 OK):**
```json
{
  "message": "Profile updated successfully",
  "user": {
    "_id": "507f1f77bcf86cd799439011",
    "name": "John Updated",
    "username": "johnupdated",
    "email": "john.new@example.com",
    "createdAt": "2025-10-20T10:00:00.000Z",
    "updatedAt": "2025-10-23T12:30:00.000Z"
  }
}
```

**Error Responses:**

*400 Bad Request - No Fields Provided:*
```json
{
  "error": "At least one field must be provided for update"
}
```

*400 Bad Request - Duplicate Email/Username:*
```json
{
  "error": "Email already in use by another user",
  "field": "email"
}
```

*400 Bad Request - Validation Error:*
```json
{
  "error": "Invalid email format"
}
```

*401 Unauthorized:*
```json
{
  "error": "Token expired",
  "message": "Your session has expired. Please login again."
}
```

*404 Not Found:*
```json
{
  "error": "User not found"
}
```

---

### 🤖 Bot Interaction Endpoints

#### Run Bot Query
```http
POST /api/bot/run
```

Send a query to the RAG chatbot and receive an answer.

**Authentication:** Required  
**Rate Limit:** 10 requests per minute per IP

**Headers:**
```http
Authorization: Bearer <your-jwt-token>
```

**Request Body:**
```json
{
  "input": "What is machine learning?"
}
```

**Validation Rules:**
- `input`: Required, non-empty, maximum 1000 characters

**Success Response (200 OK):**
```json
{
  "success": true,
  "answer": "Machine learning is a subset of artificial intelligence that focuses on the development of algorithms and statistical models that enable computers to perform tasks without explicit instructions, relying on patterns and inference instead.",
  "session_id": "user_507f1f77bcf86cd799439011_1698765432000",
  "user_id": "507f1f77bcf86cd799439011",
  "timestamp": "2025-10-23T12:34:56.789Z",
  "sources": ["document1.pdf", "document2.pdf"],
  "confidence": 0.95
}
```

**Response Fields:**
- `success`: Boolean indicating if request was successful
- `answer`: The bot's response text
- `session_id`: Unique session identifier for tracking
- `user_id`: User ID who made the request
- `timestamp`: ISO 8601 timestamp
- `sources`: (Optional) Source documents used for the answer
- `confidence`: (Optional) Confidence score (0-1)

**Error Responses:**

*400 Bad Request - Missing Input:*
```json
{
  "error": "Input query is required"
}
```

*400 Bad Request - Input Too Long:*
```json
{
  "error": "Input query is too long (max 1000 characters)"
}
```

*401 Unauthorized:*
```json
{
  "error": "Token expired",
  "message": "Your session has expired. Please login again."
}
```

*503 Service Unavailable - Bot Service Down:*
```json
{
  "success": false,
  "error": "Bot service is currently unavailable. Please try again later.",
  "errorType": "SERVICE_UNAVAILABLE",
  "timestamp": "2025-10-23T12:34:56.789Z"
}
```

*504 Gateway Timeout:*
```json
{
  "success": false,
  "error": "Bot request timed out. Please try a shorter query or try again.",
  "errorType": "TIMEOUT",
  "timestamp": "2025-10-23T12:34:56.789Z"
}
```

*500 Internal Server Error:*
```json
{
  "success": false,
  "error": "Failed to process your request",
  "errorType": "INTERNAL_ERROR",
  "timestamp": "2025-10-23T12:34:56.789Z"
}
```

---

## Rate Limiting

Rate limits are enforced per IP address:

| Endpoint Category | Limit | Window |
|------------------|-------|--------|
| Auth endpoints (`/api/auth/*`) | 5 requests | 15 minutes |
| Bot endpoints (`/api/bot/*`) | 10 requests | 1 minute |
| User endpoints (`/api/user/*`) | 50 requests | 5 minutes |
| General (all other) | 100 requests | 15 minutes |

**Rate Limit Headers:**

Response includes these headers:
```http
RateLimit-Limit: 5
RateLimit-Remaining: 4
RateLimit-Reset: 1698765432
```

**Rate Limit Exceeded Response (429 Too Many Requests):**
```json
{
  "error": "Too many authentication attempts from this IP, please try again after 15 minutes.",
  "retryAfter": "15 minutes"
}
```

---

## Error Response Format

All errors follow a consistent format:

```json
{
  "error": "Human-readable error message",
  "field": "fieldName",
  "details": "Additional details (development only)"
}
```

**Common HTTP Status Codes:**

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 201 | Created | Resource created successfully |
| 400 | Bad Request | Invalid request data |
| 401 | Unauthorized | Authentication required or failed |
| 404 | Not Found | Resource not found |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Server error (no details in production) |
| 502 | Bad Gateway | Upstream service error |
| 503 | Service Unavailable | Service temporarily unavailable |
| 504 | Gateway Timeout | Upstream service timeout |

---

## Examples

### Complete User Flow

#### 1. Register
```bash
curl -X POST http://localhost:5000/api/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Jane Smith",
    "email": "jane@example.com",
    "username": "janesmith",
    "password": "myPassword123"
  }'
```

#### 2. Login
```bash
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "username": "janesmith",
    "password": "myPassword123"
  }'
```

Save the token from the response.

#### 3. Get Profile
```bash
curl http://localhost:5000/api/user/me \
  -H "Authorization: Bearer YOUR_TOKEN_HERE"
```

#### 4. Update Profile
```bash
curl -X PUT http://localhost:5000/api/user/me \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{
    "name": "Jane Updated Smith"
  }'
```

#### 5. Ask Bot Question
```bash
curl -X POST http://localhost:5000/api/bot/run \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN_HERE" \
  -d '{
    "input": "What is artificial intelligence?"
  }'
```

### JavaScript/Fetch Example

```javascript
// Register
const registerResponse = await fetch('http://localhost:5000/api/auth/register', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    name: 'Jane Smith',
    email: 'jane@example.com',
    username: 'janesmith',
    password: 'myPassword123'
  })
});
const registerData = await registerResponse.json();

// Login
const loginResponse = await fetch('http://localhost:5000/api/auth/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    username: 'janesmith',
    password: 'myPassword123'
  })
});
const loginData = await loginResponse.json();
const token = loginData.token;

// Bot Query
const botResponse = await fetch('http://localhost:5000/api/bot/run', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json',
    'Authorization': `Bearer ${token}`
  },
  body: JSON.stringify({
    input: 'What is artificial intelligence?'
  })
});
const botData = await botResponse.json();
console.log(botData.answer);
```

### React Integration Example

```javascript
import { useState, useEffect } from 'react';

const API_BASE_URL = 'http://localhost:5000/api';

// Authentication Hook
function useAuth() {
  const [token, setToken] = useState(localStorage.getItem('token'));
  
  const login = async (username, password) => {
    const response = await fetch(`${API_BASE_URL}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password })
    });
    const data = await response.json();
    if (response.ok) {
      setToken(data.token);
      localStorage.setItem('token', data.token);
      return data;
    }
    throw new Error(data.error);
  };
  
  const logout = () => {
    setToken(null);
    localStorage.removeItem('token');
  };
  
  return { token, login, logout };
}

// Bot Query Component
function BotChat() {
  const { token } = useAuth();
  const [input, setInput] = useState('');
  const [answer, setAnswer] = useState('');
  const [loading, setLoading] = useState(false);
  
  const askBot = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE_URL}/bot/run`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ input })
      });
      const data = await response.json();
      if (response.ok) {
        setAnswer(data.answer);
      } else {
        setAnswer(`Error: ${data.error}`);
      }
    } catch (error) {
      setAnswer(`Error: ${error.message}`);
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <div>
      <input 
        value={input} 
        onChange={(e) => setInput(e.target.value)}
        placeholder="Ask a question..." 
      />
      <button onClick={askBot} disabled={loading}>
        {loading ? 'Asking...' : 'Ask'}
      </button>
      {answer && <div><strong>Answer:</strong> {answer}</div>}
    </div>
  );
}
```

---

## Versioning

Current API version: **v1.0.0**

Future versions may use URL versioning: `/api/v2/...`

---

## Support

For issues or questions about the API, please refer to:
- [README.md](./README.md) - General documentation
- [SECURITY.md](./SECURITY.md) - Security guidelines
- [DEPLOYMENT.md](./DEPLOYMENT.md) - Deployment guide

---

**Last Updated:** October 23, 2025
