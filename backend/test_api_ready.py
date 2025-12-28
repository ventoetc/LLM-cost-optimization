#!/usr/bin/env python3
"""Quick startup verification - checks if the system is ready to run"""
import os
import sys

def check_env_var(name, required=True):
    value = os.getenv(name)
    if value:
        masked = value[:8] + "..." if len(value) > 8 else "***"
        print(f"✓ {name}: {masked}")
        return True
    else:
        status = "✗ REQUIRED" if required else "○ Optional"
        print(f"{status} {name}: Not set")
        return not required

def check_file(path, description):
    if os.path.exists(path):
        print(f"✓ {description}: {path}")
        return True
    else:
        print(f"✗ {description}: {path} (missing)")
        return False

print("="*60)
print("LLM Cost Optimizer - Startup Verification")
print("="*60)
print()

all_good = True

print("Environment Variables:")
print("-" * 40)
all_good &= check_env_var("OPENROUTER_API_KEY", required=True)
all_good &= check_env_var("ANTHROPIC_API_KEY", required=False)
all_good &= check_env_var("OPENAI_API_KEY", required=False)
all_good &= check_env_var("DATABASE_URL", required=False)

print()
print("Required Files:")
print("-" * 40)
all_good &= check_file("main.py", "Main app")
all_good &= check_file("requirements.txt", "Dependencies")
all_good &= check_file(".env.example", "Environment template")
all_good &= check_file("Dockerfile", "Docker config")

print()
print("Core Services:")
print("-" * 40)
all_good &= check_file("app/services/decomposer.py", "Decomposer")
all_good &= check_file("app/services/router.py", "Router")
all_good &= check_file("app/services/executor.py", "Executor")
all_good &= check_file("app/services/aggregator.py", "Aggregator")
all_good &= check_file("app/services/orchestrator.py", "Orchestrator")

print()
print("="*60)
if all_good:
    print("✓ READY TO START")
    print()
    print("Start the server:")
    print("  uvicorn main:app --reload --host 0.0.0.0 --port 8000")
    print()
    print("Or use Docker:")
    print("  docker-compose up -d")
    print()
    print("API Documentation:")
    print("  http://localhost:8000/docs")
    sys.exit(0)
else:
    print("✗ NOT READY")
    print()
    if not os.getenv("OPENROUTER_API_KEY"):
        print("Missing required environment variable:")
        print("  1. Copy .env.example to .env")
        print("  2. Get API key from https://openrouter.ai")
        print("  3. Add to .env: OPENROUTER_API_KEY=your-key-here")
    print()
    sys.exit(1)
