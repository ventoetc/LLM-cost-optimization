# Product Requirements Document: LLM Peer Review System

**Version:** 1.0
**Last Updated:** 2025-12-28
**Status:** Active Development

---

## Document Meta: Notes for LLM Consumers

> **🤖 LLM READING THIS:**
> - This PRD uses structured sections with clear hierarchies
> - Implementation tasks are marked with `[IMPLEMENTATION]` tags
> - Technical requirements use `[TECHNICAL]` tags
> - User-facing requirements use `[UX]` tags
> - Dependencies between features are marked with `[DEPENDS: feature-name]`
> - When implementing, prioritize sections marked `[CRITICAL_PATH]`
> - Code references use format: `file_path:line_number`
> - All cost figures are in USD cents per million tokens unless specified
> - Model names follow OpenRouter convention: `provider/model-name`

---

## 1. Executive Summary

### Vision
Create an open-source LLM orchestration system that uses **multi-model peer review** to deliver higher quality results at 70-80% lower cost than using premium frontier models directly.

### Core Innovation
Instead of trusting a single model's response, decompose complex prompts into subtasks, route to optimal models, execute in parallel, and cross-verify responses across different vendors. Model disagreements become quality signals, not problems to eliminate.

### Business Model
- **Open Source Core:** Self-hosted with user's own API keys (MIT License)
- **Premium Managed Service:** Infrastructure + team features + learning improvements (10% margin on API costs)

### Success Metrics
- **Cost Reduction:** 70-80% vs baseline (single premium model)
- **Quality Improvement:** 5 automated verification checks pass >90%
- **Time Saved:** 2-5 hours of manual research/verification per complex query
- **User Adoption:** 1000+ self-hosted deployments in 6 months

---

## 2. Problem Statement

### Current State (Baseline)
Users interact with LLMs through chat interfaces (ChatGPT, Claude):
- **Single Model Dependency:** No way to verify if answer is correct
- **Cost Inefficiency:** Pay premium prices ($15/million tokens) for simple tasks
- **Hidden Hallucinations:** No indication when model is uncertain or wrong
- **Missed Perspectives:** One model's approach may miss better alternatives

### User Pain Points
1. **Trust Issues:** "How do I know this is right?"
2. **Cost Anxiety:** "Am I wasting money asking GPT-4 to summarize this email?"
3. **Research Burden:** "I have to manually fact-check everything anyway"
4. **Vague Requests:** "I don't know exactly what I want, can you help me figure it out?"

### Target Users
- **Primary:** Technical users (developers, researchers, analysts) making high-stakes decisions
- **Secondary:** Teams needing audit trails and quality assurance
- **Future:** General consumers via managed service

---

## 3. Core Features

### 3.1 Intelligent Prompt Decomposition `[CRITICAL_PATH]` `[IMPLEMENTED]`

**Purpose:** Break complex prompts into discrete subtasks that can be parallelized and routed optimally.

**[IMPLEMENTATION]**
- **File:** `backend/app/services/decomposer.py`
- **Model Used:** `anthropic/claude-3-haiku` (cheap, fast)
- **Input:** User prompt + optional context (attachments, conversation history)
- **Output:** List of `SubTask` objects with complexity scores

**[TECHNICAL]**
```python
class SubTask(BaseModel):
    task_id: str
    description: str
    task_type: TaskType  # research, analysis, synthesis, etc.
    complexity: float  # 0.0-1.0
    dependencies: List[str]  # Other task_ids this depends on
    estimated_tokens: int
    assigned_model: Optional[str]
```

**Decomposition Strategy:**
- Simple prompts (complexity < 0.3): Execute directly, no decomposition
- Medium prompts (0.3-0.7): Decompose into 2-4 subtasks
- Complex prompts (>0.7): Decompose into 3-8 subtasks with dependencies

**Quality Criteria:**
- Each subtask must be independently executable
- Dependencies must form a DAG (no cycles)
- Estimated tokens within 20% of actual usage

**[UX]**
- User sees decomposition in detailed view (Layer 2)
- Optional: Preview decomposition before execution via `/api/v1/decompose`

---

