from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from typing import Any

from litellm.integrations.custom_logger import CustomLogger

# Este callback roda dentro do LiteLLM Proxy.
# Ele persiste um ledger local por API consumidora usando metadata enviada na chamada.
try:
    from ledger import Ledger, now_iso
except Exception:  # pragma: no cover - fallback quando import path muda no container
    from src.ledger import Ledger, now_iso

def _extract_metadata(kwargs: dict[str, Any]) -> dict[str, Any]:
    candidates = []

    candidates.append(kwargs.get("metadata"))

    litellm_params = kwargs.get("litellm_params") or {}
    candidates.append(litellm_params.get("metadata"))

    standard_logging_object = kwargs.get("standard_logging_object") or {}
    candidates.append(standard_logging_object.get("metadata"))

    proxy_server_request = kwargs.get("proxy_server_request") or {}
    candidates.append(proxy_server_request.get("metadata"))

    for candidate in candidates:
        if isinstance(candidate, dict) and candidate:
            return candidate

    return {}

def _month_from_ts(dt: datetime) -> str:
    return dt.strftime('%Y-%m')

def _json_safe(value):
    """Converte objetos não serializáveis do LiteLLM em tipos seguros para JSON."""
    if value is None:
        return None

    if isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}

    if isinstance(value, (list, tuple, set)):
        return [_json_safe(v) for v in value]

    # Pydantic / dataclass-like
    if hasattr(value, "model_dump"):
        try:
            return _json_safe(value.model_dump())
        except Exception:
            pass

    if hasattr(value, "dict"):
        try:
            return _json_safe(value.dict())
        except Exception:
            pass

    # Último fallback: vira string
    return str(value)

def _usage_get(response_obj: Any, key: str, default: int = 0) -> int:
    usage = getattr(response_obj, 'usage', None)
    if usage is None and isinstance(response_obj, dict):
        usage = response_obj.get('usage')
    if usage is None:
        return default
    if isinstance(usage, dict):
        return int(usage.get(key, default) or default)
    return int(getattr(usage, key, default) or default)


def _response_id(response_obj: Any) -> str | None:
    if isinstance(response_obj, dict):
        return response_obj.get('id')
    return getattr(response_obj, 'id', None)


class CostAllocationCallback(CustomLogger):
    async def async_log_success_event(self, kwargs, response_obj, start_time, end_time):
        metadata = _extract_metadata(kwargs)

        api_id = (
            metadata.get("api_id")
            or metadata.get("user_api_key_metadata", {}).get("api_id")
            or kwargs.get("user")
            or "unknown"
        )

        api_name = (
            metadata.get("api_name")
            or metadata.get("user_api_key_metadata", {}).get("api_name")
            or api_id
        )

        prompt_tokens = _usage_get(response_obj, 'prompt_tokens')
        completion_tokens = _usage_get(response_obj, 'completion_tokens')
        total_tokens = _usage_get(response_obj, 'total_tokens', prompt_tokens + completion_tokens)
        latency_ms = int((end_time - start_time).total_seconds() * 1000)

        # LiteLLM calcula response_cost quando conhece o modelo/preço. Para rateio final,
        # a fonte da verdade será o custo total da OCI Usage API.
        response_cost = float(kwargs.get('response_cost') or 0)

        ts = end_time if isinstance(end_time, datetime) else datetime.now(timezone.utc)
        ledger = Ledger(os.environ.get('LEDGER_DB', '/app/storage/ledger.sqlite'))

        model = (
            kwargs.get("model")
            or kwargs.get("model_name")
            or (kwargs.get("standard_logging_object") or {}).get("model")
            or (kwargs.get("response_cost_information") or {}).get("model")
            or "unknown"
        )

        safe_metadata = {
            "api_id": api_id,
            "api_name": api_name,
            "owner": metadata.get("owner"),
            "model": model,
        }

        ledger.insert_usage({
            'ts': ts.isoformat(),
            'month': _month_from_ts(ts),
            'api_id': api_id,
            'api_name': api_name,
            'virtual_key_hash': str(kwargs.get('litellm_api_key') or kwargs.get('api_key') or '')[:12],
            'model': kwargs.get('model'),
            'request_id': _response_id(response_obj),
            'prompt_tokens': prompt_tokens,
            'completion_tokens': completion_tokens,
            'total_tokens': total_tokens,
            'response_cost': response_cost,
            'latency_ms': latency_ms,
            'status': 'success',
            'metadata_json': json.dumps(safe_metadata, ensure_ascii=False),
        })


proxy_handler_instance = CostAllocationCallback()
