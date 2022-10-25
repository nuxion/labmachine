import secrets

from rich.console import Console

from labmachine import defaults, utils
from labmachine.providers.google.compute import Compute
from labmachine.providers.google.dns import GoogleDNS
from labmachine.types import (AttachStorage, BootDiskRequest, DNSRecord,
                              GPURequest, VMRequest, Permissions)

g = Compute()
dns = GoogleDNS()
console = Console()

scopes = Permissions(account="labcreator@earthflow.iam.gserviceaccount.com", roles=["cloud-platform"])

_rand = utils.generate_random(
    size=5, alphabet=defaults.NANO_MACHINE_ALPHABET)

MACHINE = f"test-{_rand}"
PROJECT = "test"
DOCKER_IMG="jupyter-gdal:latest"
DOMAIN="test.com"


vm = VMRequest(
    name=MACHINE,
    instance_type="n1-standard-1",
    startup_script=open("labmachine/files/gce_test.sh").read(),
    location="us-central1-c",
    provider="gce",
    boot=BootDiskRequest(
        image="lab-minimal-010",
        size="30",
        disk_type="pd-standard",
        auto_delete=True
    ),
    metadata={
        "image": DOCKER_IMG,
        "registry": "us-central1-docker.pkg.dev/earthflow/repo",
    },
    # preemptible=True,
    tags=["http-server", "https-server"],
    permissions=scopes,
    network="default",
    external_ip="ephemeral",
    labels={"project": PROJECT, "gpu": "no"},
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
