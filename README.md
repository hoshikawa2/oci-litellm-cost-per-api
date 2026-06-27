
# OCI Generative AI Cost Allocation per API using LiteLLM


## Overview

Organizations commonly expose a single OCI Generative AI endpoint to dozens or hundreds of internal APIs and AI Agents.

Although OCI provides consolidated billing information for Generative AI consumption, it does **not** provide an out-of-the-box cost breakdown by individual application or API.

This project solves that problem.

By introducing LiteLLM Proxy between the applications and OCI Generative AI, every request can be attributed to a specific API, while the official monthly OCI cost is collected through the OCI Usage REST API and proportionally allocated back to each consumer.

The result is an accurate chargeback/showback model without changing the existing applications.

---

## Business Use Case

Typical enterprise scenario:

- Multiple REST APIs
- AI Agents
- LangGraph applications
- MCP Servers
- RAG services

all consume the same OCI Generative AI endpoint.

Finance receives only the total monthly OCI invoice.

Engineering needs answers such as:

- Which API generated the highest cost?
- Which squad consumed the most tokens?
- Which application should optimize prompts?
- How much does each business unit owe?

Thi material answers those questions.

---

## Architecture

Applications -> LiteLLM Proxy -> OCI Generative AI

LiteLLM records detailed token usage per virtual key/API.

OCI Usage API provides the official monthly cost.

The allocation engine proportionally distributes the OCI invoice according to measured consumption.

---

## Why LiteLLM?

LiteLLM provides several capabilities particularly useful in OCI environments:

- Unified OpenAI-compatible endpoint
- Multiple LLM providers behind a single API
- Virtual API Keys
- Callbacks
- Usage tracking
- Authentication abstraction
- Gateway functionality
- Rate limiting
- Budget enforcement
- Model routing
- Observability integration

This makes LiteLLM an ideal component for enterprise cost attribution.

---

## Cost Allocation Strategy

The project intentionally **does not** trust LiteLLM estimated prices.

Instead:

1. LiteLLM measures usage.
2. OCI Usage API provides the official invoice amount.
3. The invoice is proportionally distributed.

Formula:

```
weighted_tokens =
input_tokens × input_weight +
output_tokens × output_weight

share =
weighted_tokens(API)
/ weighted_tokens(all APIs)

allocated_cost =
share × official OCI monthly cost
```

---

## Integration with OCI Usage REST API

The allocation job authenticates using OCI Request Signing and queries the Usage API.

Returned information includes:

- Monthly cost
- SKU
- Service
- Currency
- Usage period

The value becomes the source of truth.

---

## Components

## LiteLLM Proxy

Acts as enterprise LLM Gateway.

Responsibilities:

- forwards requests to OCI
- authenticates
- tracks usage
- executes callbacks
- stores request metadata

## Custom Callback

Captures every request and stores:

- API identifier
- request count
- latency
- input tokens
- output tokens
- total tokens

## SQLite Ledger

Stores the local consumption ledger used for allocation.

## Allocation Engine

Reads:

- Ledger
- OCI Usage API

Produces:

- proportional cost allocation

## API Service

Simple REST service used to simulate multiple APIs.

## Load Simulator

Generates concurrent traffic for validation.

---

## Repository Structure

```
config/
    apis.yaml
    litellm_config.yaml
    genai.pem

src/
    api_service.py
    custom_callbacks.py
    ledger.py
    allocate_costs.py
    simulate_load.py
    create_litellm_keys.py
    oci_usage_rest.py
    settings.py

storage/
scripts/
docker-compose.yml
requirements.txt
```

---

## Configuration Files

## .env

Contains environment configuration.

Important parameters include:

- OCI credentials
- LiteLLM endpoint
- Usage API endpoint
- database path

## config/apis.yaml

Defines:

- monitored APIs
- owners
- virtual keys
- allocation metric
- model alias
- token weights

## config/litellm_config.yaml

LiteLLM Proxy configuration.

Includes:

- exposed models
- OCI provider
- callbacks
- authentication
- master key
- database

---

## Source Files

### allocate_costs.py

Performs monthly allocation.

### oci_usage_rest.py

Consumes OCI Usage REST API using OCI request signing.

### custom_callbacks.py

Receives LiteLLM callback events.

### ledger.py

Persists local usage statistics.

### api_service.py

REST service representing client APIs.

### simulate_load.py

Generates concurrent traffic.

### create_litellm_keys.py

Creates LiteLLM virtual keys.

### settings.py

Centralizes application configuration.

---

## Running the Project

### 1. Create Python environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure

```
cp .env.example .env
```

Fill OCI credentials.

### 3. Start infrastructure

```
docker compose up -d
```

### 4. Create LiteLLM keys

```
python src/create_litellm_keys.py
```

### 5. Start API service

```
PYTHONPATH=src uvicorn api_service:app --host 0.0.0.0 --port 8080
```

