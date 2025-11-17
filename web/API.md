# Paper Companion API Documentation

Complete API reference for the Paper Companion web backend.

**Base URL:** `http://localhost:8000`
**API Version:** 0.1.0
**Content-Type:** `application/json` (except file uploads)

## Authentication

Currently no authentication is required. For production deployment, consider adding API key authentication or OAuth.

## Error Handling

All errors return consistent JSON format:

```json
{
  "error": {
    "code": 404,
    "message": "Session not found: abc123",
    "path": "/sessions/abc123"
  }
}
```

### HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created |
| 204 | No Content (successful deletion) |
| 400 | Bad Request |
| 404 | Not Found |
| 422 | Validation Error |
| 500 | Internal Server Error |

---

## Sessions API

### Create Session

Create a new analysis session from PDF or Zotero.

**Endpoint:** `POST /sessions/new`

**Request (PDF Upload):**
```http
POST /sessions/new
Content-Type: multipart/form-data

file: <PDF file>
save_pdf: true (optional, default: true)
```

**Request (From Zotero):**
```http
POST /sessions/new
Content-Type: multipart/form-data

zotero_key: ZOTERO_ITEM_KEY
```

**Response:** `201 Created`
```json
{
  "session_id": "abc123def456",
  "filename": "attention_is_all_you_need.pdf",
  "initial_analysis": "This paper introduces the Transformer architecture...",
  "created_at": "2025-01-15T10:00:00.000Z",
  "updated_at": "2025-01-15T10:00:05.000Z",
  "zotero_key": null,
  "page_count": 15
}
```

**Errors:**
- `400`: Invalid file or missing parameters
- `500`: PDF processing or Claude API failure

---

### List Sessions

Get all sessions with pagination.

**Endpoint:** `GET /sessions`

**Query Parameters:**
- `limit` (optional): Maximum results (default: 50, max: 100)
- `offset` (optional): Skip first N results (default: 0)

**Example:**
```http
GET /sessions?limit=20&offset=0
```

**Response:** `200 OK`
```json
{
  "sessions": [
    {
      "session_id": "abc123",
      "filename": "paper1.pdf",
      "created_at": "2025-01-15T10:00:00Z",
      "updated_at": "2025-01-15T11:30:00Z",
      "zotero_key": null,
      "exchange_count": 5
    }
  ],
  "total": 42,
  "limit": 20,
  "offset": 0
}
```

---

### Get Session Details

Get complete session with conversation history.

**Endpoint:** `GET /sessions/{session_id}`

**Response:** `200 OK`
```json
{
  "session_id": "abc123",
  "filename": "paper.pdf",
  "initial_analysis": "This paper...",
  "created_at": "2025-01-15T10:00:00Z",
  "updated_at": "2025-01-15T11:30:00Z",
  "page_count": 10,
  "conversation": [
    {
      "id": 1,
      "role": "user",
      "content": "What is the main contribution?",
      "created_at": "2025-01-15T10:05:00Z"
    },
    {
      "id": 2,
      "role": "assistant",
      "content": "The main contribution is...",
      "model_used": "claude-sonnet-4-20250514",
      "created_at": "2025-01-15T10:05:03Z"
    }
  ],
  "metadata": {
    "total_exchanges": 5,
    "flagged_exchanges": 2,
    "highlights": 3
  }
}
```

**Errors:**
- `404`: Session not found

---

### Delete Session

Delete a session and all associated data.

**Endpoint:** `DELETE /sessions/{session_id}`

**Response:** `204 No Content`

**Errors:**
- `404`: Session not found

---

### Export Session

Export session as markdown.

**Endpoint:** `GET /sessions/{session_id}/export`

**Response:** `200 OK`
```markdown
# Paper Analysis: attention_is_all_you_need.pdf

## Initial Analysis
This paper introduces...

## Conversation

### Q: What is the main contribution?
**A:** The main contribution is...

⭐ Flagged: Key architectural insight

...
```

---

## Queries API

### Query Paper

Ask a question about the paper with full context.

**Endpoint:** `POST /sessions/{session_id}/query`

**Request:**
```json
{
  "query": "What methodology did they use?",
  "highlighted_text": "We propose a novel...",  // optional
  "page_number": 5,                             // optional
  "use_sonnet": true                            // optional, default: true
}
```

