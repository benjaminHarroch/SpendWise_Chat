# SpendWise Chat – System Architecture

## 1. High-Level Architecture

SpendWise Chat is a backend system that:
1) Receives WhatsApp messages via webhook  
2) Stores raw messages  
3) Processes messages asynchronously (queue + worker)  
4) Uses an LLM to extract structured expense data  
5) Stores expenses in PostgreSQL  
6) Answers analytics questions via SQL + optional LLM intent parsing  
7) Sends replies back to WhatsApp

**Core principle:**  
- **LLM = extraction + intent parsing** (language understanding)  
- **SQL/Postgres = truth + calculations** (accurate analytics)

---

## 2. Main Components (What each thing is + why)

### 2.1 WhatsApp Cloud API
**What:** WhatsApp Business Platform (Cloud API) delivers inbound messages to your server and allows your server to send replies.

**Why:** Real integration that feels “production-like” and interview-worthy.

**Key concept:** WhatsApp does **HTTP POST** to your webhook URL when a message arrives.

---

### 2.2 Webhook Service (FastAPI)
**What:** An HTTP endpoint your server exposes (e.g., `POST /webhooks/whatsapp`) that WhatsApp calls when an event happens (incoming message).

**Why:** Webhooks are the standard for real-time inbound events.  
Polling (asking WhatsApp repeatedly) is slower, costly, and not scalable.

**Responsibilities:**
- Verify/validate the webhook request
- Extract minimal metadata
- Persist the raw message payload (audit/debug)
- Enqueue a background job for processing
- Return HTTP 200 quickly

---

### 2.3 Queue (Redis) + Background Worker
**What:** A queue stores jobs (tasks) to be processed later. A worker pulls jobs and executes them.

**Why:** LLM calls + DB writes + analytics may take seconds.  
You don’t want the webhook request to “wait” and risk timeout/retry storms.

**Responsibilities:**
- Decouple inbound webhook from heavy processing
- Enable retries for transient errors (LLM timeouts, network)
- Scale processing by running multiple workers

---

### 2.4 LLM Extraction Service
**What:** A module that sends user text to an LLM and receives structured JSON back.

**Why:** Users write expenses in free-form language. Rules/regex break quickly.
LLM extraction is robust across Hebrew/English and many phrasing styles.

**Responsibilities:**
- Convert message text → `ExpenseEvent` JSON
- Auto-detect category (restaurant, entertainment, etc.)
- Provide confidence/validation signals (optional)

**Important rule:**  
LLM output must be validated with a strict schema (Pydantic) before storing.

---

### 2.5 Database (PostgreSQL)
**What:** Primary source of truth.

**Why:** The project is analytics-heavy (“sum by category”, “weekly totals”, “top spender”).  
SQL is accurate and reliable for calculations.

**Responsibilities:**
- Store users
- Store raw inbound messages
- Store extracted expense events
- Support analytics queries

---

### 2.6 Analytics Service
**What:** A layer that runs SQL queries (aggregations) and formats results.

**Why:** Calculations must be deterministic (not “LLM math”).

**Responsibilities:**
- Weekly/monthly summaries
- Totals by category
- Totals by user
- Top spender / lowest spender

---

### 2.7 Query Intent Router (Natural Language Questions)
**What:** Detect whether a user message is:
- an expense report
- an analytics question
- something else (help, unknown)

**Why:** Same WhatsApp channel should support both “record” and “ask”.

**How:**
- Option A (recommended): LLM intent classification with strict output schema  
- Option B: simple rules first (fast), fallback to LLM

---

### 2.8 Reply Sender (WhatsApp Outbound)
**What:** Sends response messages back through WhatsApp Cloud API.

**Why:** Closes the loop: user sends message → system responds.

---

## 3. Data Model (Minimal MVP)

### 3.1 Users
- `id` (UUID / int)
- `phone_number` (unique)
- `display_name` (optional)
- `created_at`

### 3.2 Messages (Raw inbound)
- `id`
- `user_id`
- `text`
- `raw_payload` (JSONB)
- `created_at`

### 3.3 Expenses (Structured)
- `id`
- `user_id`
- `amount` (numeric)
- `currency` (e.g., ILS)
- `merchant` (text)
- `category` (enum/text)
- `occurred_at` (timestamp) — time of expense (defaults to message time)
- `source_message_id` (FK to messages)
- `created_at`

### (Optional later) Groups
If you want “group mode”:
- `groups` table
- `group_members`
- add `group_id` to expenses/messages

---

## 4. Message Lifecycle (End-to-End Flow)

### 4.1 Flow A – Recording an Expense

**Sequence**
1. User sends WhatsApp message: “אכלתי בBABIS והוצאתי 500”
2. WhatsApp → `POST /webhooks/whatsapp`
3. Webhook:
   - stores raw message in `messages`
   - enqueues `process_message(message_id)`
   - returns `200 OK` quickly
