import secrets

from rich.console import Console

from labmachine import defaults, utils
from labmachine.providers.google.compute import GCEProvider
from labmachine.providers.google.dns import GoogleDNS
from labmachine.types import (AttachStorage, BootDiskRequest, DNSRecord,
                              GPURequest, VMRequest)

g = GCEProvider()
dns = GoogleDNS()
console = Console()

_rand = utils.generate_random(
    size=5, alphabet=defaults.NANO_MACHINE_ALPHABET)

MACHINE = f"test-{_rand}"
MACHINE_TYPE = "e2-micro"
MACHINE_IMG = "debian-11-bullseye-v20220822"
DOCKER_IMG = "jupyter/minimal-notebook"
PROJECT = "test"
LOCATION = "us-central1-c"
TOKEN = secrets.token_urlsafe(16)
PROVIDER = "gce"
DOMAIN = "dymax.app"
ZONEID = "dymax-app"
USERID = "1000"

VOLUME_DATA = "tesdatadisk"


def check_disk():
    v = None
    try:
        v = g.get_volume(VOLUME_DATA)
    except Exception:
        pass
    if not v:
        sr = StorageRequest(
            name=VOLUME_DATA,
            location=LOCATION,
            storage_type="pd-standard"
        )
        g.create_volume(sr)


vm = VMRequest(
    name=MACHINE,
    instance_type="n1-standard-1",
    # startup_script=open(f"scripts/{PROVIDER}_startup.sh").read(),
    location="us-central1-c",
    provider="gce",
    boot=BootDiskRequest(
        image="debian-11-bullseye-v20220822",
        size="10",
        disk_type="pd-standard",
        auto_delete=True
    ),
    metadata={
        "labdomain": "dymax.app",
        "labimage": DOCKER_IMG,
        "labtoken": TOKEN,
        "labvol": VOLUME_DATA,
        "labuid": USERID
    },
    attached_disks=[
        AttachStorage(
            disk_name=VOLUME_DATA,
            mode="READ_WRITE",
        )
    ],
    # preemptible=True,
    tags=["http-server", "https-server"],
    network="default",
    external_ip="ephemeral",
    labels={"project": PROJECT, "gpu": "yes"},
    gpu=GPURequest(name="tesla", gpu_type="nvidia-tesla-t4", count=1)
)
console.print(f">> Creating VM as [magenta]{vm.name}[/]...")
instance = g.create_vm(vm)
url = f"{instance.vm_name}.{PROJECT}.{DOMAIN}"
# record = DNSRecord(
#     name=f"{url}.",
#     zoneid=ZONEID,
#     record_type="A",
#     data=[
#         instance.public_ips[0]
#     ]
# )
# dns.create_record(record)
console.print(f">> Creating URL: [magenta]{url}[/]...")
console.print(f"[green bold]🙌 Done![/]\n")
console.print(f"Now you can enter going to: ")
console.print(f"\t {instance.vm_name}")
#console.print(f"\t https://{url}\n")
# console.print(f"\t Token: [red bold]{TOKEN}[/]")
