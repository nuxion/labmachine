import json
import os
import secrets
from pathlib import Path
from typing import List, Optional, Set
from urllib.parse import urlparse

from pydantic import BaseModel

from labmachine import defaults, utils
from labmachine.base import DNSSpec, ProviderSpec
from labmachine.io.kvspec import GenericKVSpec
from labmachine.types import (AttachStorage, BlockStorage, BootDiskRequest,
                              DNSRecord, DNSZone, GPURequest, InstanceType,
                              StorageRequest, VMInstance, VMRequest)

VM_PROVIDERS = {"gce": "labmachine.providers.google.compute.GCEProvider"}
DNS_PROVIDERS = {"gce": "labmachine.providers.google.dns.GoogleDNS"}


class JupyterState(BaseModel):
    project: str
    compute_provider: str
    dns_provider: str
    location: str
    zone_id: str
    volumes: List[BlockStorage] = []
    vm: Optional[VMInstance] = None
    url: Optional[str] = None
    record: Optional[DNSRecord] = None
    volumes: Set[BlockStorage] = []
    self_link: str = None


class LabResponse(BaseModel):
    project: str
    token: str
    url: str


def fetch_state(path) -> JupyterState:
    if path.startswith("gs://"):
        GS: GenericKVSpec = utils.get_class("labmachine.io.kv_gcs.KVGS")
        _parsed = urlparse(path)
        gs = GS(_parsed.netloc)
        data = gs.get(f"{_parsed.path[1:]}")
        data = data.decode("utf-8")
    else:
        with open(path, "r") as f:
            data = f.read()

    s = JupyterState(**json.loads(data))
    return s


def push_state(state: JupyterState) -> str:
    if state.self_link.startswith("gs://"):
        GS: GenericKVSpec = utils.get_class(
            "labmachine.io.kv_gcs.KVGS")
        _parsed = urlparse(state.self_link)
        gs = GS(_parsed.netloc)
        _d = json.dumps(state.dict())
        _fp = f"{_parsed.path[1:]}"
        gs.put(_fp, _d.encode())
        fp = state.self_link
    else:
        _fp = Path(state.self_link).resolve()
        with open(_fp, "w") as f:
            f.write(json.dumps(state.dict()))
        fp = str(_fp)
    return fp


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


class JupyterController:

    def __init__(self, compute: ProviderSpec,
                 dns: DNSSpec,
                 state: JupyterState
                 ):
        self.prov = compute
        self.dns = dns
        self._zone = self.dns.get_zone(state.zone_id)
        self._state: JupyterState = state

    @classmethod
    def from_state(cls, path: str) -> "JupyterController":
        s = fetch_state(path)
        compute: ProviderSpec = utils.get_class(
            VM_PROVIDERS[s.compute_provider])()
        dns: DNSSpec = utils.get_class(DNS_PROVIDERS[s.dns_provider])()
        return cls(
            compute=compute,
            dns=dns,
            state=s
        )

    @property
    def zone(self) -> DNSZone:
        return self._zone

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
        _file = f"{self.prov.providerid}_startup.sh"
        # if gpu:
        #    _file = f"{self.prov.providerid}_startup_gpu.sh"
        with open(f"{here}/files/{_file}", "r") as f:
            startup = f.read()
        return startup

    def check_volume(self, name) -> bool:
        try:
            vol = self.prov.get_volume(name)
            self._state.volumes.add(vol)
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
        self._state.volumes.add(st)

    def create_lab(self,
                   container="jupyter/minimal-notebook:python-3.10.6",
                   uuid="1000",
                   boot_size="10",
                   boot_image="debian-11-bullseye-v20220822",
                   boot_type="pd-standard",
                   boot_delete=True,
                   ram=1,
                   cpu=1,
                   gpu=None,
                   domainid="",
                   network="default",
                   tags=["http-server", "https-server"],
                   instance_type=None,
                   volume_data=None,
                   lab_timeout=20 * 60,  # in seconds
                   debug=False
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

        vm_name = f"lab-{_name}"
        zone = self.zone
        url = f"{vm_name}.{self.prj}.{zone.domain}"
        self._state.url = url
        to_attach = []
        if volume_data:
            to_attach = [
                AttachStorage(
                    disk_name=volume_data,
                    mode="READ_WRITE",
                )
            ]
        _gpu = None
        if gpu:
            _gpu = GPURequest(name="gpu",
                              gpu_type=gpu,
                              count=1)

        vm = VMRequest(
            name=vm_name,
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
                "labdomain": f"{self.prj}.{zone.domain}".strip("."),
                "laburl": url.strip("."),
                "labimage": container,
                "labtoken": token,
                "labvol": volume_data,
                "labuid": uuid,
                "labtimeout": lab_timeout,
                "debug": "yes" if debug else "no",
                "gpu": "yes" if gpu else "no",
            },
            gpu=_gpu,
            attached_disks=to_attach,
            tags=tags,
            network=network,
            external_ip="ephemeral",
            labels={"project": self.prj},
        )
        instance = self.prov.create_vm(vm)
        self._state.vm = instance

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
        self.dns.delete_record(self.zone.id, _record)
        self._state.record = None
        self._state.url = None

    def save(self) -> str:
        """ Returns the final path where the file is written """
        push_state()
        if self._state.self_link.startswith("gs://"):

            GS: GenericKVSpec = utils.get_class(
                "labmachine.io.kv_gcs.KVGS")
            gs = GS(bucket)
            _d = json.dumps(self._state.dict())
            _fp = f"{self.prj}/{self.location}/{path}"
            gs.put(_fp, _d.encode())
            fp = f"gs://{bucket}/{_fp}"
        else:
            _fp = Path("path").resolve()
            with open(_fp, "w") as f:
                f.write(json.dumps(self._state.dict()))
            fp = str(_fp)
        return fp
