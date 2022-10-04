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


def get_auth_conf(env_var=GOOGLE_AUTH_ENV, filepath=None) -> GCConf:
    """
    https://googleapis.dev/python/google-api-core/latest/auth.html#authentication
    """
    if filepath:
        creds_path = filepath
    else:
        creds_path = os.environ.get(env_var)
    if creds_path:
        with open(creds_path, "r") as f:
            data = json.loads(f.read())
            acc = data["client_email"]
            prj = data["project_id"]
        conf = GCConf(CREDENTIALS=creds_path,
                      PROJECT=prj,
                      SERVICE_ACCOUNT=acc)
    else:
        conf = GCConf()
    return conf
