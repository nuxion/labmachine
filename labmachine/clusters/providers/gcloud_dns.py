import json
import os
from typing import Any, Dict, Optional

from labmachine.clusters.base import DNSSpec
from labmachine.clusters.types import DNSRecord, DNSTypeA, DNSZone
from libcloud.dns.providers import get_driver
from libcloud.dns.types import Provider
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


class GoogleDNS(DNSSpec):
    providerid = "gce-dns"

    def __init__(self):
        conf = get_auth_conf()
        G = get_driver(Provider.GOOGLE)
        # _env_creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        # if _env_creds:
        #     conf.credential_file = _env_creds
        self._project = conf.PROJECT
        self._account = conf.SERVICE_ACCOUNT

        self.driver = G(
            conf.SERVICE_ACCOUNT,
            conf.CREDENTIALS,
            project=conf.PROJECT,
        )

    def create_zone(self, zone: DNSZone):
        z = self.driver.create_zone(
            domain=zone.domain,
            type=zone.zone_type,
            ttl=zone.ttl,
            extra=zone.extra
        )
        return z

    def delete_zone(self, zoneid: str):
        pass

    def get_record(self, zoneid: str, recordid: str) -> DNSRecord:
        r = self.driver.get_record(zoneid, recordid)
        data = None
        if r.type == "A":
            data = DNSTypeA(
                address=r.data["rrdatas"][0]
            )

        return DNSRecord(
            name=r.name,
            zoneid=r.zone.id,
            record_type=r.type

        )

    def create_record(self, record: DNSRecord) -> Dict[str, Any]:
        z = self.driver.get_zone(record.zoneid)
        r = self.driver.create_record(
            record.name,
            z,
            type=record.record_type,
            data={
                "rrdatas": record.name,
                "type": record.record_type,
                "ttl": record.ttl
            }
        )
        return r.data

    def delete_record(self, zoneid: str, recordid: str) -> bool:
        r = self.driver.get_record(zoneid, recordid)
        deleted = self.driver.delete_record(r)
        return deleted
