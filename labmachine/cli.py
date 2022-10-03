import datetime
import json
import sys
import time
from datetime import timedelta
from pathlib import Path

import click
import requests
from rich import print_json
from rich.console import Console
from rich.progress import Progress, SpinnerColumn
from rich.prompt import Confirm
from rich.table import Table

from labmachine import defaults, jupyter, shortcuts
from labmachine.types import DNSZone
from labmachine.utils import convert_size, get_class

console = Console()
progress = Progress(
    SpinnerColumn(),
    "[progress.description]{task.description}",
)


def _load_jupyter(state_path=None) -> jupyter.JupyterController:
    if state_path:
        jup = jupyter.from_state(state_path)
    else:
        jup = jupyter.from_conf()
    return jup


def check_readiness(url: str, timeout: int = 10 * 60):
    start_time = datetime.datetime.now()
    end_time = start_time + timedelta(seconds=timeout)
    code = -1
    _url = url if url.startswith("https://") else f"https://{url}"
    while code != 200 and datetime.datetime.now() < end_time:
        try:
            res = requests.get(_url, timeout=20)
            code = res.status_code
        except requests.exceptions.RequestException:
            code = -1
        if code != 200:
            time.sleep(10)
    return code


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
    if Path(defaults.JUPCTL_CONF).is_file():
        console.print(
            f"[red]A {defaults.JUPCTL_CONF} already exist in the project[/]")
    else:
        jup = jupyter.init(
            project, compute_provider, dns_provider, location, dns_id, state)
        if not jup:
            console.print("[red]It seems that this project already exist.[/]")
            console.print("Try with the fetch command instead.")
        else:
            console.print(
                f":smile_cat: Congratulations! [green]Lab data initialized[/]")
            jupyter.save_conf(state)


@cli.command(name="list-locations")
@click.option("--compute-provider", "-C", default="gce",
              help="Provider to be used for vm creation")
@click.option("--filter-country", "-c", default=None,
              help="filter by country")
def list_locs(compute_provider, filter_country):
    """ List locations related to a compute provider """
    driver = get_class(jupyter.VM_PROVIDERS[compute_provider])()
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
    driver = get_class(jupyter.VM_PROVIDERS[compute_provider])()

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


@cli.command(name="list-images")
@click.option("--compute-provider", "-C", default="gce",
              help="Provider to be used for vm creation")
def list_images(compute_provider):
    """ List images to be used as boot disk"""
    driver = get_class(jupyter.VM_PROVIDERS[compute_provider])()

    images = driver.driver.list_images()
    table = Table(title=f"{compute_provider}'s images")
    table.add_column("name", justify="left")

    for img in images:
        table.add_row(img.name)

    console.print(table)


@cli.command(name="list-dns")
@click.option("--dns-provider", "-D", default="gce",
              help="Provider to be used for dns")
def list_dns(dns_provider):
    """ List DNS available by provider """
    driver = get_class(jupyter.DNS_PROVIDERS[dns_provider])()
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
        for key in jupyter.DNS_PROVIDERS.keys():
            table.add_row(key, "dns")

    elif kind == "compute":
        for key in jupyter.VM_PROVIDERS.keys():
            table.add_row(key, "compute")
    elif kind == "all":
        for key in jupyter.VM_PROVIDERS.keys():
            table.add_row(key, "compute")
        for key in jupyter.DNS_PROVIDERS.keys():
            table.add_row(key, "dns")

    console.print(table)


