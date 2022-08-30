from rich.console import Console

from labmachine.jupyter import JupyterController
from labmachine.providers.google import GCEProvider, GoogleDNS

console = Console()
compute = GCEProvider()
dns = GoogleDNS()
jup = JupyterController(
    compute=compute,
    dns=dns,
    project="testing",
    zoneid="dymax-app"
)


console.print("=> Checking if volume exist")
if not jup.check_volume("testing-data"):
    console.print("=> Creating new volume")
    jup.create_volume("testing-data", size="10")
else:
    console.print("=> Volume already exist")

console.print("=> Starting lab creation")
rsp = jup.create_lab(
    container="jupyter/minimal-notebook:python-3.10.6",
    instance_type="e2-micro",
    volume_data="testing-data",
    boot_image="lab-minimal-010",
)
console.print("=> Congrats! Lab created")
console.print("Go to: ")
console.print(f"\t [magenta]https://{rsp.url}[/]")
console.print(f"\t Token: [red]{rsp.token}[/]")
jup.save("state.json")
