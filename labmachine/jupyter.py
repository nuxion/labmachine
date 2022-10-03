import json
import os
import secrets
from importlib import import_module
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union
from urllib.parse import urlparse

from pydantic import BaseModel, BaseSettings

from labmachine import defaults, utils
from labmachine.base import ComputeSpec, DNSSpec
from labmachine.io.kvspec import GenericKVSpec
from labmachine.types import (AttachStorage, BlockStorage, BootDiskRequest,
                              DNSRecord, DNSZone, GPURequest, InstanceType,
                              Permissions, StorageRequest, VMInstance,
                              VMRequest)

VM_PROVIDERS = {"gce": "labmachine.providers.google.Compute"}
DNS_PROVIDERS = {
    "gce": "labmachine.providers.google.GoogleDNS",
    "cloudflare": "labmachine.providers.cloudflare.dns.CloudflareDNS",
}


def _check_dns_env_var():
    _env = os.getenv(defaults.JUP_DNS_KEY)
    if _env:
        return defaults.JUP_DNS_KEY
    else:
        return defaults.JUP_COMPUTE_KEY


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
    account: Optional[str] = None
    roles: List[str] = []
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


class ContainerRegistry(BaseModel):
    name: str
    project: str
    location: str


class JupyterConfig(BaseSettings):
    VOLUME: Optional[JupyterVolume]
    INSTANCE: JupyterInstance
    STATE_PATH: str = "state.json"
    REGISTRY: Optional[ContainerRegistry] = None

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
    registry: Optional[ContainerRegistry] = None


class LabResponse(BaseModel):
    project: str
    token: str
    url: str


def load_conf_module(settings_module) -> JupyterConfig:
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
    data = None
    if path.startswith("gs://"):
        GS: GenericKVSpec = utils.get_class("labmachine.io.kv_gcs.KVGS")
        _parsed = urlparse(path)
        gs = GS(_parsed.netloc, client_opts={
            "creds": os.getenv(defaults.JUP_COMPUTE_KEY)})
        data = gs.get(f"{_parsed.path[1:]}")
        if data:
            data = data.decode("utf-8")
    elif Path(path).exists():
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
        gs = GS(_parsed.netloc, client_opts={
            "creds": os.getenv(defaults.JUP_COMPUTE_KEY)
        })
        _fp = f"{_parsed.path[1:]}"
        gs.put(_fp, jd.encode())
        fp = state.self_link
    else:
        _fp = Path(state.self_link).resolve()
        with open(_fp, "w") as f:
            f.write(json.dumps(_dict))
        fp = str(_fp)
    return fp


def find_gce(prov: ComputeSpec, ram: int, cpu: str, gpu="") \
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


def find_node_types(prov: ComputeSpec, ram=2, cpu=2, gpu="") \
        -> List[InstanceType]:
    if prov.providerid == "gce":
        nodes = find_gce(prov, ram, cpu, gpu)
    return nodes


