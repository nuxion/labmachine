import asyncio
import math
import os
from importlib import import_module
from pathlib import Path
from typing import Any, Dict

import tomli
import tomli_w
from nanoid import generate

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
