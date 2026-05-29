"""Test script to verify all LLM providers"""
import asyncio
import os
import sys

# Add parent to path
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

# Load API keys BEFORE importing providers
from core import load_env  # This loads the API keys
from core.llm_providers import get_provider


async def test_provider(name: str):
    """Test a single provider"""
    print(f"\n{'='*50}")
    print(f"Testing {name.upper()}")
    print("=" * 50)

    try:
        provider = get_provider(name)
        if not provider:
            print(f"âŒ Provider {name} not found")
            return False

        print(f"âœ“ Provider loaded: {provider.name}")

        # Test generation
        result = await provider.generate(
            "Di 'hola' en una palabra", temperature=0.5, max_tokens=50
        )

        if result["success"]:
            print(f"âœ“ Response: {result['response'][:100]}")
            return True
        else:
            print(f"âŒ Error: {result.get('error', 'Unknown error')}")
            return False
    except Exception as e:
        print(f"âŒ Exception: {str(e)}")
        return False


async def main():
    """Test all providers"""
    providers = ["ollama", "gemini", "grok", "qwen"]
    results = {}

    print("\nðŸ”§ TESTING ALL LLM PROVIDERS\n")

    for provider_name in providers:
        results[provider_name] = await test_provider(provider_name)
        await asyncio.sleep(1)  # Brief pause between tests

    # Summary
    print(f"\n{'='*50}")
    print("SUMMARY")
    print("=" * 50)

    for name, success in results.items():
        status = "âœ… Working" if success else "âŒ Failed"
        print(f"{name.capitalize():10} : {status}")

    all_working = all(results.values())
    if all_working:
        print("\nðŸŽ‰ All providers working!")
    else:
        print("\nâš ï¸ Some providers failed")


if __name__ == "__main__":
    asyncio.run(main())