**Response:** `201 Created`
```json
{
  "exchange_id": 3,
  "response": "The authors used a controlled experiment with...",
  "model_used": "claude-sonnet-4-20250514",
  "usage": {
    "model": "claude-sonnet-4-20250514",
    "input_tokens": 2500,
    "output_tokens": 180
  }
}
```

**Notes:**
- `use_sonnet: true` uses Claude Sonnet (more capable, slower)
- `use_sonnet: false` uses Claude Haiku (faster, cheaper)
- Context includes full paper text + all previous exchanges

**Errors:**
- `404`: Session not found
- `422`: Invalid query (empty, too long, etc.)

---

### Flag Exchange

Mark an exchange as important.

**Endpoint:** `POST /sessions/{session_id}/exchanges/{exchange_id}/flag`

**Request:**
```json
{
  "note": "Key methodological insight"  // optional
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Exchange flagged successfully",
  "flag_id": 1
}
```

**Errors:**
- `404`: Session or exchange not found

---

### Unflag Exchange

Remove flag from an exchange.

**Endpoint:** `DELETE /sessions/{session_id}/exchanges/{exchange_id}/flag`

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Flag removed successfully",
  "flag_id": null
}
```

---

### List Highlights

Get all highlights for a session.

**Endpoint:** `GET /sessions/{session_id}/highlights`

**Response:** `200 OK`
```json
{
  "highlights": [
    {
      "id": 1,
      "text": "Novel attention mechanism",
      "page_number": 5,
      "exchange_id": 3,
      "created_at": "2025-01-15T10:30:00Z"
    }
  ],
  "total": 5
}
```

---

### Add Highlight

Add a text highlight to the session.

**Endpoint:** `POST /sessions/{session_id}/highlights`

**Request:**
```json
{
  "text": "Key finding to remember",
  "page_number": 10,      // optional
  "exchange_id": 5        // optional
}
```

**Response:** `201 Created`
```json
{
  "id": 7,
  "text": "Key finding to remember",
  "page_number": 10,
  "exchange_id": 5,
  "created_at": "2025-01-15T11:00:00Z"
}
```

**Errors:**
- `404`: Session not found
- `422`: Text too long or empty

---

### Delete Highlight

Delete a highlight.

**Endpoint:** `DELETE /sessions/{session_id}/highlights/{highlight_id}`

**Response:** `204 No Content`

**Errors:**
- `404`: Highlight not found

---

## Zotero API

### Search Zotero

Search your Zotero library.

**Endpoint:** `GET /zotero/search`

**Query Parameters:**
- `query` (required): Search query
- `limit` (optional): Max results (1-50, default: 10)

**Example:**
```http
GET /zotero/search?query=attention+mechanisms&limit=5
```

**Response:** `200 OK`
```json
{
  "items": [
    {
      "key": "ABC123",
      "title": "Attention Is All You Need",
      "authors": "Vaswani et al.",
      "year": "2017",
      "publication": "NeurIPS",
      "item_type": "journalArticle"
    }
  ],
  "total": 5
}
```

**Errors:**
- `500`: Zotero not configured or API error

---

### List Recent Papers

Get recently added papers from Zotero.

**Endpoint:** `GET /zotero/recent`

**Query Parameters:**
- `limit` (optional): Max results (1-100, default: 20)

**Response:** `200 OK`
```json
[
  {
    "key": "XYZ789",
    "title": "BERT: Pre-training of Deep Bidirectional Transformers",
    "authors": "Devlin et al.",
    "year": "2018",
    "publication": "NAACL",
    "item_type": "journalArticle"
  }
]
```

---

### Get Paper Details

Get full metadata for a Zotero paper.

**Endpoint:** `GET /zotero/paper/{key}`

**Response:** `200 OK`
```json
{
  "key": "ABC123",
  "version": 456,
  "library": {
    "type": "user",
    "id": 12345
  },
  "data": {
    "key": "ABC123",
    "version": 456,
    "itemType": "journalArticle",
    "title": "Attention Is All You Need",
    "creators": [
      {
        "creatorType": "author",
        "firstName": "Ashish",
        "lastName": "Vaswani"
      }
    ],
    "abstractNote": "The dominant sequence transduction models...",
    "publicationTitle": "NeurIPS",
    "date": "2017-06",
    "DOI": "10.48550/arXiv.1706.03762",
    "tags": [
      {"tag": "deep-learning"},
      {"tag": "nlp"}
    ]
  }
}
```

**Errors:**
- `404`: Paper not found
- `500`: Zotero not configured

---

### Save Insights to Zotero

Extract insights from session and save as Zotero note.

**Endpoint:** `POST /zotero/save-insights`

**Request:**
```json
{
  "session_id": "abc123",
  "parent_item_key": "ZOTERO_KEY",
  "tags": ["claude-analyzed", "critical-appraisal"]
}
```

**Response:** `200 OK`
```json
{
  "success": true,
  "message": "Insights saved successfully to Zotero",
  "note_key": null
}
```

**Process:**
1. Retrieves full session (conversation, flags, highlights)
2. Uses Claude to extract thematic insights
3. Formats as rich HTML note
4. Attaches to Zotero item with tags

**Note Format Includes:**
- Bibliographic metadata
- Strengths and weaknesses
- Methodological insights
- Key findings
- Flagged exchanges
- Highlights
- Custom themes

**Errors:**
- `404`: Session not found
- `500`: Zotero not configured or save failed

---

### Find Related Papers

Find papers in library with similar tags.

**Endpoint:** `GET /zotero/related`

**Query Parameters:**
- `tags` (required): Comma-separated tag list
- `limit` (optional): Max results per tag (1-20, default: 5)

**Example:**
```http
GET /zotero/related?tags=machine-learning,nlp&limit=5
```

**Response:** `200 OK`
```json
[
  {
    "key": "DEF456",
    "title": "BERT: Pre-training...",
    "authors": "Devlin et al.",
    "year": "2018",
    "publication": "NAACL",
    "item_type": "journalArticle"
  }
]
```

---

## Rate Limiting

**Current Status:** No rate limiting implemented.

**Recommendations for Production:**
- Claude API has rate limits (check Anthropic docs)
- Implement request throttling for expensive endpoints
- Consider caching for read-heavy operations

**Example Implementation:**
```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/sessions/{id}/query")
@limiter.limit("10/minute")
async def query_paper(...):
    ...
