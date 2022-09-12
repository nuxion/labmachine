import json
import os
import secrets
from importlib import import_module
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
from urllib.parse import urlparse

from pydantic import BaseModel, BaseSettings

from labmachine import defaults, utils
from labmachine.base import DNSSpec, ProviderSpec
from labmachine.io.kvspec import GenericKVSpec
from labmachine.types import (AttachStorage, BlockStorage, BootDiskRequest,
                              DNSRecord, DNSZone, GPURequest, InstanceType,
                              StorageRequest, VMInstance, VMRequest)

VM_PROVIDERS = {"gce": "labmachine.providers.google.compute.GCEProvider"}
DNS_PROVIDERS = {
    "gce": "labmachine.providers.google.dns.GoogleDNS",
    "cloudflare": "labmachine.providers.cloudflare.dns.CloudflareDNS",
}


class JupyterInstance(BaseModel):
    container: str = "jupyter/minimal-notebook:python-3.10.6"
    uuid: str = "1000"
    boot_size: str = "10"
    boot_image: str = "debian-11-bullseye-v20220822"
    boot_type: str = "pd-standard"
    boot_delete: bool = True
    ram: int = 1
    cpu: int = 1
    gpu: Optional[str] = None
    registry: Optional[str] = None
    network: str = "default"
    tags: List[str] = ["http-server", "https-server"]
    instance_type: Optional[str] = None
    volume_data: Optional[str] = None
    lab_timeout: int = 20 * 60  # in seconds
    debug: bool = False


class JupyterVolume(BaseModel):
    name: str
    size: str = "10"
    description: str = "Data volume",
    storage_type: str = "pd-standard",
    labels: Dict[str, Any] = {},


class JupyterConfig(BaseSettings):
    VOLUME: Optional[JupyterVolume]
    INSTANCE: JupyterInstance
    STATE_PATH: str = "state.json"

    class Config:
        env_prefix = "JUP_"


class JupyterState(BaseModel):
    project: str
    compute_provider: str
    dns_provider: str
    location: str
    zone_id: str
    self_link: str
    volumes: Dict[str, BlockStorage] = {}
    vm: Optional[VMInstance] = None
    url: Optional[str] = None
    record: Optional[DNSRecord] = None


class LabResponse(BaseModel):
    project: str
    token: str
    url: str


def load_jupyter_conf(settings_module) -> JupyterConfig:
    mod = import_module(settings_module)

    settings_dict = {}
    for m in dir(mod):
        if m.isupper():
            # sets.add(m)
            value = getattr(mod, m)
            settings_dict[m] = value

    cfg = JupyterConfig(**settings_dict)
    return cfg


def fetch_state(path) -> Union[JupyterState, None]:
    if path.startswith("gs://"):
        GS: GenericKVSpec = utils.get_class("labmachine.io.kv_gcs.KVGS")
        _parsed = urlparse(path)
        gs = GS(_parsed.netloc)
        data = gs.get(f"{_parsed.path[1:]}")
        if data:
            data = data.decode("utf-8")
    else:
        with open(path, "r") as f:
            data = f.read()
    if data:
        jdata = json.loads(data)
        s = JupyterState(**jdata)
        return s
    return None


def clean_state(state_link) -> str:
    if state_link.startswith("gs://"):
        GS: GenericKVSpec = utils.get_class(
            "labmachine.io.kv_gcs.KVGS")
        _parsed = urlparse(state_link)
        gs = GS(_parsed.netloc)
        _fp = f"{_parsed.path[1:]}"
        gs.delete(_fp)
    else:
        pass


