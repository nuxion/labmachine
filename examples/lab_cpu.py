import os

from labmachine.jupyter import JupyterInstance, JupyterVolume

STATE_PATH = "gs://nbworkflows/test/state4.json"

VOLUME = JupyterVolume(
    name="testing-data",
    size="10",
    labels={"project": "example"}
)
INSTANCE = JupyterInstance(
    container="jupyter/minimal-notebook:python-3.10.6",
    instance_type="e2-micro",
    volume_data=VOLUME.name,
    boot_image="lab-minimal-010",
    debug=True,
)
