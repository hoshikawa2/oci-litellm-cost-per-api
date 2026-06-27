from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from typing import Any

import oci
import requests
from oci.config import from_file
from oci.signer import Signer

from settings import Env


@dataclass
class OciCostResult:
    amount: float
    currency: str
    raw: dict[str, Any]


def _make_signer() -> Signer:
    cfg = from_file()
    return Signer(
        tenancy=cfg['tenancy'],
        user=cfg['user'],
        fingerprint=cfg['fingerprint'],
        private_key_file_location=cfg['key_file'],
        pass_phrase=cfg.get('pass_phrase'),
    )


def _iso_z(d: date) -> str:
    return datetime(d.year, d.month, d.day, tzinfo=timezone.utc).isoformat().replace('+00:00', 'Z')


def fetch_monthly_genai_cost_rest(month: str) -> OciCostResult:
    """Consulta a OCI Usage API via REST assinado.

    month: YYYY-MM

    Observação: em alguns tenancies o nome exato de service/productDescription pode variar.
    Ajuste OCI_USAGE_SERVICE_FILTER e OCI_USAGE_PRODUCT_FILTER no .env conforme a saída real.
    """
    env = Env()
    year, mon = [int(x) for x in month.split('-')]
    start = date(year, mon, 1)
    end = date(year + (mon == 12), 1 if mon == 12 else mon + 1, 1)

    endpoint = env.oci_usage_endpoint.rstrip('/')
    url = f'{endpoint}/{env.oci_usage_api_version}/usage'

    # RequestSummarizedUsagesDetails. A granularidade mensal reduz ruído de hora/dia.
    # GroupBy opcional ajuda a auditar qual produto/sku veio na resposta.
    payload: dict[str, Any] = {
        'tenantId': from_file()['tenancy'],
        'timeUsageStarted': _iso_z(start),
        'timeUsageEnded': _iso_z(end),
        'granularity': 'MONTHLY',
        'queryType': 'COST',
        'groupBy': ['service', 'productDescription'],
        'isAggregateByTime': True,
    }

    filters: list[dict[str, Any]] = []
    if env.oci_usage_service_filter:
        filters.append({'dimension': 'service', 'operator': 'CONTAINS', 'value': env.oci_usage_service_filter})
    if env.oci_usage_product_filter:
        filters.append({'dimension': 'productDescription', 'operator': 'CONTAINS', 'value': env.oci_usage_product_filter})
    if filters:
        payload['filter'] = {'operator': 'AND', 'dimensions': filters}

    r = requests.post(url, auth=_make_signer(), headers={'content-type': 'application/json'}, data=json.dumps(payload), timeout=60)
    r.raise_for_status()
    data = r.json()

    # OCI pode retornar itens em data/items dependendo do cliente/endpoint/revisão.
    items = data.get('items') or data.get('data') or []
    amount = 0.0
    currency = 'USD'
    for item in items:
        amount += float(item.get('computedAmount') or item.get('cost') or item.get('amount') or 0)
        currency = item.get('currency') or item.get('currencyCode') or currency

    return OciCostResult(amount=amount, currency=currency, raw=data)
