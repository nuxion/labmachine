from labmachine.jupyter import JupyterController


def load_jupyter(fpath) -> JupyterController:
    jup = JupyterController.from_state(fpath, compute=g, dns=dns)
    return jup
