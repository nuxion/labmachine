from pydantic import BaseSettings


class CFLConf(BaseSettings):
    KEY: str

    class Config:
        env_prefix = "CLOUDFLARE_"


def get_auth_conf() -> CFLConf:
    conf = CFLConf()
    return conf
