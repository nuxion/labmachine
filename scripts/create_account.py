import argparse
import os
import shlex
import subprocess
from datetime import datetime
import sys

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
    args = parser.parse_args()

    return args


def main():
    args = parse_args()
    create_cmd = (f"gcloud iam service-accounts create {args.name} "
                  f"--description='Jupyter Lab Creator' "
                  f"--display-name={args.name}")

    sa_check_cmd = f'gcloud iam service-accounts list --filter="name:{args.name}" --format="json"'
    res = run(sa_check_cmd)
    if res.stdout.decode().strip() != "[]":
        print(f"SA Account {args.name} already exist")
        sys.exit(-1)

    run(create_cmd)
    for role in FULL_ROLES:
        bind_role_cmd = (f"gcloud projects add-iam-policy-binding {args.project} "
                         f"--member='serviceAccount:{args.name}@{args.project}.iam.gserviceaccount.com' "
                         f"--role={role} "
                         )
        run(bind_role_cmd)


if __name__ == "__main__":
    main()
