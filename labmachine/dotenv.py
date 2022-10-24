import os
from typing import Dict, List

from labmachine.defaults import ENVS_FILES


def _clean_value(v: str) -> str:
    _v = v.split("#", maxsplit=1)[0]
    _v = _v.replace("'", "")
    _v = _v.replace('"', "")
    return _v.strip()


def get_envs(env_file: str) -> Dict[str, str]:
    """ it's open and parse a given file looking for variables definitions
    in the type of:

       key = value

    it will ignore lines starting with #
    it will strip out any space or any quotation mark.

    """

    _envs = {}
    with open(env_file, "r") as f:
        lines = f.readlines()
        for line in lines:
            if not line.startswith("#"):
                try:
                    k, v = line.split("=", maxsplit=1)
                except ValueError:
                    pass
                k = k.strip()
                v = _clean_value(v)
                _envs[k] = v
    return _envs


def load_envs(env_file: str) -> Dict[str, str]:
    """ it open, parse and load in the runtime enviroment any variable
    found in a file """

    _envs = {}

    try:
        _envs = get_envs(env_file)
        for k, v in _envs.items():
            os.environ[k] = v
    except FileNotFoundError as e:
        pass
    
    return _envs

def default(env_files: List[str] = ENVS_FILES) -> Dict[str, str]:
    """
    It will open a list of files on load them into the environment.

    By default ".env", ".env.dev", ".env.test", ".env.prod"

    Files are open in strict order, so if a variable is repeated it will keep
    the last found
    """

    final = {}
    for file_ in env_files:
        _envs = load_envs(file_)
        final.update(_envs)
    return final