@cli.command(name="up")
@click.option("--state", "-s", default=None, help="Where state will be stored")
@click.option("--from-module", "-f", default=None, required=True, help="Create lab from module")
# @click.option("--debug", "-d", default=False, is_flag=True, help="flag debug")
@click.option("--wait-timeout", default=None, help="Waiting timeout (in seconds)")
def lab_up(state, from_module, wait_timeout):
    """ Create a VM instance for jupyter """
    jup = _load_jupyter(state)

    with progress:
        task = progress.add_task("Starting lab creation")
        cfg = jupyter.load_conf_module(from_module)
        rsp = jup.create_lab(cfg.INSTANCE, volume=cfg.VOLUME)
        jup.push()
    console.print("=> [green]Lab created[/]")
    console.print("Go to: ")
    console.print(f"\t [magenta]https://{rsp.url}[/]")
    console.print(f"\t Token: [red]{rsp.token}[/]")
    if wait_timeout:
        console.print(
            "=> Now we need to wait until the service is avaialable")
        code = -1
        with progress:
            task = progress.add_task(
                "Checking readiness of JupyterLab service")
            code = check_readiness(rsp.url, int(wait_timeout))

        if code == 200:
            console.print("=> [green]Congratulations Lab is ready[/]")
        else:
            console.print(
                f"[orange] {rsp.url} still not available, code {code}[/]")


@cli.command(name="fetch")
@click.option("--state", "-s", default=None,
              help="Where state will be stored")
@click.option("--output", "-o", default=None,
              help="Path to record state")
def fetch(state, output):
    """ fetch new objects from the provider """
    jup = _load_jupyter(state)
    with progress:
        task1 = progress.add_task("Fetching new objects from cloud")
        _dict = jup.fetch(console)
    print_json(data=_dict)
    if output:
        with open(output, "w") as f:
            f.write(json.dumps(_dict))
    jup.push()


@cli.command(name="destroy")
@click.option("--state", "-s", default=None,
              help="Where state lives")
def destroy(state):
    """It will destroy a lab """
    jup = _load_jupyter(state)
    with progress:
        task1 = progress.add_task(
            f"[red]Destroying jupyter {jup._state.url}[/]")
        jup.destroy_lab()
        jup.push()


@volumes.command(name="create")
@click.option("--size", "-S", default="10", help="Volume size")
@click.option("--name", "-n", required=True, help="Volume name")
@click.option("--kind", "-k", default="pd-standard", help="Volume type")
@click.option("--state", "-s", default=None,
              help="Where state will be stored")
def volume_create(state, size, name, kind):
    """ create a volume """
    jup = _load_jupyter(state)
    if not jup.check_volume(name):
        console.print("=> Creating new volume")
        jup.create_volume(name, size=size, storage_type=kind)
        jup.push()
        console.print("=> Volume created")
    else:
        console.print("[x] Volume already exists")


@volumes.command(name="list")
@click.option("--state", "-s", default=None,
              help="Where state will be stored")
@click.option("--get-all", "-g", is_flag=True, default=False,
              help="Get all volumes")
def volume_list(state, get_all):
    """ list volumes """
    jup = _load_jupyter(state)
    if get_all:
        vols = jup.prov.list_volumes()
    else:
        vols = jup._state.volumes.values()
    table = Table(title=f"Volumes")

    table.add_column("name", justify="left")
    table.add_column("size", justify="right")
    table.add_column("location", justify="right")
    table.add_column("kind", justify="right")
    table.add_column("status", justify="right")
    for vol in vols:
        table.add_row(vol.name, vol.size, vol.location,
                      vol.storage_type, vol.status)

    console.print(table)


@volumes.command(name="import")
@click.option("--state", "-s", default=None,
              help="Where state will be stored")
@click.option("--name", "-n", required=True,
              help="Name of the volume")
def volume_import(state, name):
    """ import a disk from the provider into jupyter """
    jup = _load_jupyter(state)
    jup.import_volume(name)
    jup.push()
    console.print(f"Volume {name} imported.")


@volumes.command(name="unlink")
@click.option("--state", "-s", default=None,
              help="Where state will be stored")
@click.option("--name", "-n", required=True,
              help="Name of the volume")
def volume_unlink(state, name):
    """ unlink a volume from this project """
    jup = _load_jupyter(state)
    if jup._state.volumes.get(name):
        del(jup._state.volumes[name])
        jup.push()
        console.print(f"Volume {name} unlinked.")


