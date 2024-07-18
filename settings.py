import os
import platform

from pydantic import BaseSettings
from pydantic import validator


class TemporalClusterSettings(BaseSettings):
    host: str
    namespace: str = "default"

    class Config:
        env_prefix = "temporal_cluster_"
        case_insensitive = True


class TemporalWorkerSettings(BaseSettings):
    identity: str = None
    http_host: str
    http_port: int
    http_callback: str

    class Config:
        env_prefix = "temporal_worker_"
        case_insensitive = True

    @validator("identity")
    def validate_identity(cls, value: str) -> str:
        if not value:
            value = "worker-name"
        return f"{os.getpid()}@{platform.node()}#{value}"
