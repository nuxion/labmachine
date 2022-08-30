import argparse
import atexit
import json
import os
import pathlib
import re
import shlex
import subprocess
import sys
from datetime import datetime
from enum import Enum, auto
from typing import Optional

ENV_DIR = os.getenv("LAB_DIR", "/opt/lab")

INSTALLER_DIR = pathlib.Path(ENV_DIR)
INSTALLER_DIR.mkdir(parents=True, exist_ok=True)


class Logger:
    STDOUT_LOG = INSTALLER_DIR / "out.log"
    STDOUT_LOG_F = None
    STDERR_LOG = INSTALLER_DIR / "err.log"
    STDERR_LOG_F = None

    @classmethod
    def close_logs(cls):
        if cls.STDOUT_LOG_F:
            cls.STDOUT_LOG_F.close()

        if cls.STDERR_LOG_F:
            cls.STDERR_LOG_F.close()

    @classmethod
    def setup_log_dir(cls):
        """
        Create the LOG_DIR path and STD(OUT|ERR)_LOG files.
        """
        cls.STDOUT_LOG.touch(exist_ok=True)
        cls.STDERR_LOG.touch(exist_ok=True)

        cls.STDOUT_LOG_F = open(cls.STDOUT_LOG, mode="a")
        cls.STDERR_LOG_F = open(cls.STDERR_LOG, mode="a")

        atexit.register(cls.close_logs)

    @classmethod
    def print_out(cls, msg: str, end=os.linesep, print_=True):
        if cls.STDOUT_LOG_F:
            cls.STDOUT_LOG_F.write(msg + end)
            cls.STDOUT_LOG_F.flush()
        if print_:
            print(msg, end=end, file=sys.stdout)

    @classmethod
    def print_err(cls, msg: str, end=os.linesep, print_=True):
        if cls.STDERR_LOG_F:
            cls.STDERR_LOG_F.write(msg + end)
            cls.STDERR_LOG_F.flush()
        if print_:
            print(msg, end=end, file=sys.stderr)


print_out = Logger.print_out
print_err = Logger.print_err


def run(
    command: str, check=True, input=None, cwd=None, silent=False,
        environment=None
) -> subprocess.CompletedProcess:
    """
    Runs a provided command, streaming its output to the log files.
    :param command: A command to be executed, as a single string.
    :param check: If true, will throw exception on failure (exit code != 0)
    :param input: Input for the executed command.
    :param cwd: Directory in which to execute the command.
    :param silent: If set to True, the output of command won't be logged or
    printed.
    :param environment: A set of environment variable for the process to use.
    If None, the current env is inherited.
    :return: CompletedProcess instance - the result of the command execution.
    """
    if not silent:
        log_msg = (
            f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
            f"Executing: {command}" + os.linesep
        )
        print_out(log_msg)
        print_err(log_msg, print_=False)

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
        print_err(proc.stderr.decode())
        print_out(proc.stdout.decode())

    return proc


def check_python_version():
    """
    Makes sure that the script is run with Python 3.6 or newer.
    """
    if sys.version_info.major == 3 and sys.version_info.minor >= 6:
        return
    version = "{}.{}".format(sys.version_info.major, sys.version_info.minor)
    raise RuntimeError(
        "Unsupported Python version {}. "
        "Supported versions: 3.6 - 3.10".format(version)
    )


def check_docker():
    """
    Makes sure that the script is run with Python 3.6 or newer.
    """
    res = run("docker --version", check=False)
    if not res:
        print_err(f"Docker: {res}")
        return False
    print_out(f"Docker: {res}")
    return True

def install_docker():
    run("curl -Ls https://raw.githubusercontent.com/nuxion/cloudscripts/1442b4a3cbf027e64b9b58e453fb06c480fe3414/install.sh | sh"),
    run("sudo cscli -i docker")

def install_caddy():
    pass


def parse_args():
    """
    MIRROR = os.getenv("LF_MIRROR")  # with protocol
    REGISTRY = os.getenv("LF_REGISTRY")  # without protocol
    INSECURE = os.getenv("LF_INSECURE")  # yes or empty
    IMAGE = os.getenv("LF_DOCKER_IMG")  # fullname: nuxion/labfunctions
    VERSION = os.getenv("LF_DOCKER_VER")  # version
    """

    parser = argparse.ArgumentParser(description="Prepare node for lab agent")
    parser.add_argument("action", choices=[
                        "install"], default="install", nargs="?")
    parser.add_argument("--registry", help="registry url without protocol")
    parser.add_argument("--mirror", help="fullurl of a docker mirror")
    parser.add_argument(
        "--image",
        default="nuxion/labfunctions",
        help="fullimage name: nuxion/labfunctions",
    )
    parser.add_argument(
        "--version", default="0.9.0-alpha.11", help="tag version of the image"
    )
    parser.add_argument("--insecure", help="if the registry has https or not")

    args = parser.parse_args()

    return args