```

---

## Pagination

List endpoints support offset-based pagination:

```http
GET /sessions?limit=20&offset=0   # First page
GET /sessions?limit=20&offset=20  # Second page
GET /sessions?limit=20&offset=40  # Third page
```

**Response includes:**
- `total`: Total count
- `limit`: Results per page
- `offset`: Current offset

---

## Validation

Request validation uses Pydantic models. Validation errors return:

```json
{
  "error": {
    "code": 422,
    "message": "Validation error",
    "details": [
      {
        "type": "string_too_short",
        "loc": ["body", "query"],
        "msg": "String should have at least 1 character",
        "input": ""
      }
    ],
    "path": "/sessions/abc/query"
  }
}
```

---

## OpenAPI/Swagger

Interactive API documentation available at:

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **OpenAPI JSON:** http://localhost:8000/openapi.json

---

## Webhooks

**Status:** Not implemented

**Future Considerations:**
- Notify on session completion
- Alert on insight extraction
- Update on Zotero sync

---

## Versioning

**Current:** No versioning (v0.1.0 in development)

**Future:** URL-based versioning
- `/v1/sessions`
- `/v2/sessions`

---

## Best Practices

### Idempotency

- `GET` and `DELETE` requests are idempotent
- `POST` requests create new resources
- Use session IDs to avoid duplicate uploads

### Error Handling

Always check HTTP status codes and handle errors:

```python
response = requests.post(url, json=data)
if response.status_code == 200:
    result = response.json()
elif response.status_code == 404:
    print("Not found:", response.json()["error"]["message"])
else:
    print("Error:", response.json())
```

### Session Management

- Sessions persist until explicitly deleted
- Keep session IDs for later access
- Export important sessions before deletion

### Claude API Usage

- Haiku (default): Fast, cost-effective for simple queries
- Sonnet: More capable for complex analysis
- Monitor token usage in response

---

## Examples

See `examples/` directory for:
- Python client
- JavaScript/TypeScript examples
- cURL command reference
- Postman collection

---

## Changelog

### v0.1.0 (2025-01-15)
- Initial release
- Sessions, queries, and Zotero endpoints
- Insight extraction
- Full conversation history

---

For support and updates, see the main README.