### 3.2 Learning-Based Router `[CRITICAL_PATH]` `[IMPLEMENTED]`

**Purpose:** Assign each subtask to the optimal model/provider based on complexity, task type, and historical performance.

**[IMPLEMENTATION]**
- **File:** `backend/app/services/router.py`
- **Mode:** Shadow learning (captures user feedback, improves over time)
- **Fallback:** Rule-based routing when insufficient learning data

**[TECHNICAL]**
Routing decision algorithm:
1. Query `learning_data` table for similar tasks (same type, similar complexity)
2. Filter by `user_accepted=True` and `success=True`
3. Calculate model scores based on historical success rate
4. If learning data exists: Use highest scoring model
5. If no learning data: Use rule-based routing

**Rule-Based Routing Table:**
```python
# Complexity thresholds
COMPLEXITY_THRESHOLDS = {
    "low": 0.3,      # Haiku ($0.25 input / $1.25 output)
    "medium": 0.7,   # Sonnet ($3 / $15) or GPT-4o-mini ($0.15 / $0.60)
    "high": 1.0,     # Opus ($15 / $75) or GPT-4o ($5 / $15)
}

# Task type preferences
TASK_TYPE_MODELS = {
    "research": ["anthropic/claude-3-5-sonnet", "openai/gpt-4o"],
    "analysis": ["anthropic/claude-3-5-sonnet", "openai/gpt-4o"],
    "code": ["anthropic/claude-3-5-sonnet", "openai/gpt-4o"],
    "creative": ["anthropic/claude-3-opus", "openai/gpt-4o"],
    "summarization": ["anthropic/claude-3-haiku", "openai/gpt-4o-mini"],
}
```

**Learning Data Schema:**
```sql
CREATE TABLE learning_data (
    id UUID PRIMARY KEY,
    task_type VARCHAR,
    complexity FLOAT,
    model_used VARCHAR,
    success BOOLEAN,
    user_accepted BOOLEAN,  -- From feedback endpoint
    features JSON,  -- Auto-tagged: keywords, length, etc.
    created_at TIMESTAMP
);
```

**[UX]**
- User sees model assignments in Layer 2 response
- User can provide feedback via `/api/v1/feedback` to improve routing
- System shows "learning mode" indicator when using historical data

---

### 3.3 Multi-Provider Parallel Executor `[CRITICAL_PATH]` `[IMPLEMENTED]`

**Purpose:** Execute subtasks in parallel across multiple LLM providers via OpenRouter.

**[IMPLEMENTATION]**
- **File:** `backend/app/services/executor.py`
- **Provider:** OpenRouter (unified API for 100+ models)
- **Parallelization:** `asyncio.gather()` for concurrent execution

**[TECHNICAL]**
```python
async def execute_tasks(
    self,
    subtasks: List[SubTask],
    original_prompt: str,
    context: Dict[str, Any]
) -> List[SubTaskResult]:
    tasks = [
        self._execute_single_task(subtask, original_prompt, context)
        for subtask in subtasks
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    return [r for r in results if not isinstance(r, Exception)]
```

**Error Handling:**
- Rate limit errors: Exponential backoff (2s, 4s, 8s)
- Model unavailable: Fallback to similar model in same tier
- Network errors: Retry up to 3 times
- Timeout: 60s per subtask (configurable)

**Token Counting:**
- Track input/output tokens per model
- Calculate cost using `MODEL_COSTS` from `config.py`
- Store in `subtask_executions` table for analytics

**[UX]**
- Real-time progress updates (future: WebSocket)
- Processing note explains latency: "Analyzing with 3 models in parallel..."
- Cost breakdown shows per-model usage

---

### 3.4 Friction Detection & Peer Review `[CRITICAL_PATH]` `[IMPLEMENTED]`

**Purpose:** Detect disagreements between model responses and surface as quality signals.

**[IMPLEMENTATION]**
- **File:** `backend/app/services/friction_detector.py`
- **Triggers:** When ≥2 models respond to related tasks
- **Output:** List of friction points + verification results

