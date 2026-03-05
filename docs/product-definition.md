# SpendWise Chat – Product Definition

## 1. Project Overview

SpendWise Chat is a backend system that integrates with the WhatsApp API and allows users to track expenses through natural language messages.

Users can send messages such as:

"I ate at BABIS and spent 500"

The system processes incoming messages, extracts structured expense data using a Large Language Model (LLM), stores the data in a database, and generates analytics about spending behavior.

Users can also ask questions in natural language such as:

"How much did I spend this week?"

The system will respond automatically based on stored data.

The goal of this project is to demonstrate modern backend architecture combined with LLM-powered data extraction and natural language interaction.

---

# 2. Problem Statement

Tracking expenses usually requires opening dedicated finance applications and manually entering structured data.

This creates friction and discourages users from tracking their spending regularly.

SpendWise Chat removes this friction by allowing users to track expenses directly from WhatsApp using natural language messages.

This allows expense tracking to happen in a conversational and frictionless way.

---

# 3. Target Users

The system supports two main usage scenarios:

### Single User Mode

A single user tracks personal expenses.

Example:

User sends:

"I bought coffee for 20"

The system records the expense.

---

### Group Mode

Multiple users track expenses together.

Example scenarios:

* roommates sharing expenses
* friends during a trip
* shared apartment spending
* event budgets

Each expense is associated with the user who reported it.

The system can generate analytics across all users.

---

# 4. Core Features

## 4.1 WhatsApp Message Ingestion

The system receives messages from users through the WhatsApp Cloud API.

Messages are delivered to the backend through a webhook endpoint.

Example message:

"I spent 500 at BABIS"

---

## 4.2 LLM Expense Extraction

Incoming messages are processed by an LLM to extract structured data.

Example:

Input:

"I ate at BABIS and spent 500"

Output:

```json
{
  "amount": 500,
  "currency": "ILS",
  "merchant": "BABIS",
  "category": "restaurant"
}
```

The system automatically detects the category without requiring user confirmation.

Categories may include:

* restaurant
* groceries
* entertainment
* transportation
* coffee
* shopping
* utilities

---

## 4.3 Expense Storage

Extracted expenses are stored in a database.

Each expense record includes:

* user
* amount
* category
* merchant
* timestamp
* source message

---

## 4.4 Analytics Engine

The system generates spending analytics.

Examples include:

* total spending per user
* total spending per category
* weekly spending summary
* monthly spending summary
* top spending category
* highest spending user

These analytics are computed using SQL queries.

---

## 4.5 Natural Language Queries

Users can ask questions using natural language.

Examples:

"How much did I spend this week?"

"How much did we spend on restaurants?"

"Who spent the most this month?"

The system interprets the query and returns a structured response.

Example response:

"You spent ₪700 this week.

Restaurants: ₪500
Coffee: ₪80
Transportation: ₪120"

---

# 5. Example User Flows

## Flow 1 – Recording an Expense

User sends message:

"I spent 200 at the cinema"

System processing:

1. WhatsApp sends the message to the webhook
2. The backend stores the raw message
3. The message is sent to a worker
4. The worker calls the LLM extraction service
5. The extracted expense is stored in the database

System response:

"Expense recorded.

Category: Entertainment
Amount: ₪200"

---

## Flow 2 – Analytics Query

User sends message:

"How much did I spend this week?"

System processing:

1. Detect query intent
2. Run analytics query
3. Format response

System response:

"You spent ₪540 this week.

Restaurants: ₪320
Coffee: ₪40
Transportation: ₪180"

---

# 6. System Goals

The project aims to demonstrate the following engineering capabilities:

### Backend System Design

* API design
* webhook integrations
* asynchronous processing
* queue-based architectures

### AI / LLM Integration

* structured information extraction
* prompt design
* natural language query interpretation

### Data Engineering

* relational schema design
* SQL analytics
* data integrity

### Production-Style Development

* containerized infrastructure
* modular backend architecture
* clear documentation

---

# 7. Non-Goals

To keep the project focused, the following features are intentionally excluded:

* no mobile application
* no full UI dashboard
* no financial account integrations
* no payment processing
* no banking APIs

The system is focused on backend architecture and AI integration.

---

# 8. Key Technical Components

The system will use the following core components:

Backend Framework:
FastAPI

Database:
PostgreSQL

Queue / Background Processing:
Redis + worker processes

LLM Integration:
OpenAI API (or equivalent)

Infrastructure:
Docker and docker-compose

External Integration:
WhatsApp Cloud API

---

# 9. Success Criteria

The project will be considered successful when:

1. Users can send expense messages through WhatsApp.
2. The system extracts structured expense data using an LLM.
3. Expenses are stored in a relational database.
4. The system can generate spending analytics.
5. Users can ask questions in natural language and receive meaningful responses.

---

# 10. Future Improvements

Potential future improvements include:

* real-time dashboards
* expense editing
* category learning improvements
* automated weekly reports
* AI-powered spending insights
* group settlement calculations
