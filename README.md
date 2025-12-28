# LLM Cost Optimization

**Open-source intelligent routing for multi-model LLM orchestration. Save 70% on costs while improving quality through cross-model verification.**

🆓 **Self-host with your own API keys** | 🚀 **Premium managed service available**

---

## The Problem: Single Point of Failure

Using ChatGPT or Claude directly means:
- Paying premium prices for simple tasks
- Trusting one model's answer without verification
- No way to know if it hallucinated
- Missing better approaches the model didn't consider

## The Solution: Intelligent Multi-Model Routing

**Open source system that:**
- Decomposes prompts into optimal subtasks
- Routes each piece to the best model for the job (cheap → expensive only when needed)
- Cross-checks responses across different vendors
- Flags disagreements as quality signals
- Shows complete transparency into how answers were built

**You save 70-80% vs using premium models for everything, with BETTER quality through verification.**

**Core benefits:**
- **70-80% cost savings** - Use cheap models for simple tasks, premium only where needed
- **Built-in verification** - Multiple models cross-check each other
- **Warning flags** - See where models disagree (that's valuable intel)
- **Time saved** - Automation handles research + verification you'd do manually
- **Full transparency** - See exactly how your answer was made

### How It Works

1. **Decompose** - Break complex prompts into discrete subtasks using a cheap model
2. **Route** - Assign each subtask to the optimal model/provider based on task complexity
3. **Execute** - Run subtasks in parallel across multiple vendors (Anthropic, OpenAI, etc.)
4. **Cross-Check** - Compare responses to detect disagreements and contradictions
5. **Verify** - Run automated quality checks:
   - Factual consistency across models
   - Logical coherence
   - Specificity (detect vague/hallucinated content)
   - Grounding in concrete details
   - Cross-model agreement scoring
6. **Flag Warnings** - Surface disagreements as quality signals
7. **Synthesize** - Combine verified results into polished answer
8. **Learn** - System improves routing decisions based on outcomes

### Key Benefits

**Cost Savings**
- 70-80% cheaper than using premium models for everything
- Pay-per-use pricing (not flat subscription)
- Automatic routing to cheapest suitable model

**Quality Assurance**
- Multi-model cross-checking catches errors
- 5 automated verification checks
- Warning flags when models disagree
- No single point of failure

**Time Savings**
- Parallel processing across models
- Automated verification (no manual fact-checking needed)
- Shows what research it handled for you

**Transparency**
- See exactly which models were used
- View disagreements and why they matter
- Full cost breakdown
- Progressive disclosure (simple view → detailed technical report)

## Architecture

```
User Prompt
  ↓
Decomposer (cheap model) → Break into subtasks
  ↓
Learning Router → Assign optimal model to each task
  │  ├─ Simple tasks → Haiku ($)
  │  ├─ Medium tasks → Sonnet/GPT-4o ($$)
  │  └─ Complex tasks → Opus ($$$)
  ↓
Multi-Provider Executor → Parallel execution
  ↓
Quality Analyzer → Cross-check responses
  │  ├─ Detect disagreements
  │  ├─ Flag contradictions
  │  └─ Identify quality issues
  ↓
Verification Checks → Automated quality assurance
  │  ├─ Factual consistency
  │  ├─ Logical coherence
  │  ├─ Specificity check
  │  ├─ Grounding verification
  │  └─ Cross-model agreement
  ↓
Result Synthesizer → Combine verified results
  ↓
Transparent Response
  │  ├─ Polished answer
  │  ├─ Warning flags (if any)
  │  ├─ Verification results
  │  ├─ Time saved estimate
  │  ├─ Cost breakdown
  │  └─ Full technical details (on demand)
  ↓
Learning System → Improve routing over time
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

### Self-Hosted (Docker - Recommended)

```bash
# Clone repo
git clone https://github.com/ventoetc/LLM-cost-optimization.git
cd LLM-cost-optimization

# Configure API keys
cp backend/.env.example backend/.env
# Edit .env and add your OPENROUTER_API_KEY

# Start everything
docker-compose up -d

# Verify
curl http://localhost:8000/health
```

**That's it!** API runs at `http://localhost:8000`, frontend at `http://localhost:3000`

**See [DEPLOYMENT.md](DEPLOYMENT.md) for production setup, cloud deployment, scaling, etc.**

### Local Development (Python)

```bash
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env  # Add your API keys
python main.py
```

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

## Deployment Options

### Option 1: Self-Hosted (Free, Open Source)

**Bring your own API keys:**
- OpenRouter account (access to 100+ models)
- Or direct: Anthropic, OpenAI, etc.

**What you get:**
✅ Full orchestration engine
✅ Intelligent routing & decomposition
✅ Quality verification (5 automated checks)
✅ Cost tracking & comparison
✅ Warning flag system
✅ Complete transparency & audit logs

**What you manage:**
- Infrastructure (Docker/cloud hosting)
- Your own API keys & usage
- Data storage & backups

**Cost:** Infrastructure only (~$10-20/month for small-medium usage)

### Option 2: Managed Premium Service (Coming Soon)

**We handle everything:**
- Infrastructure & scaling
- API key management (volume discounts passed through)
- Advanced learning system (improves with usage)
- Team collaboration features
- Priority support & SLAs

**Pricing:**
- OpenRouter costs + 10% orchestration margin
- Still 60-70% cheaper than using Opus/GPT-4 directly
- Free tier for evaluation

**Premium features:**
- Advanced analytics dashboard
- Custom routing rules
- Team workspaces
- Compliance audit trails
- Real-time processing transparency
- Enterprise SSO & security

## Response Format

**Layer 1: Simple View (default)**
```json
{
  "answer": "Your polished answer here...",
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

**Layer 2: Detailed View (expandable)**
```json
{
  "answer": "Your polished answer...",
  "orchestration": {
    "subtasks": [
      {"task": "Security analysis", "model": "claude-3-5-sonnet", "time": 12.4},
      {"task": "Performance comparison", "model": "gpt-4o", "time": 8.1},
      {"task": "Best practices", "model": "claude-3-haiku", "time": 3.8}
    ],
    "verification_checks": [
      {"type": "factual_consistency", "passed": true, "confidence": 0.87},
      {"type": "logical_coherence", "passed": true, "confidence": 0.92},
      {"type": "specificity", "passed": true, "confidence": 0.89}
    ],
    "warnings": [
      {
        "type": "model_disagreement",
        "description": "Models disagree on scalability threshold",
        "models": ["claude-3-5-sonnet", "gpt-4o"],
        "details": "Claude: bottleneck at 10k users | GPT: handles 10k+ fine"
      }
    ],
    "cost_breakdown": {
      "total": 0.03,
      "baseline": 0.14,
      "savings": 0.11
    }
  }
}
```

**Layer 3: Full Technical Report (power users)**
Complete transparency with all model responses, verification details, and routing decisions.

## Roadmap

**Open Source (Free):**
- [x] Intelligent decomposition & routing
- [x] Multi-vendor orchestration
- [x] Quality verification (5 checks)
- [x] Warning flag system
- [x] Cost tracking
- [ ] Frontend dashboard UI
- [ ] Advanced analytics

**Premium Managed Service:**
- [ ] Hosted infrastructure
- [ ] Team collaboration
- [ ] Advanced learning system
- [ ] Custom routing rules
- [ ] Real-time transparency UI
- [ ] Enterprise features (SSO, audit logs, SLAs)

---

## Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Areas we need help:**
- Frontend development (React dashboard)
- Model provider integrations
- Documentation & examples
- Testing & quality assurance

---

## License

**MIT License** - Free to use, modify, and distribute.

See [LICENSE](LICENSE) for details.

Commercial use is allowed. If you build a business on this, consider supporting via GitHub Sponsors or using our managed service.

---

## Why Open Source?

**We believe:**
- AI orchestration should be transparent and auditable
- Users should own their data and infrastructure
- The community builds better software together
- Open source proves the value before asking for payment

**Our business model:**
- Open source core = community growth + trust
- Managed service = convenience for teams/enterprises
- Everyone wins: hobbyists self-host, companies pay for managed

---

## Star History

If this project helps you, consider giving it a ⭐ on GitHub!

It helps others discover the project and motivates continued development. 
