import json
import os
from typing import Any, Dict, List, Optional

from labmachine.base import DNSSpec
from labmachine.types import DNSRecord, DNSZone
from libcloud.dns.base import Record, Zone
from libcloud.dns.providers import get_driver
from libcloud.dns.types import Provider, RecordDoesNotExistError

from .common import GOOGLE_AUTH_ENV, GCConf, get_auth_conf


class GoogleDNS(DNSSpec):
    providerid = "gce"

    def __init__(self, keyvar: str = GOOGLE_AUTH_ENV):
        super().__init__(keyvar=keyvar)
        conf = get_auth_conf(env_var=keyvar)
        G = get_driver(Provider.GOOGLE)

        self._project = conf.PROJECT
        self._account = conf.SERVICE_ACCOUNT

        self.driver = G(
            conf.SERVICE_ACCOUNT,
            conf.CREDENTIALS,
            project=conf.PROJECT,
        )

    def list_zones(self) -> List[DNSZone]:
        zs = self.driver.list_zones()
        zones = [DNSZone(
            id=z.id,
            domain=z.domain,
            zone_type=z.type,
            ttl=z.ttl,
        ) for z in zs]
        return zones

    def create_zone(self, zone: DNSZone):
        z = self.driver.create_zone(
            domain=zone.domain,
            type=zone.zone_type,
            ttl=zone.ttl,
            extra=zone.extra
        )
        return z

    def get_zone(self, zoneid: str) -> DNSZone:
        z = self.driver.get_zone(zoneid)
        return self._data2zone(z)

    def delete_zone(self, zoneid: str):
        pass

    def _data2record(self, r: Record) -> DNSRecord:
        _id = f"{r.type}:{r.name}"
        return DNSRecord(
            id=_id,
            name=r.name,
            zoneid=r.zone.id,
            record_type=r.type,
            data=r.data["rrdatas"]
        )

    def _data2zone(self, z: Zone) -> DNSZone:
        return DNSZone(
            domain=z.domain,
            zone_type=z.type,
            ttl=z.ttl,
            id=z.id,
        )

    def get_record(self, zoneid: str, recordid: str) -> DNSRecord:
        r = self.driver.get_record(zoneid, recordid)
        return self._data2record(r)

    def list_records(self, zoneid: str) -> List[DNSRecord]:
        z = self.driver.get_zone(zoneid)
        rs = self.driver.list_records(z)
        records = [self._data2record(r) for r in rs]
        return records

    def create_record(self, record: DNSRecord) -> Dict[str, Any]:
        z = self.driver.get_zone(record.zoneid)
        r = self.driver.create_record(
            record.name,
            z,
            type=record.record_type,
            data={
                "rrdatas": record.data,
                "type": record.record_type,
                "ttl": record.ttl
            }
        )
        record.id = r.id
        return record.dict()

    def delete_record(self, zoneid: str, recordid: str) -> bool:
        """ "A:testlib.dymax.app."""
        try:
            r = self.driver.get_record(zoneid, recordid)
            deleted = self.driver.delete_record(r)
        except RecordDoesNotExistError:
            return False
        return deleted
