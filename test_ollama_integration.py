#!/usr/bin/env python3
"""
Ollama Integration Test for QuantMuse
Tests the new OllamaProvider implementation
"""

import sys
import os
import json
import logging

# Add the data_service to Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'data_service'))

from ai.llm_integration import LLMIntegration, OllamaProvider

def test_ollama_provider():
    """Test OllamaProvider directly"""
    print("Testing OllamaProvider directly...")

    try:
        # Initialize Ollama provider with user's configuration
        provider = OllamaProvider(
            model="gpt-oss:20b",
            base_url="http://10.227.135.97:11434"
        )

        print(f"✓ OllamaProvider initialized with model: {provider.model}")
        print(f"✓ Base URL: {provider.base_url}")

        # Get model info
        model_info = provider.get_model_info()
        print(f"✓ Model info: {model_info}")

        # List available models
        models = provider.list_available_models()
        print(f"✓ Available models: {len(models)} models found")
        for model in models:
            print(f"  - {model.get('name', 'Unknown')}: {model.get('size', 'Unknown size')}")

        # Test simple generation
        test_prompt = "Hello, can you introduce yourself briefly?"
        print(f"\nTesting generation with prompt: '{test_prompt}'")

        response = provider.generate_response(
            test_prompt,
            temperature=0.7,
            max_tokens=100
        )

        print("✓ Response received:")
        print(f"  Content: {response.content[:200]}...")
        print(f"  Confidence: {response.confidence}")
        print(f"  Model used: {response.model_used}")
        print(f"  Tokens used: {response.tokens_used}")

        return True

    except Exception as e:
        print(f"✗ OllamaProvider test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_llm_integration():
    """Test LLMIntegration with Ollama"""
    print("\nTesting LLMIntegration with Ollama...")

    try:
        # Initialize LLM integration with Ollama
        llm = LLMIntegration(
            provider="ollama",
            model="gpt-oss:20b",
            base_url="http://10.227.135.97:11434"
        )

        print("✓ LLMIntegration initialized with Ollama")
        # Get provider info
        provider_info = llm.get_provider_info()
        print(f"✓ Provider info: {provider_info}")

        # Test simple question
        question = "What is quantitative trading in simple terms?"
        print(f"\nTesting question: '{question}'")

        response = llm.answer_trading_question(question)
        print("✓ Response received:")
        print(f"  Content: {response.content[:200]}...")
        print(f"  Confidence: {response.confidence}")
        print(f"  Model used: {response.model_used}")

        return True

    except Exception as e:
        print(f"✗ LLMIntegration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_configuration_loading():
    """Test loading configuration with Ollama settings"""
    print("\nTesting configuration loading...")

    try:
        config_path = "config.example.json"

        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)

            ai_config = config.get('ai', {})
            ollama_config = ai_config.get('ollama', {})

            print(f"✓ Configuration loaded: {ai_config.get('llm_provider', 'Unknown')}")
            print(f"✓ Ollama base_url: {ollama_config.get('base_url', 'Not set')}")
            print(f"✓ Ollama model: {ollama_config.get('model', 'Not set')}")

            return True
        else:
            print(f"✗ Configuration file not found: {config_path}")
            return False

    except Exception as e:
        print(f"✗ Configuration loading failed: {e}")
        return False

def main():
    """Main test function"""
    print("🔧 QuantMuse Ollama Integration Test")
    print("=" * 50)

    # Setup logging
    logging.basicConfig(level=logging.INFO)

    # Run tests
    tests = [
        ("Configuration Loading", test_configuration_loading),
        ("OllamaProvider Direct Test", test_ollama_provider),
        ("LLMIntegration Test", test_llm_integration)
    ]

    results = []

    for test_name, test_func in tests:
        print(f"\n{'='*20} {test_name} {'='*20}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"✗ {test_name} crashed: {e}")
            results.append((test_name, False))

    # Summary
    print(f"\n{'='*50}")
    print("📊 TEST SUMMARY")
    print(f"{'='*50}")

    passed = 0
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if result:
            passed += 1

    print(f"\nOverall: {passed}/{len(results)} tests passed")

    if passed == len(results):
        print("🎉 All tests passed! Ollama integration is working correctly.")
        return 0
    else:
        print("⚠️  Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)