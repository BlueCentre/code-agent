import os
from pathlib import Path

import yaml

# Try to use the API key from environment variable first
api_key = os.environ.get("AI_STUDIO_API_KEY")

if not api_key:
    # If not in env var, try to read from config
    config_path = Path.home() / ".config" / "code-agent" / "config.yaml"
    if config_path.exists():
        try:
            with open(config_path, "r") as f:
                config = yaml.safe_load(f)
                if (
                    config
                    and "api_keys" in config
                    and "ai_studio" in config["api_keys"]
                ):
                    api_key = config["api_keys"]["ai_studio"]
        except Exception as e:
            print(f"Error reading config: {e}")

if not api_key:
    print("Could not find AI Studio API key in environment variables or config file.")
    print(
        "Please set AI_STUDIO_API_KEY environment variable or add it to ~/.config/code-agent/config.yaml"
    )
    exit(1)

# Now use the API key to check available models
print("Found AI Studio API key. Testing connection and checking available models...")

try:
    import google.generativeai as genai

    # Configure the API key
    genai.configure(api_key=api_key)

    # List available models
    models = genai.list_models()

    print("\nAvailable Gemini models:")
    gemini_models = []
    for model in models:
        if "gemini" in model.name.lower():
            model_name = model.name.split("/")[
                -1
            ]  # Extract just the model name from the full path
            gemini_models.append(model_name)
            supported_methods = [
                method.split(".")[-1] for method in model.supported_generation_methods
            ]
            print(f"- {model_name} (Supported methods: {', '.join(supported_methods)})")

    # Check specifically for the model mentioned in the error
    target_model = "gemini-2.5.pro-exp-03-25"
    if any(target_model in model for model in gemini_models):
        print(f"\n✅ The model '{target_model}' IS available with your API key.")
    else:
        print(f"\n❌ The model '{target_model}' is NOT available with your API key.")
        print(
            "This suggests the model name might be incorrect or the model is not yet accessible with your account."
        )
        print(
            "The model might be part of an early access program or might have been renamed."
        )

        # Suggest similar models
        print("\nSimilar available models that might work:")
        for model in gemini_models:
            if "gemini-2.5" in model:
                print(f"- {model}")

        print(
            "\nRecommendation: Try using 'gemini-2.0-pro' or one of the available gemini-2.5 models instead."
        )

except Exception as e:
    print(f"Error checking models: {e}")
    print(
        "\nThis could indicate an authentication issue with your API key or a network/service problem."
    )
