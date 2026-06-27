#!/usr/bin/env bash
set -euo pipefail

cp -n .env.example .env || true
mkdir -p storage

echo '1) Subindo Postgres + LiteLLM Proxy...'
docker compose up -d

echo '2) Registrando virtual keys por API consumidora...'
python src/create_litellm_keys.py

echo '3) Subindo simulador de APIs na porta 8080...'
uvicorn src.api_service:app --host 0.0.0.0 --port 8080
