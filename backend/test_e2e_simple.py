"""Simple end-to-end test of the orchestration system"""
import asyncio
import sys
import os

# Set a mock API key for testing
os.environ['OPENROUTER_API_KEY'] = 'sk-test-key-for-structure-validation'
os.environ['DATABASE_URL'] = 'sqlite+aiosqlite:///:memory:'

async def test_basic_flow():
    """Test the basic orchestration flow"""
    print("Testing basic orchestration flow...\n")

    try:
        # Import after setting env vars
        from app.db.database import init_db, async_session_maker
        from app.services.orchestrator import Orchestrator
        from app.models.schemas import ExecutionRequest

        # Initialize database
        print("✓ Initializing in-memory database...")
        await init_db()

        # Create a test request
        test_prompt = "Explain how photosynthesis works in simple terms"
        print(f"✓ Test prompt: '{test_prompt}'")

        # Create session and orchestrator
        async with async_session_maker() as session:
            print("✓ Created database session")

            orchestrator = Orchestrator(session)
            print("✓ Created orchestrator")

            # Test decomposer alone first
            print("\n--- Testing Decomposer ---")
            decomposition = await orchestrator.decomposer.decompose(test_prompt)
            print(f"✓ Decomposed into {len(decomposition.subtasks)} subtask(s)")
            for i, subtask in enumerate(decomposition.subtasks):
                print(f"  Task {i+1}: {subtask.description[:50]}...")
                print(f"    Type: {subtask.task_type}, Complexity: {subtask.estimated_complexity:.2f}")

            # Test router
            print("\n--- Testing Router ---")
            for subtask in decomposition.subtasks:
                model = await orchestrator.router.route_task(subtask)
                print(f"✓ Routed to: {model}")
                subtask.assigned_model = model

            print("\n--- Full System Test ---")
            print("NOTE: This will fail when trying to call OpenRouter API")
            print("      (Expected - we're using a fake API key)")
            print("      The test validates structure, not actual execution.\n")

            # Try full execution (will fail at API call, but structure will be validated)
            try:
                request = ExecutionRequest(
                    prompt=test_prompt,
                    user_id="test-user"
                )

                result = await orchestrator.execute_request(request)
                print("✓ Full orchestration completed!")
                print(f"  Request ID: {result.request_id}")
                print(f"  Total cost: ${result.total_cost:.4f}")
                print(f"  Baseline cost: ${result.baseline_cost:.4f}")
                print(f"  Savings: {result.cost_savings_percent:.1f}%")

            except Exception as e:
                error_msg = str(e)
                if "401" in error_msg or "Authorization" in error_msg or "API" in error_msg:
                    print("✓ Structure validated - failed at OpenRouter API call (expected)")
                    print(f"  Error: {error_msg[:100]}...")
                else:
                    print(f"✗ Unexpected error: {error_msg}")
                    raise

        print("\n" + "="*60)
        print("✓ Basic structure test PASSED")
        print("="*60)
        print("\nTo test with real API:")
        print("  1. Get OpenRouter API key from https://openrouter.ai")
        print("  2. Set: export OPENROUTER_API_KEY='your-key'")
        print("  3. Run: uvicorn main:app --reload")
        print("  4. Test with: curl -X POST http://localhost:8000/api/v1/execute \\")
        print("       -H 'Content-Type: application/json' \\")
        print("       -d '{\"prompt\": \"Test query\", \"user_id\": \"test\"}'")

        return True

    except Exception as e:
        print(f"\n✗ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_basic_flow())
    sys.exit(0 if success else 1)