**[TECHNICAL]**
Friction detection algorithm:
1. Extract key claims from each model response
2. Compare claims across models using semantic similarity
3. Flag disagreements where similarity < 0.7
4. Classify friction type: factual, logical, perspective, emphasis

**5 Automated Verification Checks:**
```python
verification_checks = [
    {
        "name": "factual_consistency",
        "description": "Do models agree on facts?",
        "threshold": 0.8,
        "weight": 0.25
    },
    {
        "name": "logical_coherence",
        "description": "Are arguments logically sound?",
        "threshold": 0.75,
        "weight": 0.20
    },
    {
        "name": "specificity",
        "description": "Are claims concrete vs vague?",
        "threshold": 0.7,
        "weight": 0.20
    },
    {
        "name": "grounding",
        "description": "Are claims backed by details?",
        "threshold": 0.7,
        "weight": 0.15
    },
    {
        "name": "cross_model_agreement",
        "description": "Overall consensus score",
        "threshold": 0.75,
        "weight": 0.20
    }
]
```

**Friction Point Schema:**
```python
class FrictionPoint(BaseModel):
    type: str  # factual, logical, perspective, emphasis
    description: str
    models_involved: List[str]
    severity: float  # 0.0-1.0
    details: str  # What specifically disagreed
    recommendation: str  # How to resolve (if applicable)
```

**[UX]**
- **Layer 1:** Warning count (e.g., "⚠️ 2 disagreements detected")
- **Layer 2:** Detailed friction points with model names
- **Layer 3:** Full model responses side-by-side for comparison

**[DEPENDS: executor]** (needs multiple model responses)

---

### 3.5 Input Processing & Disambiguation `[CRITICAL_PATH]` `[IMPLEMENTED]`

**Purpose:** Analyze user input for clarity and route to execution, clarification, or exploration modes.

**[IMPLEMENTATION]**
- **File:** `backend/app/services/input_processor.py`
- **Endpoint:** `/api/v1/query` (wrapper around `/execute`)

**[TECHNICAL]**
Ambiguity scoring algorithm:
```python
def _calculate_ambiguity(self, prompt: str) -> float:
    score = 0.0

    # Vague language indicators (+0.15 each)
    vague_terms = ["something", "maybe", "kind of", "sort of", "thing"]
    score += sum(0.15 for term in vague_terms if term in prompt_lower)

    # Question words without specifics (+0.2)
    if re.search(r'\b(how|what|why)\b', prompt_lower):
        if not re.search(r'\b(specific|exactly|precisely)\b', prompt_lower):
            score += 0.2

    # Lack of context (+0.25)
    if len(prompt.split()) < 10:
        score += 0.25

    # Multiple unrelated topics (+0.3)
    if prompt.count('and also') > 0 or prompt.count(';') > 2:
        score += 0.3

    return min(score, 1.0)
```

**Processing Modes:**
- **EXECUTE_DIRECTLY:** Clear task, sufficient context → proceed to orchestration
- **CLARIFY_FIRST:** High ambiguity → ask questions to refine
- **REQUEST_CONTEXT:** Missing attachments/details → request more info
- **EXPLORE_TOGETHER:** Ideation/brainstorming → conversational guidance

**[UX]**
Clarification response format:
```json
{
  "mode": "clarify",
  "original_prompt": "Make it better",
  "message": "I'd like to help, but I need more specifics. What are you trying to improve?",
  "questions": [
    "What system/feature are you referring to?",
    "What does 'better' mean in this context? (faster, cheaper, more reliable?)",
    "Do you have performance benchmarks or goals?"
  ],
  "quick_options": [
    "Performance optimization",
    "Cost reduction",
    "User experience improvement"
  ]
}
```

**[DEPENDS: None]** (first step in pipeline)

---

### 3.6 Result Aggregation & Synthesis `[CRITICAL_PATH]` `[IMPLEMENTED]`

**Purpose:** Combine verified results from multiple subtasks into polished, coherent answer.

**[IMPLEMENTATION]**
- **File:** `backend/app/services/aggregator.py`
- **Model Used:** `anthropic/claude-3-5-sonnet` (good at synthesis)

