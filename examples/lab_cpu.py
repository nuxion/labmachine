import os

from labmachine.jupyter import JupyterInstance, JupyterVolume

STATE_PATH = "state.json"

VOLUME = JupyterVolume(
    name="testing-data",
    size="10",
    labels={"project": "default"}
)

INSTANCE = JupyterInstance(
    container="jupyter/minimal-notebook:python-3.10.6",
    instance_type="e2-micro",
    volume_data=VOLUME.name,
    boot_image="lab-minimal-010",
    account=os.getenv("SA_ACCOUNT"),
    roles=["cloud-platform"],
    debug=True,
)

