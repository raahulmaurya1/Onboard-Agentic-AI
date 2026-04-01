#  OnboardAI — Agentic Bank Onboarding & Risk Intelligence Engine

> **An autonomous, multi-agent AI decision engine that thinks, reasons, and acts to orchestrate secure bank account onboarding — powered by Gen AI, LangGraph, and a 3-Tier deterministic-cognitive risk pipeline.**

[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-State_Machine-FF6B35?style=flat-square)](https://langchain-ai.github.io/langgraph/)
[![Gemini](https://img.shields.io/badge/Google_Gemini-3.1_Flash-4285F4?style=flat-square&logo=google)](https://ai.google.dev/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-pgvector-4169E1?style=flat-square&logo=postgresql)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-Session_State-DC382D?style=flat-square&logo=redis)](https://redis.io/)
[![Celery](https://img.shields.io/badge/Celery-Async_Workers-37814A?style=flat-square)](https://docs.celeryq.dev/)
[![MinIO](https://img.shields.io/badge/MinIO-Document_Storage-C72C48?style=flat-square)](https://min.io/)
[![React](https://img.shields.io/badge/React-20232A?style=flat-square&logo=react&logoColor=61DAFB)](https://react.dev/)
[![JavaScript](https://img.shields.io/badge/JavaScript-F7DF1E?style=flat-square&logo=javascript&logoColor=black)](https://developer.mozilla.org/en-US/docs/Web/JavaScript)
[![TypeScript](https://img.shields.io/badge/TypeScript-3178C6?style=flat-square&logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Vite](https://img.shields.io/badge/Vite-646CFF?style=flat-square&logo=vite&logoColor=white)](https://vitejs.dev/)
[![TailwindCSS](https://img.shields.io/badge/Tailwind_CSS-38B2AC?style=flat-square&logo=tailwind-css&logoColor=white)](https://tailwindcss.com/)

---
## 🎥 Demo Video

[![OnboardAI Demo](https://github.com/raahulmaurya1/Onboard-Agentic-AI/blob/18eea35b968ead7f7187b9c3d103f973f366f5fd/Thumbnail.png)](https://youtu.be/OO37AeUx14Q)

## Table of Contents

- [What is this System?](#-what-is-this-system)
  - [The Core Distinction](#the-core-distinction)
  - [What "Agentic" means here](#what-agentic-means-here)
- [Core Architecture](#️-core-architecture)
  - [Component Roles](#component-roles)
- [Execution Flow (Agent Lifecycle)](#-execution-flow-agent-lifecycle)
  - [The 7-Step Onboarding Sequence](#the-7-step-onboarding-sequence)
- [Tool Selection Matrix](#tool-selection-matrix)
- [Agents in the System](#-agents-in-the-system)
  - [1. Decision Agent](#1--decision-agent--appagentsdecision_agentpy)
  - [2. Intent Agent](#2--intent-agent--appagentsintent_agentpy)
  - [3. Risk Agent](#3--risk-agent--appagentsrisk_agentpy)
  - [4. Memory Agent](#4--memory-agent--appagentsmemory_agentpy)
  - [5. Lifecycle Agent](#5--lifecycle-agent--appagentslifecycle_agentpy)
  - [6. Extraction Agent](#6--extraction-agent--appagentsextraction_agentpy)
  - [7. Validation Agent](#7--validation-agent--appagentsvalidation_agentpy)
  - [8. Finalization Agent](#8--finalization-agent--appagentsfinalization_agentpy)
  - [9. Entry Agent](#9--entry-agent--appagentsentry_agentpy)
- [Tooling System](#-tooling-system)
  - [Tool Registry](#tool-registry--decision_agentpy)
  - [How Tool Discovery Works](#how-tool-discovery-works)
  - [Fast-Path Bypasses (Pre-LLM)](#fast-path-bypasses-pre-llm)
- [Model Orchestration](#-model-orchestration)
  - [Models in Use](#models-in-use)
  - [Model Selection Strategy](#model-selection-strategy)
  - [Async Coordination](#async-coordination)
- [Reasoning Strategy](#-reasoning-strategy)
  - [Planning vs. Reactive Execution](#planning-vs-reactive-execution)
  - [Decision Logic Chain](#decision-logic-chain)
  - [State-Aware Routing Rules](#state-aware-routing-rules)
- [LangGraph Framework Integration](#-langgraph-framework-integration)
  - [State Schema](#state-schema--appdbschemaspy)
  - [Graph Topology](#graph-topology)
  - [Risk Engine Integration in LangGraph](#risk-engine-integration-in-langgraph)
- [Project Structure](#-project-structure)
- [Database Architecture](#️-database-architecture)
  - [Class diagram](#class-diagram)
  - [Layer Model](#layer-model)
  - [Key Design Decisions](#key-design-decisions)
- [Setup & Installation](#-setup--installation)
  - [Prerequisites](#prerequisites)
- [Technology Stack](#technology-stack)
  - [1. Clone Repository](#1-clone-repository)
  - [2. Create Virtual Environment](#2-create-virtual-environment)
  - [3. Install Dependencies](#3-install-dependencies)
  - [4. Configure Environment Variables](#4-configure-environment-variables)
  - [5. Initialize Database](#5-initialize-database)
  - [6. Start Services](#6-start-services)
- [Usage & API Endpoints](#️-usage--api-endpoints)
  - [Core Agent Endpoint](#core-agent-endpoint)
  - [Valid ui_action Values](#valid-ui_action-values)
  - [Other Key Endpoints](#other-key-endpoints)
- [Example Execution Trace](#-example-execution-trace)
- [Architecture Diagrams](#-architecture-diagrams)
  - [1. High-Level System Architecture](#1-high-level-system-architecture)
  - [2. Agent Workflow Sequence Diagram](#2-agent-workflow-sequence-diagram)
  - [3. Authentication Sequence Diagram](#3-authentication-sequence-diagram)
  - [4. Sequence Diagram - Account open](#4-sequence-diagram---account-openretail-sme-and-digital)
  - [5. Parent Lifecycle System](#4-parent-lifecycle-system--re-kyc--reactivation)
- [Design Principles](#️-design-principles)
  - [1. Modularity](#1--modularity)
  - [2. Fail-Open Resilience](#2--fail-open-resilience)
  - [3. Privacy by Design](#3--privacy-by-design)
  - [4. Scalability](#4--scalability)
  - [5. Observability](#5--observability)
  - [6. Open-Closed Principle](#6--open-closed-principle)
- [Future Improvements](#-future-improvements)
- [License](#-license)

## 🧠 What is this System?

**OnboardAI is not an API wrapper. It is a reasoning machine.**

This system is a fully autonomous **Agentic AI Decision Engine** built for regulated banking environments. Unlike traditional rule-based onboarding systems or static ML pipelines, OnboardAI deploys a constellation of specialized AI agents that collaborate, reason, and execute in real-time to guide a customer from first contact through to a verified, risk-scored account decision — with zero hardcoded flow logic.

### The Core Distinction

| Traditional System | OnboardAI Agentic System |
|---|---|
| Hardcoded if/else routing | Gemini LLM selects the next action |
| Static rule engine | 3-Tier deterministic + cognitive risk pipeline |
| Synchronous monolith | Async agents + Celery background workers |
| No memory | pgvector semantic memory + Redis hot state |
| Manual review always | Autonomous APPROVE / REVIEW / REJECT decisions |

### What "Agentic" means here

- **Autonomous Decision-Making** — The `DecisionAgent` (powered by Gemini) independently determines the next step in the onboarding flow at every interaction without any hardcoded branching
- **Multi-Step Reasoning** — Each message triggers a Gemini reasoning loop: understand context → consult state → select tool → act → return structured UI instruction
- **Tool/Agent Orchestration** — 11 tools are registered as callable functions; Gemini's native function-calling API discovers and invokes them dynamically
- **Dynamic Execution Pipeline** — LangGraph compiles a state machine that routes applicants through intent classification → document extraction → risk evaluation → final decision, with conditional edges driven by risk engine output

---

## ⚙️ Core Architecture


<img src="https://github.com/raahulmaurya1/Onboard-Agentic-AI/blob/d0119d9381a2f4f8c0199b3817cb30b80277b29a/architecture_svg.svg" alt="My Image" style="width: 100%; height: auto; max-width: 500px;">

*Overview*

```
┌──────────────────────────────────────────────────────────────────────────────┐
│                        ONBOARDAI — SYSTEM ARCHITECTURE                       │
├───────────────────┬──────────────────────┬───────────────────────────────────┤
│   FRONTEND LAYER  │   ORCHESTRATION      │   INTELLIGENCE LAYER              │
│                   │                      │                                   │
│  React / TSX UI   │  DecisionAgent       │  Google Gemini 3.1 Flash Lite     │
│  Admin Dashboard  │  (Master Brain)      │  text-embedding-004               │
│  RiskReviewPage   │  LangGraph FSM       │  Gemini AML Analyst (Tier 3)      │
└───────────────────┴──────────────────────┴───────────────────────────────────┘
          │                   │                          │
          ▼                   ▼                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                           AGENT LAYER                                       │
│                                                                             │
│  IntentAgent  │  RiskAgent    │  MemoryAgent  │  LifecycleAgent             │
│  EntryAgent   │  ExtractionAgent │ ValidationAgent │ FinalizationAgent      │
└─────────────────────────────────────────────────────────────────────────────┘
          │                   │                          │
          ▼                   ▼                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         EXECUTION LAYER                                     │
│                                                                             │
│  FastAPI (async)  │  Celery Workers  │  OTP Service  │  Face Verification   │
│  MinIO Storage    │  GeoIP Service   │  OCR Engine   │  Signature Matcher   │
└─────────────────────────────────────────────────────────────────────────────┘
          │                   │                          │
          ▼                   ▼                          ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                         PERSISTENCE LAYER                                   │
│                                                                             │
│  PostgreSQL + pgvector  │  Redis (hot state)  │  MinIO (documents)          │
│  user_initial / sessions / user_documents / risk_evaluations                │
│  agent_context (768-dim) / additional_info                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Component Roles

| Component | Role | Technology |
|---|---|---|
| **DecisionAgent (Core Brain)** | Master LLM orchestrator; reasons about state and selects tools | Google Gemini + Function Calling |
| **Tool Registry** | 11 declarative Python function schemas exposed to Gemini | Native Gemini function-calling API |
| **LangGraph FSM** | Compiled state machine for deterministic flow control and risk routing | LangGraph `StateGraph` |
| **Risk Engine** | 3-tier pipeline: hard-kill → weighted matrix → Gemini AML | Custom Python + Gemini |
| **Memory Layer** | Semantic search over historical edge cases | pgvector (768-dim Gemini embeddings) |
| **Hot State** | Per-session volatile state during active onboarding | Redis (30-min TTL) |
| **Document Store** | OCR-processed KYC document artifacts | MinIO S3-compatible |
| **Background Workers** | Async document extraction and processing | Celery + Redis broker |

---

## 🔄 Execution Flow (Agent Lifecycle)

Every user message passes through an 8-phase reasoning loop:

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         AGENT LIFECYCLE — PER REQUEST                       │
└─────────────────────────────────────────────────────────────────────────────┘

 Phase 1: INPUT RECEIVED
   └─ HTTP POST /api/v1/decision  →  message + session_ulid + current_state

 Phase 2: FAST-PATH INTERCEPT (Pre-LLM)
   ├─ source == "lifecycle_init"   →  LifecycleOrchestrator.lookup_account()
   ├─ source == "kyc_upload"       →  Celery task fire-and-forget → RENDER_PROCESSING
   ├─ source == "poll"             →  Redis extraction result check
   └─ source == "face_poll"        →  Redis face verification result check

 Phase 3: STATE INITIALIZATION
   ├─ PostgreSQL: Load UserInitial record (status, face_verified, account_type)
   ├─ Redis: Check pending_auth:{session_ulid} for volatile auth state
   └─ Build: Dynamic context dict (isAuthenticated, phoneVerified, kycUploaded, etc.)

 Phase 4: GEMINI REASONING LOOP
   ├─ System Prompt: Strict 7-step orchestration rules + JSON schema
   ├─ Context: Serialized current state injected into prompt
   └─ Gemini reasons: What step are we at? What tool is needed?

 Phase 5: TOOL SELECTION (Function Calling)
   └─ Gemini emits a FunctionCall → tool name + arguments from the Tool Registry

 Phase 6: TOOL EXECUTION (Python Backend)
   └─ handle_tool_call() dispatches to the correct async Python function

 Phase 7: OBSERVATION + RISK HOOK
   ├─ Tool result returned to Gemini
   └─ After execute_hybrid_freeze_tool: _apply_risk_routing() runs 3-tier risk engine

 Phase 8: FINAL RESPONSE
   └─ Structured JSON: { ui_action, agent_message, session_ulid, extracted_data }
      → Frontend renders the correct screen
```

### The 7-Step Onboarding Sequence

```
Step 1: Phone OTP    →  trigger_phone_otp() + submit_phone_otp()
Step 2: Email OTP    →  trigger_email_otp() + submit_email_otp() → register_user()
Step 3: Intent       →  classify_user_intent() → retail_savings | sme_current | digital_only
Step 4: KYC Upload   →  request_document_upload() → MinIO storage
Step 5: Extraction   →  extract_and_review_tool() → Celery OCR → RENDER_DATA_REVIEW
Step 6: Face Verify  →  trigger_face_verification_tool() → DeepFace + MediaPipe liveness
Step 7: Final        →  execute_hybrid_freeze_tool() → 3-Tier Risk → APPROVE/REVIEW/REJECT
```


---
## Tool Selection Matrix


<img src="https://github.com/raahulmaurya1/Onboard-Agentic-AI/blob/bc44a0ac198539d84cd58e325f4245516b4b298c/Tool%20Selection%20Matrix.png" alt="Tool Selection Matrix" style="width: 100%; height: auto; max-width: 500px;">
---
---

## 🧩 Agents in the System

### 1. 🧠 Decision Agent — `app/agents/decision_agent.py`

The **Master Orchestrator**. The only agent that directly interfaces with the user.

| Attribute | Detail |
|---|---|
| **Purpose** | Gemini-powered LLM brain; owns the 7-step onboarding sequence |
| **Model** | `gemini-3.1-flash-lite-preview` with native function-calling |
| **Input** | `message: str`, `session_ulid: str`, `current_state: dict`, `final_data: dict` |
| **Output** | `{ ui_action, agent_message, session_ulid, data_required, extracted_data }` |
| **Invoked by** | Every API call to `/api/v1/decision` |
| **Interacts with** | All other agents via tool dispatch; Risk Engine via `_apply_risk_routing()` |
| **Special Logic** | Fast-path interceptors bypass LLM for deterministic signals (KYC upload, polling) |

**System Prompt Enforces:**
- Strict 7-step sequential flow; no steps can be skipped
- 9 valid `ui_action` strings the frontend explicitly renders
- Intent must be confirmed before document upload is triggered
- Fail-open design: any risk engine failure defaults to PROCEED

---

### 2. 🎯 Intent Agent — `app/agents/intent_agent.py`

Classifies the user's natural language request into one of 5 account categories.

| Attribute | Detail |
|---|---|
| **Purpose** | NLU classifier; maps free-form text to a strongly-typed `IntentCategory` enum |
| **Model** | Gemini with `response_mime_type="application/json"` |
| **Input** | `user_message: str` |
| **Output** | `IntentClassificationResult(intent, confidence, reasoning)` |
| **Optimization** | Keyword heuristics run first (zero-latency); LLM only invoked for ambiguous input |

**Supported Intents:**

```python
class IntentCategory(str, Enum):
    RETAIL_SAVINGS = "retail_savings"   # Standard personal savings
    DIGITAL_ONLY   = "digital_only"    # Zero-balance instant account
    SME_CURRENT    = "sme_current"     # Business current account
    RE_KYC         = "re_kyc"          # Existing customer KYC update
    REACTIVATION   = "reactivation"    # Dormant account reactivation
    UNKNOWN        = "unknown"          # Fallback / greeting
```

---

### 3. ⚠️ Risk Agent — `app/agents/risk_agent.py`

The **3-Tier Deterministic-Cognitive Risk Pipeline**. The most sophisticated component.

| Attribute | Detail |
|---|---|
| **Purpose** | Evaluates fraud, AML, and identity risk across 3 progressive tiers |
| **Input** | `user_record`, `telemetry_data`, `additional_info_record` |
| **Output** | `{ category: AUTO_APPROVE|MANUAL_REVIEW|REJECT, score: int, flags: list }` |
| **Privacy** | PII is regex-redacted before any log parsing; only bucketed features written to DB |
| **Storage** | Async fire-and-forget to `risk_evaluations` table with 128-dim feature vector |

**Tier Architecture:**
<img src="https://github.com/raahulmaurya1/Onboard-Agentic-AI/blob/ec2ee0084e800511a59289eac4bb74a0808b7325/risk_score1.jpg" alt="My Image" style="width: 100%; height: auto; max-width: 500px;">


---

### 4. 🧬 Memory Agent — `app/agents/memory_agent.py`

Provides **semantic long-term memory** using pgvector embeddings.

| Attribute | Detail |
|---|---|
| **Purpose** | Store and retrieve historical edge cases for consistent risk decisions |
| **Model** | `text-embedding-004` (768-dimensional Gemini embeddings) |
| **Storage** | `agent_context` table with IVFFLAT cosine distance index |
| **Search** | Nearest-neighbor cosine similarity via `search_similar_cases` tool |

---

### 5. 🔁 Lifecycle Agent — `app/agents/lifecycle_agent.py`

Implements the **Strategy Pattern** for Re-KYC and Account Reactivation flows.

| Attribute | Detail |
|---|---|
| **Purpose** | Reuses the 7-step pipeline for existing customers without creating new ULIDs |
| **Input** | `account_id: str`, `intent: "re_kyc" | "reactivation"` |
| **Strategy** | Force-resets flow state; existing `status` field is ignored via Redis flag |
| **Data Guard** | `upsert_user_data()` performs SQL UPDATE only — never INSERT, null-filtered |
| **Flag System** | `lifecycle_flow:{session_ulid}` Redis key (4-hour TTL) controls routing |

---

### 6. 📄 Extraction Agent — `app/agents/extraction_agent.py`

Runs OCR on uploaded KYC documents via Celery background workers.

| Attribute | Detail |
|---|---|
| **Purpose** | Extract structured fields from PAN, Aadhaar, GST certificates |
| **Workers** | `process_documents_async` (retail) / `process_sme_documents_async` (SME) |
| **Output** | Combined data written to Redis temp store; polled by frontend |
| **Library** | PyMuPDF + Pytesseract + Pillow |

---

### 7. ✅ Validation Agent — `app/agents/validation_agent.py`

Cross-validates extracted OCR data for consistency and completeness.

---

### 8. 🔒 Finalization Agent — `app/agents/finalization_agent.py`

Runs **Hybrid Freeze** — merges verified data into the user profile and triggers the risk hook.

---

### 9. 👤 Entry Agent — `app/agents/entry_agent.py`

Handles initial user registration in PostgreSQL after dual OTP verification.

---

## 🛠 Tooling System

The Decision Agent (Gemini) operates exclusively through a **declarative Tool Registry** of 11 Python functions. Gemini never calls these functions directly — it emits a `FunctionCall` object and the Python dispatcher executes them.

### Tool Registry — `decision_agent.py`

```python
tool_registry_schemas = [
    trigger_phone_otp,           # Send SMS OTP to begin onboarding
    trigger_email_otp,           # Send verification email
    submit_phone_otp,            # Verify 6-digit SMS OTP → generate session_ulid
    submit_email_otp,            # Verify email OTP → register_user()
    classify_user_intent,        # NLU: route to IntentAgent → IntentCategory
    request_document_upload,     # Signal React UI to open document upload drawer
    extract_and_review_tool,     # Fire Celery OCR task → RENDER_PROCESSING
    trigger_face_verification_tool,  # Signal React UI to open face capture
    execute_hybrid_freeze_tool,  # Finalize profile → trigger 3-tier risk engine
    escalate_to_human_tool,      # Push session to ops manual review queue
    search_similar_cases,        # pgvector semantic search in agent_context
]
```

### How Tool Discovery Works

```
1. Tool schemas passed to Gemini as function declarations
2. Gemini reasons about current state and selects the appropriate tool
3. Gemini emits: FunctionCall(name="trigger_phone_otp", args={"phone": "9876543210"})
4. handle_tool_call() dispatches to Python implementation
5. Result returned as FunctionResponse to Gemini
6. Gemini generates final structured JSON response
```

### Fast-Path Bypasses (Pre-LLM)

Certain high-frequency, deterministic signals bypass the LLM entirely to reduce latency:

| Signal | Fast-Path Action |
|---|---|
| `source == "kyc_upload"` | Dispatch Celery task → return `RENDER_PROCESSING` immediately |
| `source == "poll"` | Check Redis for extraction result → return data or keep polling |
| `source == "face_poll"` | Check Redis for face verification result |
| `source == "lifecycle_init"` | Invoke LifecycleOrchestrator → skip LLM entirely |

---

## 🤖 Model Orchestration

### Models in Use

| Model | Provider | Purpose | Parameters |
|---|---|---|---|
| `gemini-3.1-flash-lite-preview` | Google AI | Master orchestrator, intent classification | Function-calling enabled |
| `gemini-3.1-flash-lite-preview` | Google AI | Tier 3 AML risk analyst | JSON response mode, 15s timeout |
| `text-embedding-004` | Google AI | 768-dim semantic embeddings for memory | `retrieval_document` task type |
| DeepFace (VGG-Face) | Open Source | Face similarity scoring | Cosine distance |
| MediaPipe Face Mesh | Google | Liveness / blink detection | 468 facial landmarks |

### Model Selection Strategy

- **DecisionAgent**: Always uses `gemini-3.1-flash-lite-preview` — balances speed + intelligence for real-time chat
- **RiskAgent Tier 3**: Same model, but invoked with a domain-specific AML prompt and hard 15-second timeout
- **MemoryAgent**: `text-embedding-004` exclusively — purpose-built for retrieval tasks
- **Fallback Design**: Every Gemini call wraps in `try/except`; failures degrade gracefully (fail-open)
- **Digital-Only Bypass**: Tier 3 Gemini call is skipped entirely for `digital_only` accounts — only deterministic tiers run

### Async Coordination

```python
# Log sources read concurrently before risk evaluation
gunicorn_data, celery_data = await asyncio.gather(
    read_gunicorn_log_async(),
    read_celery_log_async(),
)

# Risk storage is fire-and-forget — never blocks the response
asyncio.create_task(store_risk_data(...))

# Face verification with 15s Gemini timeout
raw_text = await asyncio.wait_for(
    asyncio.to_thread(_call_gemini), timeout=15.0
)
```

---

## 🧠 Reasoning Strategy

### Planning vs. Reactive Execution

OnboardAI uses a **hybrid reasoning model**:

**Reactive (LLM Layer):** The DecisionAgent responds to each message reactively, using current state as context. There is no pre-planned multi-step trajectory — each tool call is decided in the moment based on what step the state indicates.

**Planned (LangGraph FSM):** The `onboarding_flow.py` LangGraph state machine represents a compiled execution plan with conditional routing edges. This provides deterministic guarantees that the risk engine always runs after extraction.

### Decision Logic Chain

```
User Message → State Hydrated (DB + Redis)
      ↓
System Prompt: "You are at Step X. These tools are available."
      ↓
Gemini Reasoning: "State shows phoneVerified=True, emailVerified=True,
                   intent=null → must ask for intent before KYC"
      ↓
Tool Selected: classify_user_intent(user_message="I want a business account")
      ↓
Tool Result: { intent: "sme_current", confidence: 0.97 }
      ↓
Intent cached in Redis: session_intent:{session_ulid} = "sme_current"
      ↓
Response: { ui_action: "RENDER_KYC_UPLOAD", agent_message: "...upload GST + PAN + Aadhaar" }
```

### State-Aware Routing Rules

The system prompt encodes strict rules that prevent Gemini from hallucinating shortcuts:

- Intent field must be non-null before `RENDER_KYC_UPLOAD` is ever returned  
- `RENDER_FACE_VERIFICATION` only after data review is confirmed  
- `RENDER_AUTO_APPROVE` only after successful `execute_hybrid_freeze_tool`  
- All off-topic queries are explicitly refused

---

## 🔗 LangGraph Framework Integration

LangGraph is used as the **compiled state machine** for the onboarding workflow.

### State Schema — `app/db/schemas.py`

```python
class OnboardingState(BaseModel):
    session_ulid: Optional[str]
    intent: Optional[str]
    documents_uploaded: bool = False
    status: Optional[str]     # draft → KYC_UPLOADED → FACE_VERIFIED → approved/rejected
    risk_score: Optional[float]
    current_step: Optional[str]
```

### Graph Topology

```
START
  │
  ├─[no intent]──────────→ conversational_node → intent_classification → END
  │
  ├─[intent, no docs]───→ request_document_upload → trigger_extraction → evaluate_risk
  │
  └─[intent + docs]─────→ trigger_extraction → evaluate_risk
                                                      │
                                          ┌───────────┴───────────┐
                                          ▼           ▼           ▼
                                     auto_approve  reject  human_review
                                          │           │           │
                                          └───────────┴───────────┘
                                                      │
                                                     END
```

### Risk Engine Integration in LangGraph

The `evaluate_risk` node runs `process_onboarding()` from `app/services/risk_engine.py`, which internally delegates to `evaluate_full_risk()` from the RiskAgent. Since LangGraph nodes are synchronous, the async call is bridged using `concurrent.futures.ThreadPoolExecutor` when inside FastAPI's running event loop.

---

## 📦 Project Structure

```
backend_risk_score/
│
├── app/                              # Main application package
│   ├── main.py                       # FastAPI app factory + router registration
│   ├── config.py                     # Pydantic Settings (env var loading)
│   │
│   ├── agents/                       # 🧠 Core AI Decision Engine
│   │   ├── decision_agent.py         # Master Orchestrator (Gemini + Tool Registry)
│   │   ├── intent_agent.py           # NLU intent classifier
│   │   ├── risk_agent.py             # 3-Tier risk evaluation engine
│   │   ├── memory_agent.py           # pgvector semantic memory
│   │   ├── lifecycle_agent.py        # Re-KYC / Reactivation strategy
│   │   ├── extraction_agent.py       # OCR document extraction logic
│   │   ├── validation_agent.py       # Cross-document validation
│   │   ├── finalization_agent.py     # Hybrid freeze + profile commitment
│   │   ├── entry_agent.py            # User registration handler
│   │   └── rule_book.json            # Static risk rulebook config
│   │
│   ├── orchestration/
│   │   └── onboarding_flow.py        # LangGraph StateGraph (compiled FSM)
│   │
│   ├── api/                          # FastAPI route handlers
│   │   ├── auth_routes.py            # OTP send/verify endpoints
│   │   ├── decision_routes.py        # /api/v1/decision (main agent entry)
│   │   ├── onboarding_routes.py      # KYC upload, data confirmation
│   │   ├── face_routes.py            # Face verification submission
│   │   ├── review_routes.py          # Data review and editing
│   │   ├── ops_routes.py             # Ops maker/checker endpoints
│   │   └── risk_review_routes.py     # Admin risk dashboard APIs
│   │
│   ├── services/                     # Backend execution services
│   │   ├── otp_service.py            # SMS + email OTP dispatch and verification
│   │   ├── risk_engine.py            # Risk engine orchestrator (wraps risk_agent)
│   │   ├── gemini_client.py          # Singleton Gemini model client
│   │   ├── additional_info_service.py # Form schema generation per account type
│   │   ├── geoip_service.py          # IP geolocation resolution
│   │   ├── file_detection.py         # Magika-powered file type detection
│   │   └── face_verification/
│   │       ├── face_service.py       # DeepFace similarity scoring
│   │       ├── liveness_service.py   # MediaPipe blink/liveness detection
│   │       └── video_utils.py        # Video frame extraction utilities
│   │
│   ├── db/                           # Data access layer
│   │   ├── models/                   # SQLAlchemy ORM models
│   │   │   ├── user.py               # UserInitial, AdditionalInfo
│   │   │   ├── document.py           # UserDocument, Sessions
│   │   │   └── agent.py              # AgentContext (768-dim vector)
│   │   ├── vector_store.py           # pgvector risk_evaluations persistence
│   │   ├── schemas.py                # Pydantic schemas + OnboardingState
│   │   └── redis_client.py           # Redis extraction temp store helpers
│   │
│   ├── workers/                      # Celery async task workers
│   │   ├── celery_app.py             # Celery app factory (Redis broker)
│   │   └── tasks/
│   │       └── extraction.py         # process_documents_async / process_sme_documents_async
│   │
│   ├── storage/
│   │   ├── minio.py                  # MinIO S3 client (document upload/download)
│   │   └── redis.py                  # Redis async client singleton
│   │
│   ├── middleware/
│   │   └── prefix_validation.py      # Request validation middleware
│   │
│   └── utils/                        # Shared utility functions
│
├── databases/
│   └── README_DATABASE.md            # Full database schema documentation
│
├── frontend_admin/                   # React Admin Dashboard (Vite + TypeScript)
│   └── src/
│       ├── pages/RiskReviewPage.tsx  # Human review queue UI
│       └── components/ui.tsx         # Shared UI components
│
├── migrations/                       # Alembic database migrations
├── alembic/                          # Alembic migration scripts
├── docker/                           # Docker configuration
├── scripts/                          # Utility scripts
├── requirements.txt                  # Python dependencies
├── alembic.ini                       # Alembic configuration
└── .env                              # Environment variables (not committed)
```

---

## 🗄️ Database Architecture

The system uses **PostgreSQL with pgvector** for hybrid relational + vector storage.


### Class diagram
<img src="https://github.com/raahulmaurya1/Onboard-Agentic-AI/blob/597486f6f0408da4dff8aadc5120e72f8e13de19/class_doagram.png" alt="class daigram" style="width: 100%; height: auto; max-width: 500px;">

### Layer Model

```
LAYER 1 — AUTH & SESSION
  • user_initial    → Core user records (ULID primary key)
  • sessions        → 30-minute TTL sessions

LAYER 2 — DOCUMENT & EXTRACTION
  • user_documents  → OCR results + MinIO URLs (PENDING → EXTRACTED → VERIFIED)
  • additional_info → Form data (industry_nic, turnover, PEP status)

LAYER 3 — RISK & VECTOR INTELLIGENCE
  • risk_evaluations  → ML feature store (128-dim vector, bucketed PII-free data)
  • agent_context     → Semantic memory (768-dim Gemini embeddings, IVFFLAT index)
```

### Key Design Decisions

| Decision | Rationale |
|---|---|
| ULID primary keys | Time-sortable, URL-safe, collision-free |
| JSONB for `verified_data` | Flexible schema for evolving OCR output |
| Anonymized `risk_evaluations` | Privacy compliance — age buckets, NIC codes, no raw PII |
| Dual vector tables | 128-dim for ML similarity, 768-dim for semantic recall |
| Async fire-and-forget storage | Risk data write never blocks the onboarding response |

---

## ⚡ Setup & Installation

### Prerequisites

- Python 3.11+
- PostgreSQL 15+ with `pgvector` extension
- Redis 7+
- MinIO (or any S3-compatible store)
- Google AI API key (Gemini)
- Tesseract OCR installed on the host

## Technology Stack

| Layer | Technology | Version |
| :--- | :--- | :--- |
| **API Framework** | FastAPI + Uvicorn / Gunicorn | Latest stable |
| **Agent Orchestration** | LangGraph | Latest stable |
| **Primary Database** | PostgreSQL + AsyncPG | 12+ |
| **Vector Search** | pgvector | Latest stable |
| **Cache + Broker** | Redis | Latest stable |
| **Task Queue** | Celery | Latest stable |
| **Object Storage** | MinIO (S3-compatible) | Latest stable |
| **LLM + Vision** | Google Gemini 2.0 Flash Lite | Current |
| **Embeddings** | Google text-embedding-004 | Current |
| **Face Recognition** | DeepFace + OpenFace | Latest stable |
| **Eye Detection** | MediaPipe | Latest stable |
| **OCR** | Tesseract | 5.x |
| **PDF Processing** | PyMuPDF (fitz) | Latest stable |
| **Image Processing** | Pillow (PIL) | Latest stable |
| **File Detection** | Magika | Latest stable |
| **String Matching** | RapidFuzz | Latest stable |
| **Data Validation** | Pydantic | v2 |
| **Database Migrations** | Alembic | Latest stable |
| **Unique Identifiers** | Python-ULID | Latest stable |

### 1. Clone Repository

```bash
git clone https://github.com/your-org/onboardai-backend.git
cd onboardai-backend
```

### 2. Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux / macOS
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Create a `.env` file in the project root:

```env
# Application
APP_ENV=development
SECRET_KEY=your-secret-key-here

# Database
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/onboardai

# Redis
REDIS_URL=redis://localhost:6379/0

# MinIO
MINIO_ENDPOINT=localhost:9000
MINIO_ACCESS_KEY=minioadmin
MINIO_SECRET_KEY=minioadmin
MINIO_BUCKET=kyc-documents

# Google AI
GEMINI_API_KEY=your-gemini-api-key

# OTP (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASS=your-app-password

# Log paths (for risk engine telemetry parsing)
GUNICORN_LOG_PATH=/var/log/gunicorn/access.log
CELERY_LOG_PATH=/var/log/celery/worker.log
```

### 5. Initialize Database

```bash
# Enable pgvector extension in PostgreSQL
psql -U postgres -c "CREATE EXTENSION IF NOT EXISTS vector;"
psql -U postgres -c "CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\";"

# Run Alembic migrations
alembic upgrade head
```

### 6. Start Services

```bash
# Terminal 1: FastAPI backend
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# Terminal 2: Celery worker (document extraction)
celery -A app.workers.celery_app worker --loglevel=info --concurrency=4

# Terminal 3: Admin dashboard (React)
cd frontend_admin && npm install && npm run dev
```

---

## ▶️ Usage & API Endpoints

### Core Agent Endpoint

```
POST /api/v1/decision
Content-Type: application/json

{
  "message": "I want to open a savings account",
  "session_ulid": "01ARZNDK...",       // Optional on first call
  "current_state": {},
  "source": null
}

Response:
{
  "ui_action": "RENDER_PHONE_AUTH",
  "agent_message": "Welcome! To begin, please enter your phone number.",
  "session_ulid": "01ARZNDK...",
  "data_required": ["phone"],
  "extracted_data": {}
}
```

### Valid `ui_action` Values

| ui_action | Triggered When |
|---|---|
| `RENDER_CHAT` | General conversation / intent unknown |
| `RENDER_PHONE_AUTH` | Phone OTP collection |
| `RENDER_EMAIL_AUTH` | Email OTP collection |
| `RENDER_KYC_UPLOAD` | Document upload screen |
| `RENDER_PROCESSING` | Async background task running |
| `RENDER_DATA_REVIEW` | OCR data extracted, user reviews |
| `RENDER_FACE_VERIFICATION` | Liveness + selfie capture |
| `RENDER_ADDITIONAL_INFO_FORM` | Post-face form (occupation, PEP, etc.) |
| `RENDER_AUTO_APPROVE` | Risk score < 40 — account approved |
| `RENDER_HUMAN_REVIEW` | Risk score 40–79 — ops review queue |
| `RENDER_ERROR` | Recoverable error screen |

### Other Key Endpoints

```
POST   /api/v1/face/verify          # Submit liveness video for verification
POST   /api/v1/onboarding/upload    # Upload KYC documents to MinIO
GET    /api/v1/risk-review          # Admin: list pending human review cases
POST   /api/v1/ops/approve/{id}     # Ops: approve a MANUAL_REVIEW application
POST   /api/v1/ops/reject/{id}      # Ops: reject an application
GET    /api/v1/review/{session_id}  # Fetch extracted data for review
```

---

## 🔍 Example Execution Trace

**Scenario:** SME business owner opening a Current Account

```
USER: "I want to open a business account for my trading firm"

─── Phase 1: Fast-Path Check ──────────────────────────────────────────────────
  ✗ No special source flag → proceed to full LLM loop

─── Phase 2: State Hydration ──────────────────────────────────────────────────
  DB: UserInitial not found (new session)
  Redis: No pending_auth key
  State: { isAuthenticated: false, phoneVerified: false, intent: null }

─── Phase 3: Gemini Reasoning ─────────────────────────────────────────────────
  "State: unauthenticated. Step 1 requires phone OTP. User message is irrelevant
   to current step. Must collect phone first."

  FunctionCall: trigger_phone_otp(phone=[not yet collected])
  → Actually returns RENDER_PHONE_AUTH to collect phone first

─── After Phone ───────────────────────────────────────────────────────────────
  Tool: submit_phone_otp("9876543210", "482917")
  Result: { session_ulid: "01ARZ3NDEK..." }
  Response: RENDER_EMAIL_AUTH

─── After Email ───────────────────────────────────────────────────────────────
  Tool: submit_email_otp("839221")
  → entry_agent.register_user() creates DB record
  → Redis pending_auth cleared
  Response: RENDER_CHAT (ask for account type)

─── Intent Classification ─────────────────────────────────────────────────────
  Keyword match: "business" → SME_CURRENT (confidence: 0.90)
  Redis: session_intent:{ulid} = "sme_current"
  Response: RENDER_KYC_UPLOAD (Aadhaar + PAN + GST required)

─── Document Upload ───────────────────────────────────────────────────────────
  Fast-path: source == "kyc_upload"
  Celery: process_sme_documents_async.delay(session_ulid, [url1, url2, url3])
  Response: RENDER_PROCESSING (immediate, no LLM call)

─── Extraction Poll ───────────────────────────────────────────────────────────
  Redis: temp_extraction:{ulid} found with validated combined_data
  DB Sync: user.name, pan_id, aadhar_id, gst_data committed to PostgreSQL
  Response: RENDER_DATA_REVIEW ({ name, dob, address, pan_id, gst_data })

─── Face Verification ─────────────────────────────────────────────────────────
  Video submitted → DeepFace (similarity: 96.2%) + MediaPipe (blinks: 3)
  Redis: face_verification:{ulid} = { status: success, overall_verdict: true }
  Response: RENDER_ADDITIONAL_INFO_FORM (SME business details)

─── Final Risk Evaluation ─────────────────────────────────────────────────────
  execute_hybrid_freeze_tool() → finalization_agent.execute_hybrid_freeze()
  
  _apply_risk_routing():
    Tier 1: No hard kills (face=96.2%, blinks=3, liveness=97.8%)
    Tier 2: matrix_score = 15 (face 90-99% range, minor penalty)
    Tier 3: Gemini AML → industry_nic=51001, turnover=50L
             → { additional_risk: 5, aml_flags: [] }
    Total: 20 → AUTO_APPROVE ✅
    
  asyncio.create_task(store_risk_data(...))  # Fire-and-forget to risk_evaluations
  Response: RENDER_AUTO_APPROVE 🎉
```

---

## 📊 Architecture Diagrams

### 1. High-Level System Architecture

<img src="https://github.com/raahulmaurya1/Onboard-Agentic-AI/blob/ec2ee0084e800511a59289eac4bb74a0808b7325/High-Level%20System%20Architecture.jpg" alt="High-Level System Architecture" style="width: 100%; height: auto; max-width: 500px;">

---

### 2. Agent Workflow Sequence Diagram

<img src="https://github.com/raahulmaurya1/Onboard-Agentic-AI/blob/ec2ee0084e800511a59289eac4bb74a0808b7325/Agent%20Workflow%20Sequence%20Diagram.jpg" alt="Agent Workflow Sequence Diagram" style="width: 100%; height: auto; max-width: 500px;">
---

### 3. Authentication Sequence Diagram

<img src="https://github.com/raahulmaurya1/Onboard-Agentic-AI/blob/2014e9e0eb108d852fe384d4015ac669b840c425/auth.svg" alt="Authencation" style="width: 100%; height: auto; max-width: 500px;">

---

### 4. Sequence Diagram - Account open(Retail, SME and Digital)
<img src="https://github.com/raahulmaurya1/Onboard-Agentic-AI/blob/ec2ee0084e800511a59289eac4bb74a0808b7325/account_open.png" alt="Sequence Diagram - Account open" style="width: 100%; height: auto; max-width: 500px;">

---

### 4. Parent Lifecycle System — Re-KYC & Reactivation

<img src="https://github.com/raahulmaurya1/Onboard-Agentic-AI/blob/ec2ee0084e800511a59289eac4bb74a0808b7325/rekyc_reactivate.png" alt="Parent Lifecycle System — Re-KYC & Reactivation
" style="width: 100%; height: auto; max-width: 500px;">

---

## 🛡️ Design Principles

### 1. 🧩 Modularity
Every agent is a standalone, independently testable Python module with no circular dependencies. The `DecisionAgent` never directly imports service code — it dispatches through the tool handler interface. New tools can be added by declaring a function schema and adding one `elif` branch to `handle_tool_call()`.

### 2. ⚖️ Fail-Open Resilience
The entire system is designed to **never block onboarding** due to an AI failure:
- Risk engine errors → `_risk_action: PROCEED` (applicant flows through)
- Gemini Tier 3 timeout (15s) → `additional_risk: 0` (no penalty)
- Face verification store failure → logged and skipped
- Celery task dispatch failure → user sees upload retry prompt

### 3. 🔒 Privacy by Design
- Raw PII (Aadhaar, PAN, phone) is **regex-redacted** before any log parsing
- `risk_evaluations` table stores **only bucketed, anonymized features** (age decade, NIC code, country ISO)
- No raw identity numbers ever enter the vector store or ML pipeline
- Session TTL (30 minutes) enforced at database level

### 4. 📈 Scalability
- **Horizontal**: Celery workers scale independently of FastAPI
- **Async I/O**: `asyncpg` + SQLAlchemy async for non-blocking DB operations
- **IVFFLAT indexes**: Both vector tables use approximate nearest-neighbor indexes for sub-millisecond semantic search at scale
- **Fire-and-forget**: Risk data persistence never adds to response latency

### 5. 🔭 Observability
- Structured logging with `[OnboardAI][COMPONENT]` prefixes on every agent action
- `[RiskHook]` log series traces every risk routing decision with score + category + flags
- `[POLL]` log series tracks async extraction state transitions
- `[Lifecycle]` log series traces every lifecycle operation with row counts

### 6. 🧱 Open-Closed Principle
The `_apply_risk_routing()` hook wires the risk pipeline into the orchestrator without modifying the pipeline itself. New account types, new risk tiers, and new tools can be added without touching the core agent loop.

---

## 🚀 Future Improvements

| Area | Planned Improvement |
|---|---|
| **Multi-Agent Collaboration** | Introduce a Supervisor Agent that dynamically spawns sub-agents for parallel document processing across multiple KYC types simultaneously |
| **Memory Optimization** | Implement sliding-window context compression for long sessions; use Redis TTL-based cache warming for frequent edge case patterns |
| **Autonomous Planning** | Upgrade from reactive single-step reasoning to multi-turn planning using Gemini's extended context window — allow the agent to pre-plan the remaining steps |
| **Model Routing** | Add a model selector that switches between Gemini Flash Lite (speed) and Gemini Pro (accuracy) based on risk score proximity to thresholds |
| **Streaming Responses** | Implement Server-Sent Events (SSE) for real-time agent reasoning traces visible in the UI |
| **Continuous Learning** | Use the `actual_outcome` field in `risk_evaluations` to feed verified labels back into a fine-tuned risk classifier |
| **Multi-Jurisdictional** | Abstract country-specific AML rules into pluggable rule modules per jurisdiction |
| **Audit Trail** | Full cryptographic audit log of every agent decision for regulatory compliance |

---

## 📄 License

This project is proprietary and confidential.

```
Copyright © 2026 OnboardAI. All Rights Reserved.

Unauthorized copying, distribution, modification, or use of this software
is strictly prohibited without prior written permission.
```

---

<div align="center">

**Built with 🧠 Agentic Intelligence · Powered by Gen AI · Secured by 3-Tier Risk Engine**

*"The system doesn't follow rules — it reasons about them."*

</div>