4. Worker pulls job:
   - loads message text from DB
   - runs intent detection (expense vs query)
   - calls LLM extraction (if expense)
   - validates output schema
   - inserts into `expenses`
5. Reply service sends confirmation message to WhatsApp:
   - “Expense recorded: ₪500, Restaurants, BABIS”

**Key properties**
- Webhook stays fast
- Worker is retryable
- DB has full audit trail (raw + structured)

---

### 4.2 Flow B – Analytics Question

Example: “כמה הוצאתי השבוע על מסעדות?”

**Sequence**
1. WhatsApp → Webhook
2. Webhook stores raw message + enqueues job
3. Worker:
   - detects intent = `analytics_query`
   - extracts filters:
     - timeframe = week
     - category = restaurant
     - scope = user
   - runs SQL aggregation
   - formats response
4. Sends WhatsApp reply:
   - “This week you spent ₪X on Restaurants”

---

## 5. API Endpoints (Backend)

### 5.1 Webhook
- `GET /webhooks/whatsapp/verify` (WhatsApp verification handshake)
- `POST /webhooks/whatsapp` (inbound events)

### 5.2 Health / Ops
- `GET /health` (liveness)
- `GET /ready` (readiness, checks DB/Redis)

### 5.3 Admin/Debug (no UI needed)
- `GET /expenses?user_id=&from=&to=&category=`
- `GET /analytics/weekly?user_id=`
- `GET /analytics/monthly?user_id=`
- `GET /analytics/top-spenders?from=&to=`
- `GET /messages?user_id=`

> These endpoints are optional but extremely useful for demos + debugging.

---

## 6. LLM Design (Strict + Reliable)

### 6.1 Expense Extraction Schema
LLM must output a strict JSON object like:

- `type`: `"expense"`
- `amount`: number
- `currency`: `"ILS"` (default if Hebrew + ₪)
- `merchant`: string | null
- `category`: enum string
- `occurred_at`: ISO datetime | null

### 6.2 Intent Classification Schema
LLM outputs:

- `type`: `"expense" | "analytics_query" | "unknown"`
- if `analytics_query`:
  - `timeframe`: `"week" | "month" | "custom" | "all_time"`
  - `category`: optional
  - `scope`: `"me" | "group" | "user"`
  - `target_user`: optional
  - `from`, `to`: optional

### 6.3 Why strict schema?
- Prevents “creative” outputs that break code
- Makes system testable and deterministic
- Makes interview explanation strong (“we validate LLM output”)

---

## 7. Error Handling & Retries (Production-like)

### 7.1 Webhook rules
- Always respond `200 OK` quickly once message is persisted and queued.
- Never block on LLM inside webhook.

### 7.2 Worker retries
- Transient errors (timeouts, rate limits): retry with backoff
- Permanent errors (invalid schema): store as “failed_parse” and reply with fallback message:
  - “I couldn’t understand this message. Try: ‘BABIS 500 restaurant’”

### 7.3 Idempotency
WhatsApp can re-send events.  
To avoid duplicates:
- store `whatsapp_message_id` (unique) on `messages`
- if already exists → ignore / update safely

---

## 8. Security & Configuration

- Environment variables:
  - `DATABASE_URL`
  - `REDIS_URL`
  - `WHATSAPP_VERIFY_TOKEN`
  - `WHATSAPP_ACCESS_TOKEN`
  - `WHATSAPP_PHONE_NUMBER_ID`
  - `LLM_API_KEY`
- Validate WhatsApp webhook verification token
- Never commit secrets
- Add basic rate limiting (optional)

---

## 9. Scaling Strategy (If load grows)

- Webhook service scales horizontally (multiple instances)
- Redis queue coordinates work
- Add more worker instances to process messages faster
- PostgreSQL can handle analytics; add indexes:
  - `expenses(user_id, occurred_at)`
  - `expenses(category, occurred_at)`
  - `messages(whatsapp_message_id)` unique

---

## 10. Repository Structure (Recommended)

backend/
- app/
  - api/                # FastAPI routes (webhook, admin)
  - models/             # SQLAlchemy models
  - schemas/            # Pydantic schemas
  - services/
    - whatsapp/         # send reply + helpers
    - analytics/        # SQL queries + formatting
    - router/           # intent routing (expense vs query)
    - storage/          # repositories/DB logic
  - llm/
    - prompts/          # prompt templates
    - client.py         # LLM client
    - extractors.py     # expense extraction / intent classification
  - workers/
    - consumer.py       # queue consumer
  - core/
    - config.py         # env settings
    - logging.py
    - exceptions.py
- tests/
- docs/

---

## 11. Deliverables for This Stage

Create the file:

- `docs/system-architecture.md` (this document)

You are done with Stage 2 when:
- The architecture diagram is agreed
- The message lifecycle is clear
- The LLM responsibilities are clearly scoped
- The endpoint list is agreed
