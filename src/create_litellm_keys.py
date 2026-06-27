from __future__ import annotations

import httpx

from settings import Env, load_config


def main() -> None:
    env = Env()
    cfg = load_config(env.config_file)
    headers = {'Authorization': f'Bearer {env.litellm_master_key}'}

    with httpx.Client(timeout=30) as client:
        for api in cfg.apis:
            payload = {
                'key': api.virtual_key,
                'aliases': {cfg.model.alias: cfg.model.alias},
                'models': [cfg.model.alias],
                'metadata': {'api_id': api.id, 'api_name': api.name, 'owner': api.owner},
                'team_id': api.owner or api.id,
                'user_id': api.id,
            }
            r = client.post(f'{env.litellm_base_url.replace("/v1", "")}/key/generate', headers=headers, json=payload)
            if r.status_code in (200, 201):
                print(f'OK key criada/registrada: {api.id}')
            elif r.status_code == 400 and 'already' in r.text.lower():
                print(f'OK key já existe: {api.id}')
            else:
                print(f'ERRO {api.id}: {r.status_code} {r.text}')


if __name__ == '__main__':
    main()