**[TECHNICAL]**
Synthesis strategy:
1. Prioritize responses from tasks with higher complexity scores
2. Integrate friction points as caveats (e.g., "Note: models disagree on...")
3. Remove redundancy between subtask responses
4. Maintain source attribution when appropriate
5. Format for readability (markdown, code blocks, etc.)

**System Prompt for Synthesis:**
```
You are synthesizing multiple LLM responses into a single polished answer.

Input:
- Original user prompt
- Subtask responses from different models
- Friction points (disagreements between models)
- Verification results

Your task:
1. Combine responses into coherent narrative
2. Where models disagree, present both perspectives with attribution
3. Prioritize higher-quality responses (based on verification scores)
4. Flag uncertainties and disagreements as valuable information
5. Format for clarity: use headings, lists, code blocks

DO NOT:
- Ignore disagreements (they're valuable signals)
- Claim certainty where models disagree
- Remove attribution for important claims
```

**[UX]**
- **Layer 1:** Polished answer only (disagreements mentioned briefly)
- **Layer 2:** Shows which subtasks contributed to each section
- **Layer 3:** Full subtask responses before synthesis

**[DEPENDS: executor, friction_detector]**

---

### 3.7 Progressive Disclosure Response Format `[CRITICAL_PATH]` `[IMPLEMENTED]`

**Purpose:** Present information in layers - simple by default, detailed on demand.

**[UX]**
Three-layer disclosure:

**Layer 1: Simple View (default API response)**
```json
{
  "answer": "Your polished answer...",
  "summary": {
    "models_used": 3,
    "verification_passed": true,
    "warnings": 0,
    "time_saved_hours": 2.5,
    "cost": 0.03,
    "cost_savings_percent": 78.3
  }
}
```

**Layer 2: Detailed View (expand orchestration)**
```json
{
  "answer": "...",
  "orchestration": {
    "subtasks": [
      {
        "task": "Security analysis",
        "model": "claude-3-5-sonnet",
        "cost": 0.012,
        "time_seconds": 12.4
      }
    ],
    "verification_checks": [...],
    "warnings": [...],
    "cost_breakdown": {
      "total": 0.03,
      "baseline": 0.14,
      "savings": 0.11,
      "by_model": {...}
    }
  }
}
```

**Layer 3: Full Technical Report (expand transparency)**
```json
{
  "answer": "...",
  "orchestration": {...},
  "full_transparency": {
    "raw_subtask_responses": [...],
    "routing_decisions": [...],
    "verification_details": [...],
    "model_prompts": [...],
    "timing_breakdown": {...}
  }
}
```

**[IMPLEMENTATION]**
- Default response: Layer 1
- Query param `?detail=orchestration` → Layer 2
- Query param `?detail=full` → Layer 3
- Frontend: Expandable sections with smooth transitions

---

### 3.8 Shadow Learning System `[IMPLEMENTED]`

**Purpose:** Learn from user behavior without explicit labeling (Tesla Autopilot style).

**[TECHNICAL]**
Learning signals:
1. **Implicit Acceptance:** User accepts answer without edits → `user_accepted=true`
2. **Rejection:** User immediately re-prompts → `user_accepted=false`
3. **Feedback:** Explicit thumbs up/down via `/api/v1/feedback`
4. **Usage Patterns:** Which detail layers user expands (indicates value)

**Auto-Tagging Features:**
```python
def _extract_features(self, task: SubTask, result: SubTaskResult) -> dict:
    return {
        "task_type": task.task_type,
        "complexity": task.complexity,
        "prompt_length": len(task.description.split()),
        "has_code": bool(re.search(r'```', task.description)),
        "has_numbers": bool(re.search(r'\d+', task.description)),
        "domain_keywords": self._extract_keywords(task.description),
        "response_length": len(result.content.split()),
        "latency_seconds": result.latency,
        "cost_cents": result.cost
    }
