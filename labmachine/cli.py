import click
import time
from rich import print_json
from rich.console import Console
from rich.progress import Progress, SpinnerColumn
from rich.table import Table
import requests

from labmachine.jupyter import (DNS_PROVIDERS, VM_PROVIDERS, JupyterController,
                                JupyterState, fetch_state, push_state)
from labmachine.types import DNSZone
from labmachine.utils import get_class

console = Console()
progress = Progress(
    SpinnerColumn(),
    "[progress.description]{task.description}",
)


@click.group()
def cli():
    """
    jupctl command line
    """
    pass


@click.group()
def volumes():
    """ volumes operations """
    pass


@cli.command(name="list-locations")
@click.option("--compute-provider", "-C", default="gce",
              help="Provider to be used for vm creation")
@click.option("--filter-country", "-c", default=None,
              help="filter by country")
def list_locs(compute_provider, filter_country):
    """ List locations related to a compute provider """
    driver = get_class(VM_PROVIDERS[compute_provider])()
    locs = driver.driver.list_locations()
    table = Table(title=f"{compute_provider}'s locations")

    table.add_column("location", justify="left")
    table.add_column("country", justify="right")

    for loc in locs:
        if filter_country:
            if loc.country == filter_country:
                table.add_row(loc.name, loc.country)
        else:
            table.add_row(loc.name, loc.country)

    console.print(table)


@cli.command(name="list-vm-types")
@click.option("--compute-provider", "-C", default="gce",
              help="Provider to be used for vm creation")
@click.option("--location", "-l", default=None,
              help="by location")
def list_vm_types(compute_provider, location):
    """ List vm types """
    driver = get_class(VM_PROVIDERS[compute_provider])()

    types = driver.driver.list_sizes(location=location)
    table = Table(title=f"{compute_provider}'s vm types")
    table.add_column("name", justify="left")
    table.add_column("ram", justify="right")
    table.add_column("cpu", justify="right")

    for vm in types:
        _cpu = vm.extra["guestCpus"]
        _ram = f"{round(vm.ram/1024)} GB"
        table.add_row(vm.name, _ram, str(_cpu))

    console.print(table)


@cli.command(name="list-dns")
@click.option("--dns-provider", "-D", default="gce",
              help="Provider to be used for dns")
def list_dns(dns_provider):
    """ List DNS available by provider """
    driver = get_class(DNS_PROVIDERS[dns_provider])()
    zones = driver.list_zones()
    table = Table(title=f"DNS zones")

    table.add_column("dns id", justify="left")
    table.add_column("domain", justify="right")
    table.add_column("type", justify="right")

    for zone in zones:
        table.add_row(zone.id, zone.domain, zone.zone_type)

    console.print(table)


@cli.command(name="list-providers")
@click.argument("kind", default="all", type=click.Choice(["dns", "compute", "all"]))
def list_provs(kind):
    """ list compute and dns providers """

    table = Table(title="Providers list")
    table.add_column("code", justify="left")
    table.add_column("kind", justify="right")

    if kind == "dns":
        for key in DNS_PROVIDERS.keys():
            table.add_row(key, "dns")

    elif kind == "compute":
        for key in VM_PROVIDERS.keys():
            table.add_row(key, "compute")
    elif kind == "all":
        for key in VM_PROVIDERS.keys():
            table.add_row(key, "compute")
        for key in DNS_PROVIDERS.keys():
            table.add_row(key, "dns")

    console.print(table)


@cli.command(name="init")
@click.option("--project", "-p", default="default", help="Project")
@click.option("--compute-provider", "-C", default="gce",
              help="Provider to be used for vm creation")
@click.option("--dns-provider", "-D", default="gce",
              help="Provider to be used for dns creation")
@click.option("--location", "-l", default=None,
              help="location to be used")
@click.option("--dns-id", "-d", default=None, required=True,
              help="Domain to be used")
@click.option("--state", "-s", default="state.json", help="Where state will be stored")
def init(project, compute_provider, dns_provider, location, dns_id, state):
    """ Initialize jupctl """
    jup = JupyterController.init(
        project, compute_provider, dns_provider, location, dns_id, state)
    if not jup:
        console.print("[red]It seems that this project already exist.[/]")
        console.print("Try with the fetch command instead.")
    else:
        console.print(f"=> Congrats! 🎉 [green]Lab data initialized[/]")


@cli.command(name="up")
@click.option("--volume", "-v", default=None, help="Volume name to use")
@click.option("--container", "-c",
              default="jupyter/minimal-notebook:python-3.10.6",
              help="Container to be used")
@click.option("--boot-image", "-b", default="debian-11-bullseye-v20220822",
              help="Boot image")
@click.option("--instance-type", "-T", default="",
              help="Instance type")
@click.option("--network", "-n", default="default",
              help="network")
@click.option("--tags", "-t", default="http-server,https-server",
              help="Tags to be used")
@click.option("--timeout", default=20,
              help="Timeout in minutes")
@click.option("--state", "-s", default="state.json", help="Where state will be stored")
@click.option("--debug", "-d", default=False, is_flag=True, help="flag debug")
@click.option("--wait", "-w", is_flag=True, default=False, help="Wait until service is ready")
def up(volume, container, boot_image, instance_type, network, tags,
       timeout, state, debug, wait):
    """ Create a VM instance for jupyter """
    jup = JupyterController.from_state(state)
    if volume:
        console.print("=> Checking if volume exist")
        if not jup.check_volume(volume):
            console.print(f"=> [orange]Warning: volume {volume} doesn't exist")
        # jup.create_volume(volume, size=volume_size)
    with progress:
        task = progress.add_task("Starting lab creation")
        rsp = jup.create_lab(
            container=container,
            boot_image=boot_image,
            instance_type=instance_type,
            volume_data=volume,
            network=network,
            tags=tags.split(","),
            debug=debug,
        )
        jup.push()
        if wait:
            code = -1
            while code != 200:
                res = requests.get(rsp.url)
                code = res.status_code
                time.sleep(10)

    console.print("=> Congrats! Lab created")
    console.print("Go to: ")
    console.print(f"\t [magenta]https://{rsp.url}[/]")
    console.print(f"\t Token: [red]{rsp.token}[/]")


@cli.command(name="fetch")
@click.option("--state", "-s", default="state.json",
              help="Where state will be stored")
def fetch(state):
    """ fetch new objects from the provider """
    jup = JupyterController.from_state(state)
    with progress:
        task1 = progress.add_task("Fetching new objects from cloud")
        _dict = jup.fetch(console)
    print_json(data=_dict)
    jup.push()


@cli.command(name="destroy")
@click.option("--state", "-s", default="state.json",
              help="Where state will be stored")
def destroy(state):
    """It will destroy a lab """
    jup = JupyterController.from_state(state)
    with progress:
        task1 = progress.add_task(
            f"[red]Destroying jupyter {jup._state.url}[/]")
        jup.destroy_lab()
        jup.push()


if __name__ == "__main__":

    cli()