def push_state(state: JupyterState) -> str:
    _dict = state.dict()
    jd = json.dumps(_dict)

    if state.self_link.startswith("gs://"):
        GS: GenericKVSpec = utils.get_class(
            "labmachine.io.kv_gcs.KVGS")
        _parsed = urlparse(state.self_link)
        gs = GS(_parsed.netloc)
        _fp = f"{_parsed.path[1:]}"
        gs.put(_fp, jd.encode())
        fp = state.self_link
    else:
        _fp = Path(state.self_link).resolve()
        with open(_fp, "w") as f:
            f.write(json.dumps(_dict))
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
    if self.prov.providerid == "gce":
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
    def init(cls, project,
             compute_provider,
             dns_provider,
             location,
             dns_id,
             state_path) -> Union["JupyterController", None]:
        if not fetch_state(state_path):
            st = JupyterState(
                project=project,
                compute_provider=compute_provider,
                dns_provider=dns_provider,
                location=location,
                zone_id=dns_id,
                self_link=state_path,
            )
            fp = push_state(st)
            jup = cls.from_state(state_path)
            return jup
        return None

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

    def build_url(self, vm_name) -> str:
        url = f"{vm_name}.{self.prj}.{self.zone.domain}"
        return url

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

    def import_volume(self, name):
        _v = self.prov.get_volume(name, location=self.location)
        self._state.volumes[name] = _v

    def resize_volume(self, name, size) -> bool:
        vol = self._state.volumes.get(name)
        if vol:
            res = self.prov.resize_volume(name, size,
                                          location=self._state.location)
            if res:
                vol.size = size
                self._state.volumes[name] = vol
            return res
        return False

    def destroy_volume(self, name) -> bool:
        vol = self._state.volumes.get(name)
        if vol:
            res = self.prov.destroy_volume(name, self.location)
            del(self._state.volumes[name])
            return res
        return False

    def check_volume(self, name) -> bool:
        vol = self.prov.get_volume(name)
        if vol:
            return True
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
        self._state.volumes[name] = st

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
                   registry=None,
                   network="default",
                   tags=["http-server", "https-server"],
                   instance_type=None,
                   volume_data=None,
                   lab_timeout=20 * 60,  # in seconds
                   debug=False
                   ) -> LabResponse:
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
        url = self.build_url(vm_name)
        self._state.url = url
        to_attach = []
        if volume_data:
            vol = self.prov.get_volume(volume_data)
            if vol:
                to_attach = [
                    AttachStorage(
                        disk_name=volume_data,
                        mode="READ_WRITE",
                    )
                ]
                self._state.volumes[volume_data] = vol

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
                "location": self.location,
                "registry": registry
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
        if self._state.vm:
            self.prov.destroy_vm(vm=self._state.vm.vm_name,
                                 location=self._state.vm.location)
            self._state.vm = None
        if self._state.record:
            self.dns.delete_record(self.zone.id, self._state.record.id)
            self._state.record = None
        self._state.url = None

    def push(self) -> str:
        """ Returns the final path where the file is written """
        fp = push_state(self._state)
        return fp

    def fetch(self, console=None):
        vms = self.prov.list_vms()
        vm_set = False
        for vm in vms:
            prj = vm.labels.get("project")
            if prj == self._state.project:
                self._state.vm = vm
                if console:
                    console.print(
                        f"=> VM {self._state.vm.vm_name} fetched")
                    vm_set = True
                # for vol in self._state.vm.volumes:
                #     _v = self.prov.get_volume(vol)
                #     if _v not in
                #
                break
        if not vm_set:
            self._state.vm = None
            if console:
                console.print(
                    f"=> Stale vm found")
        records = self.dns.list_records(self._state.zone_id)
        if self._state.vm:
            for rec in records:
                if self._state.vm.vm_name in rec.name:
                    self._state.record = rec
                    if console:
                        console.print(
                            f"=> DNS {self._state.record.name} fetched")
                    self._state.url = self.build_url(self._state.vm.vm_name)
                    break
        volumes = {}
        for _vol in self._state.volumes.keys():
            vol = self.prov.get_volume(_vol)
            if vol:
                volumes[_vol] = vol
        self._state.volumes = volumes

        _dict = self._state.dict()
        return _dict

    def clean(self):
        clean_state(self._state.self_link)
