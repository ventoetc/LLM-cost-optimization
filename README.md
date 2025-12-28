# LLM Cost Optimization Orchestration

**Multi-agent, multi-vendor LLM orchestration system that optimizes costs while improving quality through adversarial verification.**

## Core Innovation

Traditional multi-agent systems aim for consensus. This system uses **intentional dissent as a feature** to surface hallucinations, edge cases, and hidden assumptions.

### How It Works

1. **Decompose** - Break complex prompts into discrete subtasks using a cheap model
2. **Route** - Assign each subtask to the optimal model/provider based on learning
3. **Execute** - Run subtasks in parallel across multiple vendors (Anthropic, OpenAI, etc.)
4. **Verify** - Different models with different training/biases challenge each other
5. **Surface Friction** - Conflicts between vendor responses reveal hallucinations and assumptions
6. **Learn** - Shadow mode captures which disagreements led to better solutions

### Key Benefits

- **Hallucination Detection** - Multi-vendor diversity creates natural error checking
- **Cost Optimization** - Cheap models can challenge expensive ones, forcing justification
- **Quality Through Conflict** - Adversarial validation surfaces issues consensus would miss
- **Vendor Independence** - Never locked into a single provider's failure modes
- **Economic Incentives** - System learns which conflicts are valuable vs noise

## Architecture

```
User Prompt
  ↓
Decomposer (cheap model) → Subtasks
  ↓
Learning Router → Assign models from different vendors
  ↓
Multi-Provider Executor → Parallel execution
  ↓
Adversarial Verification → Surface conflicts & dissent
  ↓
Result Aggregator → Synthesize with conflict analysis
  ↓
Cost Comparison vs Baseline (frontier model)
  ↓
Shadow Learning → Capture what dissent was valuable
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
✅ Result aggregation
✅ Cost comparison vs baseline
✅ Metrics tracking and API

🚧 Frontend dashboard (in progress)
🚧 Adversarial verification layer
🚧 Dissent/conflict visualization

## Next Steps

1. Implement explicit adversarial verification where models challenge each other's outputs
2. Add conflict detection and surfacing in results
3. Build frontend dashboard with dissent visualization
4. Enhance learning system to identify "valuable dissent" patterns
5. Add support for iterative refinement based on conflicts 
