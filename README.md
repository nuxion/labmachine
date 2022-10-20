# labmachine

This is a POC with two purposes: refactoring a cluster package from [labfunctions](github.com/labfunctions/labfunctions) and allowing the creation and self registering of a jupyter instance.

This work was inpired by [Let Deep Learning VMs and Jupyter notebooks burn the midnight oil for you](https://cloud.google.com/blog/products/ai-machine-learning/let-deep-learning-vms-and-jupyter-notebooks-to-burn-the-midnight-oil-for-you-robust-and-automated-training-with-papermill)

Right now only works for Google Cloud but should be easy to expand to other providers. 


For examples, see [examples](examples/)

See `infra_[cpu|gpu].py` and `lab_[cpu|gpu].py`

`infra_*` files are raw implementacion of the cluster library.

Lab files are abstractions built over this library for jupyter lab provisioning.

## Features

- VM creation (Google)
- Jupyter on docker
- SSL certificates (ZeroSSL & Caddy)
- Volumes managments (Creation, Resizing, deletion, formating, etc)
- DNS A record creation (Google, Cloudflare)
- Automatic shutdown by inactivity (by Jupyter)
- GPU Provisioning (nvidia-smi installation, docker configuration, etc)
- Linux image creation (Packer)
- Entities types for autocompletion
- Logging into cloud provider log service

# Documentation

- [Quickstart](docs/quickstart.md)
- [Permissions](docs/permissions.md)
- [Volumes](docs/volumes.md)


## Next work

See https://trello.com/b/F2Smw3QO/labmachine

