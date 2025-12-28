# LLM Cost Optimization Orchestration

**Multi-agent, multi-vendor LLM orchestration that reduces human emotional friction through intelligent task decomposition and friction detection.**

## Core Innovation: Emotional Friction Mapping

**Where AI models show friction = Where humans feel frustration**

This system maps AI model friction to human emotional/cognitive friction. When different models (from different vendors with different training) disagree or struggle, they're surfacing the same micro-frustrations that accumulate during human task execution:
- Uncertainty about the right approach
- Confusion from too many options
- Doubt about correctness
- Overwhelm from complexity
- Anxiety about missing something critical

**This is what we're using AI to help with** - not just task completion, but emotional labor reduction.

### How It Works

1. **Decompose** - Break complex prompts into discrete subtasks using a cheap model
2. **Route** - Assign each subtask to the optimal model/provider based on learning
3. **Execute** - Run subtasks in parallel across multiple vendors (Anthropic, OpenAI, etc.)
4. **Detect Friction** - Analyze where models show cognitive variance (different approaches, uncertainty, contradictions)
5. **Map to Human Experience** - Translate AI friction into human emotions:
   - Model disagreement → Human uncertainty
   - Multiple approaches → Confusion/choice paralysis
   - Low confidence → Doubt and second-guessing
   - Long responses → Overwhelm
6. **Verify** - Run basic hallucination/error checks:
   - Factual consistency across models
   - Logical coherence
   - Specificity (not vague fabrications)
   - Grounding in concrete details
   - Cross-model agreement patterns
7. **Surface Insights** - Show users what micro-frustrations the AI handled for them
8. **Learn** - Shadow mode captures which frictions were valuable vs noise

### Key Benefits

- **Emotional Labor Reduction** - System handles uncertainty, doubt, and overwhelm that would drain human focus
- **Micro-Frustration Detection** - Surfaces the small annoyances that accumulate:
  - "Not sure which approach is right"
  - "Too many options to consider"
  - "Might be missing something important"
  - "This is taking longer than expected"
- **Transparent Difficulty** - Processing time reflects genuine complexity, not inefficiency
- **Hallucination Prevention** - 5 basic verification checks across multi-vendor responses
- **Human-Centered Value** - Shows users: "You saved X hours and avoided feeling Y emotions"
- **Cost Optimization** - Achieve comparable results at fraction of frontier model costs

## Architecture

```
User Prompt
  ↓
Decomposer (cheap model) → Subtasks
  ↓
Learning Router → Assign models from different vendors
  ↓
Multi-Provider Executor → Parallel execution across vendors
  ↓
Friction Detector → Analyze where models show cognitive variance
  ↓
Emotional Mapper → Translate AI friction to human emotions
  │  ├─ What would cause human uncertainty?
  │  ├─ What micro-frustrations would accumulate?
  │  └─ How much cognitive load + time saved?
  ↓
Verification Checks → Basic hallucination/error detection
  │  ├─ Factual consistency
  │  ├─ Logical coherence
  │  ├─ Specificity check
  │  ├─ Grounding verification
  │  └─ Cross-model agreement
  ↓
Result Aggregator → Synthesize with friction insights
  ↓
Response with Transparency
  │  ├─ The answer
  │  ├─ What friction was detected
  │  ├─ What human emotions/frustrations were addressed
  │  ├─ Verification check results
  │  ├─ Processing time explanation
  │  └─ Cost savings vs baseline
  ↓
Shadow Learning → Capture valuable friction patterns
```

## Use Cases

**Best for:**
- High-stakes decisions (medical, legal, financial)
- Bias detection and mitigation
- Edge case discovery
- Critical reasoning validation
- Iterative problem-solving where friction reveals insights

**Not ideal for:**
- Speed-critical tasks
- Simple queries with obvious answers
- Tasks where dissent adds no value

## Comparison vs Baseline

Measures cost and quality against using a single premium frontier model (Claude Opus 4.5, GPT-4o) through standard chat interface with attachments and MCP.

**Goal:** Achieve comparable or better results at significantly lower cost by intelligently routing work and using multi-vendor verification.

## Quick Start

### Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY

# Run the server
python main.py
```

Server will start at `http://localhost:8000`

### API Endpoints

- `POST /api/v1/execute` - Execute an orchestrated request
- `POST /api/v1/decompose` - Preview prompt decomposition
- `POST /api/v1/feedback` - Submit user feedback (shadow learning)
- `GET /api/v1/metrics/summary` - Get high-level metrics
- `GET /api/v1/metrics/detail` - Get detailed metrics with breakdowns

### Example Request

```bash
curl -X POST http://localhost:8000/api/v1/execute \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Analyze the security implications of using JWT tokens vs session cookies for authentication",
    "user_id": "user123"
  }'
```

## Current Status

✅ Backend API with FastAPI
✅ Prompt decomposition service
✅ Learning-based task router with shadow mode
✅ Multi-provider execution via OpenRouter
✅ **Friction detection system** - analyzes model cognitive variance
✅ **Emotional friction mapper** - maps AI friction to human emotions
✅ **5 verification checks** - hallucination/error detection
✅ **Human-centered response format** - shows what frustrations were handled
✅ Result aggregation with friction insights
✅ Cost comparison vs baseline
✅ Metrics tracking and API

🚧 Frontend dashboard (in progress)
🚧 Friction visualization components
🚧 Real-time processing transparency UI

## Response Format

When you make a request, you receive:

```json
{
  "aggregated_result": "The actual answer",
  "human_friction_insight": {
    "primary_emotions": ["uncertainty", "confusion"],
    "micro_frustrations": [
      "Not sure which approach is right",
      "Too many options to consider"
    ],
    "cognitive_load": "moderate",
    "time_saved_hours": 2.5,
    "user_message": "This task has moderate complexity. The AI is managing challenges like: Not sure which approach is right, Too many options to consider. This would typically take 2.5 hours of focused human effort."
  },
  "verification_checks": [
    {"check_type": "factual_consistency", "passed": true, "confidence": 0.87},
    {"check_type": "logical_coherence", "passed": true, "confidence": 0.92}
  ],
  "friction_points": [
    {
      "location": "methodology",
      "description": "Different approaches suggested",
      "severity": "moderate",
      "models_involved": ["anthropic/claude-3-haiku", "openai/gpt-4o"],
      "human_impact": "Choice paralysis from multiple valid options."
    }
  ],
  "processing_note": "Your request was decomposed into 3 specialized subtasks. The system detected 2 friction points where different models showed cognitive variance - this mirrors the difficulty a human would experience. Estimated time saved: 2.5 hours.",
  "cost_savings_percent": 78.3
}
```

## Next Steps

1. Build frontend dashboard with friction visualization
2. Enhance learning system to identify "valuable friction" patterns over time
3. Add iterative refinement mode where high-friction points trigger deeper analysis
4. Integrate user feedback to improve emotional mapping accuracy
5. Add real-time processing transparency (show what's happening as it happens) 
