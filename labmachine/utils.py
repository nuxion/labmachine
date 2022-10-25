import asyncio
import math
import os
from importlib import import_module
from pathlib import Path
from typing import Any, Dict

import tomli
import tomli_w
from nanoid import generate
import os
import shlex
import subprocess
import logging



from labmachine.defaults import NANO_ID_ALPHABET


def generate_random(size=10, strategy="nanoid", alphabet=NANO_ID_ALPHABET) -> str:
    """Default URLSafe id"""
    if strategy == "nanoid":
        return generate(alphabet=alphabet, size=size)
    raise NotImplementedError("Strategy %s not implemented", strategy)


async def run_async(func, *args, **kwargs):
    """Run sync functions from async code"""
    loop = asyncio.get_running_loop()
    rsp = await loop.run_in_executor(None, func, *args, **kwargs)
    return rsp


def mkdir_p(fp):
    """Make the fullpath
    similar to mkdir -p in unix systems.
    """
    Path(fp).mkdir(parents=True, exist_ok=True)


def get_class(fullclass_path):
    """get a class or object from a module. The fullclass_path should be passed as:
    package.my_module.MyClass
    """
    module, class_ = fullclass_path.rsplit(".", maxsplit=1)
    mod = import_module(module)
    cls = getattr(mod, class_)
    return cls


def write_toml(fpath, data: Dict[Any, Any]):
    with open(fpath, "wb") as f:
        tomli_w.dump(data, f)


def read_toml(fpath) -> Dict[Any, Any]:
    with open(fpath, "r") as f:
        data = tomli.loads(f.read())
        return data


def convert_size(size_bytes):
    if size_bytes == 0:
        return "0B"
    size_name = ("B", "KB", "MB", "GB", "TB", "PB", "EB", "ZB", "YB")
    i = int(math.floor(math.log(size_bytes, 1024)))
    p = math.pow(1024, i)
    s = round(size_bytes / p, 2)
    return "%s %s" % (s, size_name[i])


def from_path_to_module_str(fp) -> str:
    """ experimental:
    from "examples/model.py" it should return
    "example.model"
    """
    return fp.rsplit(".", maxsplit=1)[0].replace("/", ".")


def shell(
        command: str, check=True, input=None, cwd=None, silent=False, env=None, shell_=False,
) -> subprocess.CompletedProcess:
    """
    Runs a provided command, streaming its output to the log files.
    :param command: A command to be executed, as a single string.
    :param check: If true, will throw exception on failure (exit code != 0)
    :param input: Input for the executed command.
    :param cwd: Directory in which to execute the command.
    :param silent: If set to True, the output of command won't be logged or printed.
    :param env: A set of environment variable for the process to use. If None, the current env is inherited.
    :return: CompletedProcess instance - the result of the command execution.
    """
    if not silent:
        log_msg = "Executing: {command}"
        # log_msg = (
        #     f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] "
        #     f"Executing: {command}" + os.linesep
        # )
        # print(log_msg)
        # print(log_msg)
        logging.info(log_msg)

    proc = subprocess.run(
        shlex.split(command),
        check=check,
        shell=shell_,
        stderr=subprocess.PIPE,
        stdout=subprocess.PIPE,
        input=input,
        cwd=cwd,
        env=env,
    )

    if not silent:
        if proc.stderr.decode():
            logging.error(proc.stderr.decode())
        if proc.stdout.decode():
            logging.info(proc.stdout.decode())
        # print(proc.stderr.decode())
        # print(proc.stdout.decode())

    return proc


