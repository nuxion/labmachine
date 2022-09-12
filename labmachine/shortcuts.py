from labmachine import jupyter


def controller_from_state(fpath) -> jupyter.JupyterController:
    jup = JupyterController.from_state(fpath, compute=g, dns=dns)
    return jup


def lab_from_module(settings_module: str) -> jupyter.LabResponse:
    cfg = jupyter.load_jupyter_conf(settings_module)
    jup = jupyter.JupyterController.from_state(cfg.STATE_PATH)

    if cfg.VOLUME and not jup.check_volume(cfg.VOLUME.name):
        jup.create_volume(cfg.VOLUME.name, size=cfg.VOLUME.size)
        jup.push()
    rsp = jup.create_lab(**cfg.INSTANCE.dict())
    jup.push()
    return rsp