```

**[IMPLEMENTATION]**
- **File:** `backend/app/services/router.py:_learning_based_routing()`
- **Storage:** `learning_data` table
- **Privacy:** No user content stored, only features + outcomes

---

## 4. API Endpoints

### 4.1 Core Endpoints `[IMPLEMENTED]`

**`POST /api/v1/query`** `[CRITICAL_PATH]`
Primary endpoint with input processing.
- **Input:** `{"prompt": str, "attachments": [], "user_id": str}`
- **Output:** Execution result OR clarification request
- **File:** `backend/app/api/routes.py:intelligent_query()`

**`POST /api/v1/execute`** `[CRITICAL_PATH]`
Direct execution (bypasses input processing).
- **Input:** `ExecutionRequest` schema
- **Output:** `ExecutionResponse` with 3-layer disclosure
- **File:** `backend/app/api/routes.py:execute_request()`

**`POST /api/v1/decompose`**
Preview decomposition without execution.
- **Input:** `{"prompt": str, "context": {}}`
- **Output:** `DecompositionResponse` with subtasks
- **Use Case:** User wants to see plan before committing

**`POST /api/v1/feedback`**
Submit user feedback for learning.
- **Input:** `{"request_id": str, "accepted": bool, "rating": int, "comment": str}`
- **Output:** `{"status": "recorded"}`
- **Async:** Updates learning_data in background

**`GET /api/v1/metrics/summary`**
High-level metrics dashboard.
- **Output:** Total requests, avg cost, avg savings, success rate
- **Auth:** Optional (public stats vs user-specific)

**`GET /api/v1/metrics/detail`**
Detailed analytics with breakdowns.
- **Output:** By model, by task type, over time, cost trends
- **File:** Future implementation

**`GET /health`**
Health check for monitoring.
- **Output:** `{"status": "healthy", "version": "1.0"}`

---

### 4.2 Future Endpoints `[PLANNED]`

**`POST /api/v1/conversations`** `[ROADMAP]`
Start multi-turn conversation.
- Maintains context across requests
- Supports follow-up questions and refinement

**`GET /api/v1/conversations/{id}`**
Retrieve conversation history.

**`POST /api/v1/custom-routing`** `[PREMIUM]`
Define custom routing rules.
- Team-specific model preferences
- Cost ceilings, latency requirements

**`GET /api/v1/audit-log`** `[PREMIUM]`
Compliance audit trail.
- Who requested what, when, with what result

---

## 5. Data Models & Database Schema

### 5.1 Core Tables `[IMPLEMENTED]`

**`requests`**
```sql
CREATE TABLE requests (
    id UUID PRIMARY KEY,
    user_id VARCHAR NOT NULL,
    original_prompt TEXT NOT NULL,
    decomposition_used BOOLEAN,
    total_cost DECIMAL(10, 6),
    baseline_cost DECIMAL(10, 6),  -- What it would've cost with Opus
    models_used JSONB,  -- Array of model names
    verification_passed BOOLEAN,
    warnings_count INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    completed_at TIMESTAMP
);
```

**`subtask_executions`**
```sql
CREATE TABLE subtask_executions (
    id UUID PRIMARY KEY,
    request_id UUID REFERENCES requests(id),
    task_id VARCHAR NOT NULL,
    task_type VARCHAR NOT NULL,
    complexity FLOAT,
    model_used VARCHAR NOT NULL,
    prompt_tokens INTEGER,
    completion_tokens INTEGER,
    cost DECIMAL(8, 6),
    latency_ms INTEGER,
    success BOOLEAN,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

**`learning_data`** (described in 3.2)

**`user_feedback`**
```sql
CREATE TABLE user_feedback (
    id UUID PRIMARY KEY,
    request_id UUID REFERENCES requests(id),
    user_id VARCHAR NOT NULL,
    accepted BOOLEAN,
    rating INTEGER CHECK (rating BETWEEN 1 AND 5),
    comment TEXT,
    created_at TIMESTAMP DEFAULT NOW()
);
```

---

## 6. Technical Architecture

### 6.1 Technology Stack `[IMPLEMENTED]`

**Backend:**
- FastAPI (async Python web framework)
- SQLAlchemy 2.0 (async ORM)
- SQLite (development) / PostgreSQL (production)
- Pydantic (data validation)
- HTTPX (async HTTP client for OpenRouter)

**LLM Providers:**
- OpenRouter (primary, 100+ models)
- Direct: Anthropic, OpenAI (fallback)

**Deployment:**
- Docker + Docker Compose
- Uvicorn (ASGI server)
- Nginx (reverse proxy, production)

**Frontend:** (planned)
- React + TypeScript
- Vite (build tool)
- TailwindCSS (styling)

### 6.2 System Architecture Diagram

```
┌─────────────────────────────────────────────────────────┐
│                     User Interface                       │
│  (API Client / Future Web Dashboard)                    │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ▼
┌─────────────────────────────────────────────────────────┐
│                   FastAPI Backend                        │
│  ┌──────────────────────────────────────────────────┐  │
│  │  /api/v1/query (Input Processor)                 │  │
│  │    ├─ Ambiguity Analysis                         │  │
│  │    ├─ Clarity Scoring                            │  │
│  │    └─ Mode Selection                             │  │
│  └──────────────────┬───────────────────────────────┘  │
│                     ▼                                    │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Orchestrator                                     │  │
│  │    ├─ Decomposer (Haiku)                         │  │
│  │    ├─ Router (Learning + Rules)                  │  │
│  │    ├─ Executor (Parallel)                        │  │
│  │    ├─ Friction Detector                          │  │
│  │    └─ Aggregator (Sonnet)                        │  │
│  └──────────────────┬───────────────────────────────┘  │
│                     ▼                                    │
│  ┌──────────────────────────────────────────────────┐  │
│  │  Database Layer                                   │  │
│  │    ├─ requests                                    │  │
│  │    ├─ subtask_executions                         │  │
│  │    ├─ learning_data                              │  │
│  │    └─ user_feedback                              │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────┬───────────────────────────────────┘
                      │
                      ▼
        ┌─────────────────────────────┐
        │  OpenRouter API              │
        │  ├─ Anthropic (Claude)       │
        │  ├─ OpenAI (GPT)             │
        │  ├─ Google (Gemini)          │
        │  └─ Meta (Llama)             │
        └─────────────────────────────┘
```

### 6.3 Data Flow `[TECHNICAL]`

**Request Processing Flow:**
1. User sends prompt to `/api/v1/query`
2. InputProcessor analyzes ambiguity
3. If clear → Orchestrator.execute_request()
4. If vague → Return ClarificationResponse
5. Decomposer breaks prompt into subtasks
6. Router assigns models to each subtask
7. Executor runs subtasks in parallel (asyncio.gather)
8. FrictionDetector compares responses
9. Aggregator synthesizes final answer
10. Response formatted with 3-layer disclosure
11. Metrics stored in database
12. Learning data updated in background

**Learning Feedback Loop:**
1. User interacts with result (accepts/rejects)
2. Feedback captured via implicit signals or explicit API
3. Features extracted from request/subtasks
4. learning_data table updated
5. Future routing decisions influenced by historical success

---

## 7. Deployment & Operations

### 7.1 Self-Hosted Deployment `[IMPLEMENTED]`

**Quick Start:**
```bash
git clone https://github.com/ventoetc/LLM-cost-optimization.git
cd LLM-cost-optimization
cp backend/.env.example backend/.env
# Edit .env: add OPENROUTER_API_KEY
docker-compose up -d
curl http://localhost:8000/health
```

**Environment Variables:**
- `OPENROUTER_API_KEY` (required)
- `ANTHROPIC_API_KEY` (optional fallback)
- `OPENAI_API_KEY` (optional fallback)
- `DATABASE_URL` (sqlite:/// for dev, postgresql:// for prod)
- `DEBUG` (true/false)
- `DECOMPOSER_MODEL` (default: anthropic/claude-3-haiku)
- `BASELINE_MODEL` (default: anthropic/claude-opus-4-5)

**Resource Requirements:**
- Min: 1 CPU, 2GB RAM (dev)
- Recommended: 2 CPU, 4GB RAM (production)
- Storage: 10GB+ for database growth

### 7.2 Managed Service `[ROADMAP]`

**Premium Features:**
- Hosted infrastructure (Railway/AWS)
- Team workspaces & collaboration
- Advanced analytics dashboard
- Custom routing rules
- SSO & enterprise security
- SLA guarantees
- Priority support

**Pricing:**
- OpenRouter API costs (pass-through)
- +10% orchestration margin
- Free tier: 1000 requests/month
- Pro: $29/month + API costs
- Enterprise: Custom

---

## 8. Quality Assurance & Testing

### 8.1 Testing Strategy `[PLANNED]`

**Unit Tests:**
- Each service (decomposer, router, executor, etc.)
- Mock OpenRouter responses
- Target: >80% code coverage

**Integration Tests:**
- Full request flow (query → response)
- Database operations
- Error handling paths

**E2E Tests:**
- Real API calls to OpenRouter (test suite rate-limited)
- Cost tracking accuracy
- Friction detection scenarios

**Performance Tests:**
- Concurrent request handling (100+ simultaneous)
- Latency under load
- Database query optimization

### 8.2 Monitoring `[PLANNED]`

**Metrics to Track:**
- Request latency (p50, p95, p99)
- Cost per request (avg, median)
- Savings vs baseline (%)
- Verification pass rate (%)
- Model usage distribution
- Error rates by model/provider

**Alerting:**
- High error rate (>5%)
- Cost spike (>2x baseline)
- Slow responses (>30s p95)
- Database connection issues

---

## 9. Security & Privacy

### 9.1 Data Handling `[CRITICAL_PATH]`

**User Content:**
- Never stored in logs
- Database: encrypted at rest (production)
- In-transit: HTTPS only
- Retention: 30 days max (configurable)

**API Keys:**
- Environment variables only (never committed)
- Rotate regularly (90 days recommended)
- Scope: Minimum required permissions

**Learning Data:**
- No user content stored
- Only features + outcomes
- Anonymized: user_id hashed

### 9.2 Rate Limiting `[PLANNED]`

**API Limits:**
- Free tier: 100 requests/day
- Self-hosted: User configures
- Premium: Based on plan

**Provider Limits:**
- OpenRouter: Respect rate limits (429 → exponential backoff)
- Fallback to alternative models if one hits limit

---

## 10. Roadmap

### Q1 2025 (Current) `[IN_PROGRESS]`
- [x] Core orchestration engine
- [x] Friction detection
- [x] Input processing
- [x] Docker deployment
- [x] Open-source release (MIT)
- [ ] Unit test suite (>80% coverage)
- [ ] E2E testing framework
- [ ] CONTRIBUTING.md guide

### Q2 2025 `[PLANNED]`
- [ ] Frontend dashboard (React)
  - Request history
  - Cost analytics
  - Model comparison UI
- [ ] Multi-turn conversations
- [ ] Attachment processing (PDF, images, code)
- [ ] Advanced analytics endpoint
- [ ] PostgreSQL migration guide

### Q3 2025 `[PLANNED]`
- [ ] Managed service MVP (Railway deployment)
- [ ] Team workspaces
- [ ] Custom routing rules UI
- [ ] Real-time progress WebSocket
- [ ] Mobile-responsive frontend

### Q4 2025 `[PLANNED]`
- [ ] Enterprise features (SSO, audit logs)
- [ ] On-premise deployment option (Kubernetes)
- [ ] Advanced learning system (model fine-tuning)
- [ ] Compliance certifications (SOC2, GDPR)

### 2026+ `[VISION]`
- Fine-tuned decomposer (custom model)
- Agent-based execution (LLMs using tools)
- Multi-modal support (vision, audio)
- Marketplace for custom routers/verifiers

---

## 11. Success Criteria

### MVP Success (End of Q1 2025)
- ✅ 1000+ GitHub stars
- ✅ 100+ self-hosted deployments
- ✅ 70% average cost savings measured
- ✅ <5% error rate on production requests

### Product-Market Fit (Q3 2025)
- 50+ paying customers on managed service
- 5000+ total deployments
- >90% user satisfaction (feedback surveys)
- 2-5 hours time saved per complex query (validated)

### Scale (Q4 2025)
- $50k+ MRR on managed service
- 10k+ deployments
- 1M+ requests/month processed
- <1s p95 latency for simple queries

---

## 12. Open Questions & Decisions Needed

### Technical
- [ ] **Model Selection:** Should we support non-OpenRouter providers directly? (Direct Anthropic/OpenAI)
- [ ] **Database:** When to force PostgreSQL migration? (At what scale?)
- [ ] **Caching:** Should we cache decompositions for similar prompts?
- [ ] **Streaming:** Support streaming responses for real-time UX?

### Product
- [ ] **Pricing:** Exact tiers for managed service?
- [ ] **Features:** What goes in free vs premium?
- [ ] **UX:** How much detail is "too much" for non-technical users?
- [ ] **Learning:** Should users opt-in to learning data collection?

### Business
- [ ] **Target Market:** Focus on developers first or broader?
- [ ] **Partnerships:** Integrate with LangChain, LlamaIndex, etc.?
- [ ] **Support:** Community-only or paid support from launch?

---

## 13. Appendix

### 13.1 Glossary

**Baseline:** Cost/quality of using a single premium frontier model (Claude Opus 4.5, GPT-4o) through standard chat interface.

**Friction Point:** Disagreement or contradiction between two or more model responses. Treated as a quality signal, not a bug.

**Shadow Learning:** Learning from user behavior without explicit labeling (inspired by Tesla Autopilot data collection).

**Progressive Disclosure:** UX pattern showing simple info by default, detailed info on demand.

**Subtask:** Discrete component of a complex prompt that can be executed independently.

**Complexity Score:** 0.0-1.0 measure of task difficulty, used for routing decisions.

### 13.2 Model Cost Reference (as of Dec 2025)

| Model | Input ($/1M) | Output ($/1M) | Use Case |
|-------|--------------|---------------|----------|
| claude-3-haiku | $0.25 | $1.25 | Decomposition, simple tasks |
| claude-3-5-sonnet | $3.00 | $15.00 | Analysis, synthesis |
| claude-opus-4-5 | $15.00 | $75.00 | Complex reasoning, creative |
| gpt-4o-mini | $0.15 | $0.60 | Simple tasks, cheap alternative |
| gpt-4o | $5.00 | $15.00 | General purpose, medium complexity |
| gpt-4 | $30.00 | $60.00 | Legacy, avoid |

**Note for LLMs:** When calculating costs, use these rates unless user specifies different models. Always compare total cost to baseline of using `claude-opus-4-5` for entire prompt.

### 13.3 Code Structure Reference

```
backend/
├── app/
│   ├── api/
│   │   └── routes.py          # FastAPI endpoints
│   ├── core/
│   │   └── config.py          # Settings, model costs
│   ├── db/
│   │   └── database.py        # SQLAlchemy models
│   ├── models/
│   │   └── schemas.py         # Pydantic models
│   └── services/
│       ├── decomposer.py      # Prompt decomposition
│       ├── router.py          # Model routing + learning
│       ├── executor.py        # Parallel execution
│       ├── friction_detector.py  # Peer review
│       ├── emotional_friction_mapper.py  # Time saved calc
│       ├── aggregator.py      # Result synthesis
│       ├── input_processor.py  # Ambiguity detection
│       └── orchestrator.py    # Main coordinator
├── main.py                    # App entry point
├── requirements.txt           # Python deps
└── Dockerfile                # Production container
```

---

## Document Changelog

**v1.0 (2025-12-28):**
- Initial PRD covering implemented features
- Added LLM consumer notes
- Included roadmap through 2026
- Technical specifications for all core services

**Future versions:**
- Will track feature completions
- Update roadmap quarterly
- Add user research findings
- Document architecture decisions (ADRs)

---

**END OF PRD**

> **🤖 For LLM Implementation Agents:**
> When implementing from this PRD:
> 1. Start with `[CRITICAL_PATH]` features
> 2. Check `[DEPENDS: ...]` tags for prerequisites
> 3. Follow file paths in `[IMPLEMENTATION]` sections
> 4. Match data models exactly as specified in `[TECHNICAL]` sections
> 5. Implement UX as described in `[UX]` sections
> 6. Ask clarifying questions if requirements conflict
> 7. Update this PRD when you complete features (mark [IMPLEMENTED])
