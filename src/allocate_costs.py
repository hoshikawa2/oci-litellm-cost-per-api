from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
from typing import Any

from ledger import Ledger
from oci_usage_rest import fetch_monthly_genai_cost_rest
from settings import Env, load_config


def compute_allocations(rows: list[dict[str, Any]], total_cost: float, metric: str, input_weight: float, output_weight: float) -> list[dict[str, Any]]:
    enriched = []
    for r in rows:
        weighted_tokens = (r['input_tokens'] or 0) * input_weight + (r['output_tokens'] or 0) * output_weight
        r = dict(r)
        r['weighted_tokens'] = weighted_tokens
        enriched.append(r)

    denominator = sum(float(r[metric] or 0) for r in enriched) or 1.0
    for r in enriched:
        share = float(r[metric] or 0) / denominator
        r['allocation_metric'] = metric
        r['share_pct'] = round(share * 100, 6)
        r['allocated_cost'] = round(total_cost * share, 6)
    return enriched


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--month', help='YYYY-MM; default vem de config/apis.yaml')
    parser.add_argument('--oci-cost', type=float, help='Permite testar sem chamar OCI Usage API')
    parser.add_argument('--out', default='./storage/allocation_report.csv')
    args = parser.parse_args()

    env = Env()
    cfg = load_config(env.config_file)
    month = args.month or cfg.month
    rows = Ledger(env.ledger_db).monthly_usage(month)

    if args.oci_cost is None:
        cost_result = fetch_monthly_genai_cost_rest(month)
        total_cost = cost_result.amount
        currency = cost_result.currency or cfg.currency
        Path('./storage/oci_usage_raw.json').write_text(json.dumps(cost_result.raw, indent=2, ensure_ascii=False), encoding='utf-8')
    else:
        total_cost = args.oci_cost
        currency = cfg.currency

    allocations = compute_allocations(
        rows=rows,
        total_cost=total_cost,
        metric=cfg.allocation_metric,
        input_weight=cfg.model.input_weight,
        output_weight=cfg.model.output_weight,
    )

    fieldnames = [
        'month', 'api_id', 'api_name', 'requests', 'input_tokens', 'output_tokens', 'total_tokens',
        'weighted_tokens', 'litellm_estimated_cost', 'allocation_metric', 'share_pct', 'allocated_cost',
        'avg_latency_ms'
    ]
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open('w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in allocations:
            writer.writerow({k: r.get(k) for k in fieldnames})

    print(json.dumps({
        'month': month,
        'oci_total_cost': total_cost,
        'currency': currency,
        'allocation_metric': cfg.allocation_metric,
        'report': str(out),
        'allocations': allocations,
    }, indent=2, ensure_ascii=False))


if __name__ == '__main__':
    main()
