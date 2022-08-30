from labmachine.jupyter import JupyterController
from labmachine.providers.google import GCEProvider, GoogleDNS

def load_jupyter(fpath) -> JupyterController:
    """ TODO: provider should be infered from state """
    g = GCEProvider()
    dns = GoogleDNS()
    jup = JupyterController.from_state(fpath, compute=g, dns=dns)
    return jup