@volumes.command(name="resize")
@click.option("--state", "-s", default=None,
              help="Where state will be stored")
@click.option("--name", "-n", required=True,
              help="Name of the volume")
@click.option("--size", "-S", required=True,
              help="New size of the volume")
def volume_resize(state, name, size):
    """ resize a volume """
    jup = _load_jupyter(state)
    res = jup.resize_volume(name, size)
    if res:
        jup.push()
        console.print(f"[green]Volume {name} resized.[/]")
    else:
        console.print(f"[red]Volume {name} resize fail.[/]")


@volumes.command(name="destroy")
@click.option("--state", "-s", default=None,
              help="Where state will be stored")
@click.option("--name", "-n", required=True,
              help="Name of the volume")
def volume_destroy(state, name):
    """ resize a volume """
    jup = _load_jupyter(state)
    _confirm = Confirm.ask(f"Do you want to destroy {name} volume?")
    if _confirm:
        res = jup.destroy_volume(name)
        if res:
            jup.push()
            console.print(f"[green]Volume {name} destroyed.[/]")
        else:
            console.print(f"[red]Volume {name} destroy failed.[/]")


@cli.command(name="clean")
@click.option("--state", "-s", default=None,
              help="Where state will be stored")
def clean_state_cmd(state):
    """ Will remove the state file """
    jup = _load_jupyter(state)
    _confirm = Confirm.ask(f"Do you want to remove the state from {_state}?")
    if _confirm:
        clean_state(_state)
        Path(defaults.JUPCTL_CONF).unlink()
        console.print(f"[green]State deleted from {_state}[/]")


@cli.command(name="wait")
@click.option("--timeout", "-t", default=10 * 60,
              help="Timeout (in seconds)")
@click.argument("url")
def wait_for_jupyter(timeout, url):
    """ Wait for jupyter to be ready """
    with progress:
        task = progress.add_task("Waiting for jupyter lab")
        code = check_readiness(url, timeout)
    if code == 200:
        console.print(f"[green]{url} Ready[/]")
    else:
        console.print(f"[orange] {url} not avaialable, code: {code}[/]")


@cli.command(name="status")
@click.option("--state", "-s", default=None,
              help="Where state will be stored")
@click.option("--output", "-o", default=None,
              help="Path to record state")
def show_state(state, output):
    """ Shows state """
    jup = _load_jupyter(state)
    console.print_json(data=jup._state.dict())
    if output:
        with open(output, "w") as f:
            f.write(json.dumps(_dict))


@cli.command(name="push")
@click.option("--from-file", "-f", default="state.json",
              help="Path to record state")
def push_state_cli(state, from_file):
    """ Push state """
    with open(from_file, "w") as f:
        jdata = json.loads(f.read())
    _state = JupyterState(**jdata)
    push_state(_state)
    console.print(f"State {from_file} pushed to {_state.self_link}")


@cli.command(name="list-containers")
@click.option("--name", "-n", default=None,
              help="repo name")
@click.option("--project", "-p", default=None,
              help="project of the repo")
@click.option("--location", "-l", default=None,
              help="location")
def list_containers(name, project, location):
    """ list containers """
    from labmachine.providers.google.artifacts import Artifacts
    art = Artifacts(keyvar=defaults.JUP_COMPUTE_KEY)

    containers = art.list_docker_images(
        repo_name=name, project=project, location=location)
    # console.print(res)
    table = Table(title=f"Containers")

    table.add_column("name", justify="left")
    table.add_column("tags", justify="right")
    table.add_column("size", justify="right")
    table.add_column("uri", justify="right")
    for con in containers:
        table.add_row(con.name,
                      ",".join(con.tags),
                      convert_size(con.image_size_bytes),
                      con.uri,
                      )
    console.print(table)


cli.add_command(volumes)

if __name__ == "__main__":

    cli()