### 6. Generate traffic

```
python src/simulate_load.py

or

python src/simulate_load.py --calls 30 --concurrency 5
```

### 7. Allocate costs


This command will calculate the total cost came from OCI Billing API:

```
python src/allocate_costs.py --month 2026-06
```

But, if you have the total cost or want to simmulate, you can run:

```
python src/allocate_costs.py --month 2026-06 --oci-cost 1234.56
```

---

## Expected Result

The report shows, for every API:

- Requests
- Input Tokens
- Output Tokens
- Weighted Tokens
- Consumption Percentage
- Allocated OCI Cost

```json
{
  "period": {
    "start": "2026-06-01T00:00:00Z",
    "end": "2026-06-30T23:59:59Z"
  },
  "provider": "OCI Generative AI",
  "currency": "USD",
  "summary": {
    "total_requests": 152394,
    "total_input_tokens": 38952800010,
    "total_output_tokens": 12855660000,
    "estimated_llm_cost_usd": 812.47,
    "official_oci_cost_usd": 816.31,
    "difference_usd": -3.84,
    "difference_percent": -0.47
  },
  "apis": [
    {
      "api_name": "customer-api",
      "requests": 52340,
      "input_tokens": 15400230000,
      "output_tokens": 4923400000,
      "estimated_cost_usd": 312.55,
      "percentage": 38.47,
      "models": [
        {
          "model": "cohere.command-r-plus",
          "requests": 41220,
          "cost_usd": 221.73
        },
        {
          "model": "llama-3.3-70b-instruct",
          "requests": 11120,
          "cost_usd": 90.82
        }
      ]
    },
    {
      "api_name": "billing-api",
      "requests": 48213,
      "input_tokens": 12398300000,
      "output_tokens": 3983200000,
      "estimated_cost_usd": 256.19,
      "percentage": 31.53,
      "models": [
        {
          "model": "cohere.command-r-plus",
          "requests": 48213,
          "cost_usd": 256.19
        }
      ]
    },
    {
      "api_name": "orders-api",
      "requests": 31844,
      "input_tokens": 7564200000,
      "output_tokens": 2845100000,
      "estimated_cost_usd": 171.34,
      "percentage": 21.09,
      "models": [
        {
          "model": "llama-3.3-70b-instruct",
          "requests": 31844,
          "cost_usd": 171.34
        }
      ]
    },
    {
      "api_name": "search-api",
      "requests": 19997,
      "input_tokens": 3600080010,
      "output_tokens": 1103966000,
      "estimated_cost_usd": 72.39,
      "percentage": 8.91,
      "models": [
        {
          "model": "gemma-3-27b-it",
          "requests": 19997,
          "cost_usd": 72.39
        }
      ]
    }
  ],
  "billing_validation": {
    "oci_usage_api": {
      "cost_usd": 816.31,
      "currency": "USD"
    },
    "litellm_estimation": {
      "cost_usd": 812.47
    },
    "status": "MATCH_WITHIN_THRESHOLD"
  },
  "generated_at": "2026-06-30T23:59:59Z"
}
```

---

## Reference Documentation

Oracle Cloud

- [OCI Generative AI](https://docs.oracle.com/en-us/iaas/Content/generative-ai/home.htm)
- [OCI Usage API](https://docs.oracle.com/en-us/iaas/Content/pl-sql-sdk/doc/usage-api-package.html)
- [OCI Request Signing](https://docs.oracle.com/en-us/iaas/Content/API/Concepts/usingapi.htm)
- [OCI SDK for Python](https://docs.oracle.com/en-us/iaas/Content/API/SDKDocs/pythonsdk.htm)

LiteLLM

- [LiteLLM Documentation](https://docs.litellm.ai/docs/)
- [LiteLLM Proxy](https://docs.litellm.ai/docs/providers/litellm_proxy)
- [LiteLLM Callbacks](https://docs.litellm.ai/docs/observability/callbacks)
- [LiteLLM Budget Management](https://docs.litellm.ai/docs/proxy/users)
- [LiteLLM Token Usage & Cost](https://docs.litellm.ai/docs/completion/token_usage)
---

## Conclusion

This material demonstrates a practical enterprise architecture for implementing cost visibility over OCI Generative AI.

Instead of relying on estimated model pricing, it combines precise request-level telemetry from LiteLLM with the official OCI billing information, enabling transparent chargeback and showback across APIs, business units and AI platforms.

The approach is lightweight, provider-independent inside OCI Generative AI, and can easily evolve into a production-ready FinOps solution.

---

## Disclaimer

>**IMPORTANT**: The source code must be used at your own risk. There is no support and/or link with any company. The source code is free to modify and was built solely for the purpose of helping the community

---

## Acknowledgments

- **Author** - Cristiano Hoshikawa (Oracle LAD A-Team Solution Engineer)