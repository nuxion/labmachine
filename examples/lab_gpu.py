import os

from labmachine.jupyter import JupyterInstance, JupyterVolume

STATE_PATH = "state.json"
VOLUME = JupyterVolume(
    name="testing-data",
    size="10",
    labels={"project": "example"}
)
INSTANCE = JupyterInstance(
    container="nuxion/minimal-jupyter-gpu:0.1.0-cuda11.5",
    instance_type="n1-standard-1",
    volume_data=VOLUME.name,
    gpu="nvidia-tesla-t4",
    boot_image="lab-minimal-010-gpu",
    boot_size="20",
    debug=True,
)
