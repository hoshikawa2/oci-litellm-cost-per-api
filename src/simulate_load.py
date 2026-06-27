from __future__ import annotations

import argparse
import asyncio
import random
from uuid import uuid4

import httpx

from settings import Env, load_config


PROMPTS = [
    'Explique em uma frase o que é rateio de custo de LLM.',
    'Gere uma resposta curta para cliente perguntando segunda via de fatura.',
    'Classifique a intenção: quero trocar meu plano de internet.',
    'Resuma em tópicos uma política de uso responsável de IA.',
    'Dê 3 métricas para monitorar consumo de tokens por API.',
]


async def call_one(client: httpx.AsyncClient, base_url: str, api_id: str) -> None:
    prompt = random.choice(PROMPTS) + f' request={uuid4()}'
    try:
        r = await client.post(
            f'{base_url}/apis/{api_id}/ask',
            headers={'x-request-id': str(uuid4())},
            json={'prompt': prompt, 'max_tokens': random.choice([64, 128, 256])},
        )
        print(api_id, r.status_code, r.json().get('usage'))
    except Exception as e:
        print(api_id, 'ERROR', repr(e))


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument('--calls', type=int, default=30)
    parser.add_argument('--concurrency', type=int, default=5)
    parser.add_argument('--api-base', default='http://localhost:8080')
    args = parser.parse_args()

    env = Env()
    cfg = load_config(env.config_file)
    api_ids = [a.id for a in cfg.apis]
    sem = asyncio.Semaphore(args.concurrency)

    async with httpx.AsyncClient(timeout=180) as client:
        async def guarded(i: int) -> None:
            async with sem:
                await call_one(client, args.api_base, random.choice(api_ids))
        await asyncio.gather(*(guarded(i) for i in range(args.calls)))


if __name__ == '__main__':
    asyncio.run(main())
