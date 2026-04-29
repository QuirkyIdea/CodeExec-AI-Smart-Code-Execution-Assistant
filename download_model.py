import os
from huggingface_hub import snapshot_download, login
from pathlib import Path

# Login using the provided API key
login(token="your_huggingface_token_here")

mistral_models_path = Path.home().joinpath('mistral_models', '7B-Instruct-v0.3')
mistral_models_path.mkdir(parents=True, exist_ok=True)

print(f"Downloading Mistral-7B-Instruct-v0.3 to {mistral_models_path}...")
try:
    snapshot_download(
        repo_id="mistralai/Mistral-7B-Instruct-v0.3",
        allow_patterns=["params.json", "consolidated.safetensors", "tokenizer.model.v3"],
        local_dir=mistral_models_path
    )
    print("Download complete!")
except Exception as e:
    print(f"Error during download: {e}")
