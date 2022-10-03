import argparse
import json
import os
import shlex
import subprocess
import sys
from datetime import datetime

FULL_ROLES = [
    "roles/artifactregistry.reader",
    "roles/compute.instanceAdmin.v1",
    "roles/dns.admin",
    "roles/iam.serviceAccountTokenCreator",
    "roles/iam.serviceAccountUser",
    "roles/storage.admin",
    "roles/storage.objectAdmin",
]


def run(
    command: str, check=True, input=None, cwd=None, silent=False, environment=None
) -> subprocess.CompletedProcess:
    """
    Runs a provided command, streaming its output to the log files.
    :param command: A command to be executed, as a single string.
    :param check: If true, will throw exception on failure (exit code != 0)
    :param input: Input for the executed command.
    :param cwd: Directory in which to execute the command.
    :param silent: If set to True, the output of command won't be logged or printed.
    :param environment: A set of environment variable for the process to use.
    If None, the current env is inherited.
    :return: CompletedProcess instance - the result of the command execution.
    """
    if not silent:
        log_msg = (
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
            f"Executing: {command}" + os.linesep
        )
        print(log_msg)

    proc = subprocess.run(
        shlex.split(command),
        check=check,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        input=input,
        cwd=cwd,
        env=environment,
    )

    if not silent:
        print(proc.stdout.decode())

    return proc


def parse_args():
    """
    """

    parser = argparse.ArgumentParser(
        description="Prepare SA Account for labctl")
    parser.add_argument("--project", help="Project where it will be created")
    parser.add_argument("--name", help="Name of the account")
    parser.add_argument("--bucket", help="Name of the bucket to be created")
    parser.add_argument("--network", default="default",
                        help="Name of the network for the firewall")
    args = parser.parse_args()

    return args


def assign_roles(args):
    print(f"Assigning roles to {args.name}")
    for role in FULL_ROLES:
        bind_role_cmd = (f"gcloud projects add-iam-policy-binding {args.project} "
                         f"--member='serviceAccount:{args.name}@{args.project}.iam.gserviceaccount.com' "
                         f"--role={role} "
                         )
        run(bind_role_cmd, silent=True)


def create_bucket(args):
    res = run(f"gsutil ls gs://{args.bucket}", silent=True, check=False)
    if res.returncode == 1:
        print(f"Creating bucket {args.bucket}")
        run(f"gcloud alpha storage bucket create gs://{args.bucket}")
    else:
        print(f"Bucket gs://{args.bucket} already exist")


def create_firewall(args):
    firewall_cmd = (f"gcloud compute --project={args.project} firewall-rules create default-allow-http "
                    f"--description='http and https' --direction=INGRESS --priority=1000 "
                    f"--network={args.network} --action=ALLOW --rules=tcp:80,tcp:443 "
                    f"--source-ranges=0.0.0.0/0 --target-tags=http-server")

    firewall_check = "gcloud compute firewall-rules list --format=json"
    res = run(firewall_check, silent=True, check=False)
    data = json.loads(res.stdout)
    firewall_created = False
    for rule in data:
        if rule.get("name") == "default-allow-http":
            firewall_created = True
    if not firewall_created:
        print(f"Creating firewall for tcp:80,443 for network {args.network}")
        run(firewall_cmd)
    else:
        print("Firewall already exist for tcp:80,443")


def main():
    args = parse_args()
    create_cmd = (f"gcloud iam service-accounts create {args.name} "
                  f"--description='Jupyter Lab Creator' "
                  f"--display-name={args.name}")

    sa_check_cmd = f'gcloud iam service-accounts list --filter="name:{args.name}" --format="json"'
    res = run(sa_check_cmd)
    if res.stdout.decode().strip() != "[]":
        print(f"SA Account {args.name} already exist")
    else:
        print(f"Creating SA Account {args.name}")
        run(create_cmd)
        asign_roles(args)

    create_bucket(args)
    create_firewall(args)


if __name__ == "__main__":
    main()
