from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Env(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')

    litellm_base_url: str = 'http://localhost:4000/v1'
    litellm_master_key: str = 'sk-master-poc'
    litellm_model_alias: str = 'oci-gemini-25-pro'
    ledger_db: str = './storage/ledger.sqlite'
    config_file: str = './config/apis.yaml'

    oci_usage_endpoint: str = 'https://usageapi.us-ashburn-1.oci.oraclecloud.com'
    oci_usage_api_version: str = '20200107'
    oci_usage_service_filter: str = 'generative_ai'
    oci_usage_product_filter: str | None = None


class ApiDef(BaseModel):
    id: str
    name: str
    virtual_key: str
    owner: str | None = None


class ModelDef(BaseModel):
    alias: str
    oci_model_name: str
    input_weight: float = 1.0
    output_weight: float = 5.0


class AppConfig(BaseModel):
    month: str
    allocation_metric: Literal['weighted_tokens', 'total_tokens', 'requests'] = 'weighted_tokens'
    currency: str = 'USD'
    model: ModelDef
    apis: list[ApiDef] = Field(default_factory=list)


def load_config(path: str | Path) -> AppConfig:
    with open(path, 'r', encoding='utf-8') as f:
        return AppConfig.model_validate(yaml.safe_load(f))