class JupyterController:

    def __init__(self, compute: ComputeSpec,
                 dns: DNSSpec,
                 state: JupyterState
                 ):
        self.compute = compute
        self.dns = dns
        self._zone = self.dns.get_zone(state.zone_id)
        self._state: JupyterState = state

    @classmethod
    def init(cls,
             project: str,
             compute_provider: str,
             dns_provider: str,
             location: str,
             dns_id: str,
             state_path: str,
             ) -> Union["JupyterController", None]:
        """ it will be deprecated in future releases """
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
            compute: ComputeSpec = utils.get_class(
                VM_PROVIDERS[compute_provider])(keyvar=defaults.JUP_COMPUTE_KEY)
            dns: DNSSpec = utils.get_class(
                DNS_PROVIDERS[dns_provider])(
                    keyvar=_check_dns_env_var())
            jup = cls(compute, dns=dns, state=st)
            return jup
        return None

    # @classmethod
    # def from_settings(cls, settings_module: str) -> "JupyterController":
    #     cfg = load_jupyter_conf(settings_module)
    #     state = fetch_state(cfg.STATE_PATH)
    #     compute: ComputeSpec = utils.get_class(
    #         VM_PROVIDERS[state.compute_provider])(keyvar=defaults.JUP_COMPUTE_KEY)
    #     dns: DNSSpec = utils.get_class(
    #         DNS_PROVIDERS[state.dns_provider])(keyvar=_check_dns_env_var())

    #     return cls(
    #         compute=compute,
    #         dns=dns,
    #         state=state
    #     )

    @classmethod
    def from_state(cls, path: str) -> "JupyterController":
        """ It will be deprecated in future releases"""
        s = fetch_state(path)
        compute: ComputeSpec = utils.get_class(
            VM_PROVIDERS[s.compute_provider])(
                keyvar=defaults.JUP_COMPUTE_KEY
        )
        dns: DNSSpec = utils.get_class(DNS_PROVIDERS[s.dns_provider])(
            keyvar=defaults.JUP_COMPUTE_KEY)
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

    @property
    def url(self) -> str:
        return self._state.url

    def _build_url(self, vm_name) -> str:
        url = f"{vm_name}.{self.prj}.{self.zone.domain}"
        return url

    def find_node_types(self, ram=2, cpu=2) -> List[InstanceType]:
        if prov.providerid == "gce":
            nodes = find_gce(self.compute, ram, cpu, gpu)
        return nodes

    def _get_startup_script(self):
        here = os.path.abspath(os.path.dirname(__file__))
        _file = f"{self.compute.providerid}_startup.sh"
        with open(f"{here}/files/{_file}", "r") as f:
            startup = f.read()
        return startup

    def import_volume(self, name):
        _v = self.compute.get_volume(name, location=self.location)
        self._state.volumes[name] = _v

    def resize_volume(self, name, size) -> bool:
        vol = self._state.volumes.get(name)
        if vol:
            res = self.compute.resize_volume(name, size,
                                             location=self._state.location)
            if res:
                vol.size = size
                self._state.volumes[name] = vol
            return res
        return False

    def destroy_volume(self, name) -> bool:
        vol = self._state.volumes.get(name)
        if vol:
            res = self.compute.destroy_volume(name, self.location)
            del(self._state.volumes[name])
            return res
        return False

    def check_volume(self, name) -> bool:
        vol = self.compute.get_volume(name)
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
        st = self.compute.create_volume(sr)
        self._state.volumes[name] = st

    def create_lab(self, instance: JupyterInstance, *,
                   volume: Optional[JupyterVolume] = None) \
            -> LabResponse:
        """
        It check for the volumes, create them, create the instance
        and register the public ip of the instance into the DNS.
        """

        token = secrets.token_urlsafe(16)
        if volume:
            if not self.check_volume(volume.name):
                self.create_volume(volume.name, size=volume.size)
                self.push()
        vm = self.create_instance(**instance.dict(), token=token)
        record = DNSRecord(
            name=self.url,
            zoneid=self.zone.id,
            record_type="A",
            data=[
                vm.public_ips[0]
            ]
        )
        data = self.dns.create_record(record)
        record.id = data["id"]
        self._state.record = record

        return LabResponse(
            url=self.url.strip("."),
            token=token,
            project=self.prj
        )

    def _generate_url(self) -> str:
        """ it generates a random vm name and creates the url without protocol:
            lab-<random_string>.<project>.<dns_domain>
        """
        _name = utils.generate_random(
            size=5, alphabet=defaults.NANO_MACHINE_ALPHABET)
        vm_name = f"lab-{_name}"

        url = f"{vm_name}.{self.prj}.{self.zone.domain}"

        return url

    def create_instance(self,
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
                        account: str = None,
                        roles: List[str] = [],
                        debug=False,
                        token=None,
                        ) -> VMInstance:
        if ram and cpu and not instance_type:
            _types = self.find_node_types(ram, cpu)
            if _types:
                node_type = _types[0].name
        else:
            node_type = instance_type

        to_attach = []
        if volume_data:
            vol = self.compute.get_volume(volume_data)
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

        scopes = None
        if account:
            scopes = Permissions(account=account, roles=roles)

        url = self._generate_url()
        self._state.url = url
        vm_name = url.split(".")[0]

        vm = VMRequest(
            name=vm_name,
            instance_type=node_type,
            startup_script=self._get_startup_script(),
            location=self.location,
            provider=self.compute.providerid,
            boot=BootDiskRequest(
                image=boot_image,
                size=boot_size,
                disk_type=boot_type,
                auto_delete=boot_delete,
            ),
            metadata={
                "labdomain": f"{self.prj}.{self.zone.domain}".strip("."),
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
            permissions=scopes,
            attached_disks=to_attach,
            tags=tags,
            network=network,
            external_ip="ephemeral",
            labels={"project": self.prj},
        )
        instance = self.compute.create_vm(vm)
        self._state.vm = instance
        return instance

    def destroy_lab(self):
        if self._state.vm:
            self.compute.destroy_vm(vm=self._state.vm.vm_name,
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
        vms = self.compute.list_vms()
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
        records = self.dns.list_records(self._state.zone_id)
        if self._state.url:
            base_name = self._state.url.split(".")[0]
            for rec in records:
                if base_name in rec.name:
                    self._state.record = rec
                    if console:
                        console.print(
                            f"=> DNS {self._state.record.name} fetched")
                    break
        volumes = {}
        for _vol in self._state.volumes.keys():
            vol = self.compute.get_volume(_vol)
            if vol:
                volumes[_vol] = vol
        self._state.volumes = volumes

        _dict = self._state.dict()
        return _dict

    def clean(self):
        clean_state(self._state.self_link)


def save_conf(state_path, conf_path=defaults.JUPCTL_CONF):
    utils.write_toml(conf_path, {"state": state_path})


def _load_state_path(conf_path=defaults.JUPCTL_CONF) -> str:
    data = utils.read_toml(conf_path)
    return data.get("state")


def from_state(path: str) -> JupyterController:
    """ It creates JupyterController from the state """
    s = fetch_state(path)
    compute: ComputeSpec = utils.get_class(
        VM_PROVIDERS[s.compute_provider])(
            keyvar=defaults.JUP_COMPUTE_KEY
    )
    dns: DNSSpec = utils.get_class(DNS_PROVIDERS[s.dns_provider])(
        keyvar=_check_dns_env_var())
    return JupyterController(
        compute=compute,
        dns=dns,
        state=s
    )


def from_conf(conf_path: str = defaults.JUPCTL_CONF) -> JupyterController:
    _state = _load_state_path(conf_path)
    jup = from_state(_state)
    return jup


def init(project: str,
         compute_provider: str,
         dns_provider: str,
         location: str,
         dns_id: str,
         state_path: str,
         ) -> Union[JupyterController, None]:
    """ it will be deprecated in future releases """
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
        compute: ComputeSpec = utils.get_class(
            VM_PROVIDERS[compute_provider])(keyvar=defaults.JUP_COMPUTE_KEY)
        dns: DNSSpec = utils.get_class(
            DNS_PROVIDERS[dns_provider])(
                keyvar=_check_dns_env_var())
        jup = JupyterController(compute, dns=dns, state=st)
        return jup
    return None
