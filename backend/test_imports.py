"""Test that all imports work correctly"""
import sys
import traceback

def test_import(module_path, description):
    try:
        __import__(module_path)
        print(f"✓ {description}")
        return True
    except Exception as e:
        print(f"✗ {description}")
        print(f"  Error: {e}")
        traceback.print_exc()
        return False

print("Testing imports...\n")

success = True

# Core modules
success &= test_import("app.core.config", "Config")
success &= test_import("app.db.database", "Database")
success &= test_import("app.models.schemas", "Schemas")

# Services
success &= test_import("app.services.decomposer", "Decomposer")
success &= test_import("app.services.router", "Router")
success &= test_import("app.services.executor", "Executor")
success &= test_import("app.services.aggregator", "Aggregator")
success &= test_import("app.services.friction_detector", "FrictionDetector")
success &= test_import("app.services.emotional_friction_mapper", "EmotionalFrictionMapper")
success &= test_import("app.services.input_processor", "InputProcessor")
success &= test_import("app.services.orchestrator", "Orchestrator")

# API
success &= test_import("app.api.routes", "Routes")

# Main app
success &= test_import("main", "Main App")

print(f"\n{'='*50}")
if success:
    print("✓ All imports successful!")
else:
    print("✗ Some imports failed")
    sys.exit(1)
