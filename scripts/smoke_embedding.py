import os
from app.embedding import embed_text, load_config

if __name__ == "__main__":
    # Non stampare testo, solo metadati + primi valori
    cfg = load_config()
    vec, model, dim = embed_text("smoke")
    print(f"provider={cfg.provider} model={model} dim={dim} v0..2={vec[:3]}")