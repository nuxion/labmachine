from typing import Any, Dict, List, Optional, Set, Union
from labmachine.base import ComputeSpec, DNSSpec, LogsSpec
from labmachine.types import (AttachStorage, BlockStorage, BootDiskRequest,
                              DNSRecord, DNSZone, GPURequest, InstanceType,
                              LogEntry, Permissions, StorageRequest,
                              VMInstance, VMRequest)

from labmachine import defaults, errors, utils
import httpx
import os

from urllib.parse import urlparse

VM_PROVIDERS = {"gce": "labmachine.providers.google.Compute"}

def fetch_output(path, *, dst):
    data = None
    if path.startswith("gs://"):
        # FIX: temporal path to override GOOGLE_CREDEN... variable
        # and use JUP_COMPUTE_KEY instead.
        os.environ[defaults.GOOGLE_AUTH_ENV] = os.environ[defaults.JUP_COMPUTE_KEY]
        GS: GenericKVSpec = utils.get_class("labmachine.io.kv_gcs.KVGS")
        _parsed = urlparse(path)
        gs = GS(_parsed.netloc, client_opts={
            "creds": os.getenv(defaults.JUP_COMPUTE_KEY)})
        data = gs.get_stream(f"{_parsed.path[1:]}")
        with open(dst, "wb") as f:
            for chunk in data:
                f.write(chunk)


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

   

class CustomProcessor:
    startup="gce_test.sh"
    boot_image=""
    provider="gce"

    def __init__(self, compute: ComputeSpec,
                 registry=None,
                 image=None,
                 account = None,
                 location="us-central1-c",
                 boot_image="debian-11-bullseye-v20220920"):
        self.compute = compute
        self.image=image
        self.boot_image=boot_image
        self.account = account
        self.registry = registry
        self.location = location
        self.vm = None
        self.status = "init"

    def has_finished(self):
        try:
            rsp = httpx.get(f"http://{self.vm.public_ips[0]}/status")
            if rsp.status_code == 200:
                return True
        except httpx.HTTPError:
            return False
        return False
        
    def get_status(self):
        data = []
        try:
            rsp = httpx.get(f"http://{self.vm.public_ips[0]}/status")
            data = rsp.text.split()
        except httpx.HTTPError:
            pass
        return data

    def get_log(self):
        data = []
        try:
            rsp = httpx.get(f"http://{self.vm.public_ips[0]}/otb.log")
            data = rsp.text.split()
        except httpx.HTTPError:
            pass
        return data

    def process_image(self, bucket, *, img_rgb, img_nir, nir_output, vm_type="e2-small", disk_size="20"):
        _bucket = bucket.strip("/")
        meta = {
            "registry": self.registry,
            "image": self.image,
            "rgb": img_rgb,
            "nir": img_nir,
            "output": nir_output,
            "bucket": _bucket,
            "image": self.image,
        }
        vm = self._create_vm(
            boot_size=disk_size,
            boot_image=self.boot_image,
            metadata=meta,
            account=self.account,
        )
        self.vm = vm
        return f"{_bucket}/{nir_output}"

    def destroy(self):
        self.compute.destroy_vm(vm=self.vm.vm_name,
                                location=self.vm.location)
        

    def _get_startup_script(self):
        here = os.path.abspath(os.path.dirname(__file__))
        _file = self.startup
        with open(f"{here}/files/{_file}", "r") as f:
            startup = f.read()
        return startup

    def find_node_types(self, ram=2, cpu=2, gpu=None) -> List[InstanceType]:
        if self.provider == "gce":
            nodes = find_gce(self.compute, ram, cpu, gpu)
        return nodes

    def _generate_name(self):
        _name = utils.generate_random(
            size=5, alphabet=defaults.NANO_MACHINE_ALPHABET)
        vm_name = f"otb-{_name}"
        return vm_name

    def _create_vm(self,
                    boot_size="10",
                    boot_image="debian-11-bullseye-v20220920",
                    boot_type="pd-standard",
                    boot_delete=True,
                    ram=1,
                    cpu=1,
                    metadata:Dict[str, str]=None,
                    gpu=None,
                    registry=None,
                    network="default",
                    tags=["http-server", "https-server"],
                    instance_type=None,
                    account: str = None,
                    roles: List[str] = ["cloud-platform"]) -> VMInstance:
        if ram and cpu and not instance_type:
            _types = self.find_node_types(ram, cpu)
            if _types:
                node_type = _types[0].name
        else:
            node_type = instance_type

        _gpu = None
        if gpu:
            _gpu = GPURequest(name="gpu",
                              gpu_type=gpu,
                              count=1)

        scopes = None
        if account:
            scopes = Permissions(account=account, roles=roles)

        vm_name = self._generate_name()

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
            metadata=metadata,
            gpu=_gpu,
            permissions=scopes,
            tags=tags,
            network=network,
            external_ip="ephemeral",
        )
        instance = self.compute.create_vm(vm)
        return instance
        

def from_env(provider="gce") -> CustomProcessor:
    compute: ComputeSpec = utils.get_class(
        VM_PROVIDERS[provider])(
            keyvar=defaults.JUP_COMPUTE_KEY
    )
    reg = os.getenv("REGISTRY")
    img = os.getenv("IMAGE")
    boot = os.getenv("BOOT")
    acc = os.getenv("ACCOUNT")
    return CustomProcessor(compute, registry=reg,
                           image=img,
                           account=acc,
                           boot_image=boot)
 
