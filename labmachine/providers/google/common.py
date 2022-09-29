import json
import os
from typing import Any, Dict, Optional

from pydantic import BaseSettings


GOOGLE_AUTH_ENV = "GOOGLE_APPLICATION_CREDENTIALS"

class GCConf(BaseSettings):
    """
    :param CREDENTIALS: credential file open by python
    :param PROJECT: projectid
    :param LOCATION: region/zone
    :param SERVICE_ACCOUNT: client_email

    """
    CREDENTIALS: str
    PROJECT: str
    LOCATION: Optional[str] = None
    SERVICE_ACCOUNT: Optional[str] = None

    class Config:
        env_prefix = "GCE_"


def get_auth_conf(env_var=GOOGLE_AUTH_ENV) -> GCConf:
    """
    https://googleapis.dev/python/google-api-core/latest/auth.html#authentication
    """
    creds_env = os.environ.get(env_var)
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
