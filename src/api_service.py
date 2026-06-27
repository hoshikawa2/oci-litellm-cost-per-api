from __future__ import annotations

import random
import time
from typing import Any

from fastapi import FastAPI, Header, HTTPException
from openai import OpenAI
from pydantic import BaseModel

from settings import Env, load_config


env = Env()
config = load_config(env.config_file)
api_by_id = {a.id: a for a in config.apis}

app = FastAPI(title='LLM Consumer API Simulator')


class PromptRequest(BaseModel):
    prompt: str | None = None
    max_tokens: int = 256


def client_for(api_id: str) -> OpenAI:
    api_def = api_by_id.get(api_id)
    if not api_def:
        raise HTTPException(status_code=404, detail=f'API {api_id} não cadastrada em {env.config_file}')
    return OpenAI(api_key=api_def.virtual_key, base_url=env.litellm_base_url)


@app.get('/apis')
def list_apis() -> list[dict[str, Any]]:
    return [a.model_dump(exclude={'virtual_key'}) for a in config.apis]


@app.post('/apis/{api_id}/ask')
def ask(api_id: str, body: PromptRequest, x_request_id: str | None = Header(default=None)) -> dict[str, Any]:
    api_def = api_by_id.get(api_id)
    if not api_def:
        raise HTTPException(status_code=404, detail='api_id inválido')

    prompt = body.prompt or f'Responda em uma frase: qual é uma boa métrica para FinOps de LLM? rand={random.randint(1, 9999)}'
    t0 = time.perf_counter()
    response = client_for(api_id).chat.completions.create(
        model=config.model.alias,
        messages=[
            {'role': 'system', 'content': 'Você é um assistente técnico objetivo.'},
            {'role': 'user', 'content': prompt},
        ],
        max_tokens=body.max_tokens,
        metadata={
            'api_id': api_def.id,
            'api_name': api_def.name,
            'owner': api_def.owner,
            'external_request_id': x_request_id,
        },
    )
    elapsed_ms = int((time.perf_counter() - t0) * 1000)
    usage = response.usage.model_dump() if response.usage else {}
    return {
        'api_id': api_id,
        'model': config.model.alias,
        'latency_ms': elapsed_ms,
        'usage': usage,
        'answer': response.choices[0].message.content,
    }
