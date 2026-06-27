# PoC - Rateio de custo OCI Generative AI via LiteLLM

Objetivo: simular várias APIs consumindo Gemini via OCI Generative AI por meio do LiteLLM Proxy, registrar uso por API e ratear o custo total mensal retornado pela OCI Usage API.

## Fluxo

1. Cada API consumidora chama o LiteLLM com uma virtual key própria.
2. O request também envia `metadata.api_id` e `metadata.api_name`.
3. Um callback do LiteLLM grava o uso em SQLite: input tokens, output tokens, total tokens, custo estimado LiteLLM e latência.
4. O job `allocate_costs.py` busca o custo mensal total na OCI Usage API via REST assinado.
5. O custo OCI é rateado proporcionalmente pelo consumo registrado no LiteLLM.

## Rodar

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# edite .env com OCI_REGION, OCI_COMPARTMENT_ID e credenciais OCI

docker compose up -d
python src/create_litellm_keys.py
PYTHONPATH=src uvicorn api_service:app --host 0.0.0.0 --port 8080
```

Em outro terminal:

```bash
python src/simulate_load.py --calls 30 --concurrency 5
python src/allocate_costs.py --month 2026-06 --oci-cost 1234.56
```

Para usar a OCI de verdade, remova `--oci-cost`:

```bash
python src/allocate_costs.py --month 2026-06
```

## Ajustes importantes

- `config/apis.yaml`: cadastro das APIs, virtual keys, dono/squad e pesos de token.
- `config/litellm_config.yaml`: modelo OCI exposto como alias `oci-gemini-25-pro`.
- `.env`: credenciais OCI, endpoint da Usage API, filtros de custo e banco local.

## Fórmula padrão

```text
weighted_tokens = input_tokens * input_weight + output_tokens * output_weight
share_api = weighted_tokens_api / sum(weighted_tokens_todas_apis)
allocated_cost_api = oci_total_monthly_cost * share_api
```

Para PoC, `input_weight=1` e `output_weight=5`. Ajuste conforme a tabela de preço efetiva do produto/SKU Gemini no contrato/OCI.
