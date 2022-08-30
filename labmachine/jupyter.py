import json
import os
import secrets
from typing import List, Optional

from pydantic import BaseModel

from labmachine import defaults, utils
from labmachine.base import DNSSpec, ProviderSpec
from labmachine.types import (AttachStorage, BlockStorage, BootDiskRequest,
                              DNSRecord, DNSZone, InstanceType, StorageRequest,
                              VMInstance, VMRequest)


def find_gce(prov: ProviderSpec, ram: int, cpu: str, gpu="") \
        -> List[InstanceType]:
    sizes = prov.driver.list_sizes(location=prov._location)
    node_types = []
    for s in sizes:
        wanted = float(ram) * 1024
        if float(s.ram) >= wanted and s.ram <= wanted + 1024 \
           and s.extra["guestCpus"] >= cpu:
            try:
                price = float(s.price)
            except:
                price = -1.
            node_types.append(InstanceType(
                name=s.name,
                cpu=s.extra["guestCpus"],
                ram=s.ram,
                price=price,
                desc=s.extra["description"]
            ))

    if node_types:
        node_types = sorted(
            node_types, key=lambda x: x.price, reverse=False)

    return node_types


def find_node_types(prov: ProviderSpec, ram=2, cpu=2, gpu="") \
        -> List[InstanceType]:
    if prov.providerid == "gce":
        nodes = find_gce(prov, ram, cpu, gpu)
    return nodes


class JupyterState(BaseModel):
    project: str
    provider: str
    location: str
    zone: DNSZone
    volumes: List[BlockStorage] = []
    vm: Optional[VMInstance] = None
    record: Optional[DNSRecord] = None
    volumes: List[BlockStorage] = []


class LabResponse(BaseModel):
    project: str
    token: str
    url: str


class JupyterController:

    def __init__(self, compute: ProviderSpec,
                 dns: DNSSpec,
                 project: str,
                 zoneid: str,
                 location="us-central1-c",
                 state: Optional[JupyterState] = None
                 ):
        self.prov = compute
        self.dns = dns
        zone = self.dns.get_zone(zoneid)
        self._state: JupyterState = state or JupyterState(
            location=location,
            project=project,
            provider=compute.providerid,
            zone=zone
        )

    @classmethod
    def from_state(cls, path, *, compute: ProviderSpec, dns: DNSSpec) -> "JupyterController":
        with open(path, "r") as f:
            d = f.read()
        s = JupyterState(**json.loads(d))
        return cls(
            compute=compute,
            dns=dns,
            project=s.project,
            zoneid=s.zone.id,
            location=s.location,
            state=s
        )

    @property
    def zone(self) -> DNSZone:
        return self._state.zone

    @property
    def location(self) -> str:
        return self._state.location

    @property
    def prj(self) -> str:
        return self._state.project

    def find_node_types(self, ram=2, cpu=2) -> List[InstanceType]:
        if prov.providerid == "gce":
            nodes = find_gce(self.prov, ram, cpu, gpu)
        return nodes

    def _get_startup_script(self):
        here = os.path.abspath(os.path.dirname(__file__))
        with open(f"{here}/files/{self.prov.providerid}_startup.sh", "r") as f:
            startup = f.read()
        return startup

    def check_volume(self, name) -> bool:
        try:
            vol = self.prov.get_volume(name)
            self._state.volumes.append(vol)
            return True
        except Exception:
            return False

    def create_volume(self, name,
                      size="10",
                      description="Data volume",
                      storage_type="pd-standard",
                      labels={},
                      ):
        sr = StorageRequest(
            name=name,
            size=size,
            location=self.location,
            labels=labels,
            description=description,
            storage_type=storage_type,
        )
        st = self.prov.create_volume(sr)
        self._state.volumes.append(st)

    def create_lab(self,
                   container="jupyter/minimal-notebook:python-3.10.6",
                   uuid="1000",
                   boot_size="10",
                   boot_image="debian-11-bullseye-v20220822",
                   boot_type="pd-standard",
                   boot_delete=True,
                   ram=1,
                   cpu=1,
                   domainid="",
                   network="default",
                   tags=["http-server", "https-server"],
                   instance_type=None,
                   volume_data=None,
                   lab_timeout=30,
                   ):
        if ram and cpu and not instance_type:
            _types = self.find_node_types(ram, cpu)
            if _types:
                node_type = _types[0].name
        else:
            node_type = instance_type

        token = secrets.token_urlsafe(16)
        _name = utils.generate_random(
            size=5, alphabet=defaults.NANO_MACHINE_ALPHABET)

        zone = self._state.zone
        to_attach = []
        if volume_data:
            to_attach = [
                AttachStorage(
                    disk_name=volume_data,
                    mode="READ_WRITE",
                )
            ]

        vm = VMRequest(
            name=f"lab-{_name}",
            instance_type=node_type,
            startup_script=self._get_startup_script(),
            location=self.location,
            provider=self.prov.providerid,
            boot=BootDiskRequest(
                image=boot_image,
                size=boot_size,
                disk_type=boot_type,
                auto_delete=boot_delete,
            ),
            metadata={
                "labdomain": zone.domain.strip("."),
                "labimage": container,
                "labtoken": token,
                "labvol": volume_data,
                "labuid": uuid,
                "labtimeout": lab_timeout,
            },
            attached_disks=to_attach,
            tags=tags,
            network=network,
            external_ip="ephemeral",
            labels={"project": self.prj},
        )
        instance = self.prov.create_vm(vm)
        self._state.vm = instance

        url = f"{instance.vm_name}.{self.prj}.{zone.domain}"
        record = DNSRecord(
            name=url,
            zoneid=self.zone.id,
            record_type="A",
            data=[
                instance.public_ips[0]
            ]
        )
        self._state.record = record
        self.dns.create_record(record)
        return LabResponse(
            url=url.strip("."),
            token=token,
            project=self.prj
        )

    def destroy_lab(self):
        self.prov.destroy_vm(vm=self._state.vm.vm_name,
                             location=self._state.vm.location)
        self._state.vm = None
        _record = f"{self._state.record.record_type}:{self._state.record.name}"
        self.dns.delete_record(self._state.zone.id, _record)
        self._state.record = None

    def save(self, path):
        with open(path, "w") as f:
            f.write(json.dumps(self._state.dict()))
