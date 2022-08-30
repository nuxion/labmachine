import json
import os
from typing import Any, Dict, Optional
from labmachine import defaults
from pydantic import BaseSettings


class GCConf(BaseSettings):
    CREDENTIALS: str
    PROJECT: str
    LOCATION: Optional[str] = None
    SERVICE_ACCOUNT: Optional[str] = None

    class Config:
        env_prefix = "GCE_"


def get_auth_conf() -> GCConf:
    creds_env = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_env:
        with open(creds_env, "r") as f:
            data = json.loads(f.read())
            acc = data["client_email"]
            prj = data["project_id"]
        conf = GCConf(CREDENTIALS=creds_env,
                      PROJECT=prj,
                      SERVICE_ACCOUNT=acc)
    else:
        conf = GCConf()
    return conf
