from typing import Any, Dict, List, NewType, Optional, Set, Tuple, Union

from pydantic import BaseModel, BaseSettings

ExtraField = NewType("ExtraField", Dict[str, Any])
AGENT_HOMEDIR = "/home/op"
USER = "op"
DOCKER_UID = "1000"
DOCKER_GID = "997"
AGENT_DOCKER_IMG = "nuxion/labfunctions"


class BlockStorage(BaseModel):
    id: str
    name: str
    size: str
    location: str
    status: str
    mount: Optional[str]
    source_image: Optional[str] = None
    description: Optional[str] = None
    storage_type: Optional[str] = None
    labels: Dict[str, Any] = {}
    extra: Optional[ExtraField] = None


class StorageRequest(BaseModel):
    """
    A generic representation of a disk, potentially the mount_point could
    be used to identify if this will be a boot disk (needed in GCE)
    """

    name: str
    size: Union[int, str]
    location: str
    mount: str = "/"
    auto_delete: bool = False
    create_if_not_exist: bool = False
    snapshot: Optional[str] = None
    image: Optional[str] = None
    labels: Dict[str, Any] = {"mount": "/"}
    permissions: Optional[List[str]] = None
    description: Optional[str] = None
    storage_type: Optional[str] = None
    extra: Optional[ExtraField] = None


# class BlockStorage(BaseModel):
#     """
#     A generic representation of a disk, potentially the mount_point could
#     be used to identify if this will be a boot disk (needed in GCE)
#     """
# 
#     name: str
#     size: Union[int, str]
#     location: str
#     mount: str = "/mnt/disk0"
#     create_if_not_exist: bool = False
#     snapshot: Optional[str] = None
#     image: Optional[str] = None
#     permissions: Optional[List[str]] = None
#     description: Optional[str] = None
#     kind: Optional[str] = None
#     extra: Optional[ExtraField] = None


class SSHKey(BaseModel):
    """
    It represents a SSHKey configuration,
    it will have the paths to public and private key
    and user associated to that key
    """

    public_path: str
    private_path: Optional[str] = None
    user: str = "op"


class MachineGPU(BaseModel):
    """A generic representation of GPU resource"""

    name: str
    gpu_type: str
    count: int = 1
    extra: ExtraField


class MachineInstance(BaseModel):
    machine_id: str
    machine_name: str
    location: str
    state: str
    private_ips: List[str]
    public_ips: List[str] = []
    volumes: List[str] = []
    labels: Dict[str, Any] = {}
    tags: List[str] = []
    pool: str = "default"
    extra: Optional[ExtraField] = None


class BlockInstance(BaseModel):
    id: str
    name: str
    size: Union[int, str]
    location: str
    mount: Optional[str] = None
    snapshot: Optional[str] = None
    image: Optional[str] = None
    permissions: Optional[List[str]] = None
    description: Optional[str] = None
    kind: Optional[str] = None
    extra: Optional[ExtraField] = None


class SSHResult(BaseModel):
    command: str
    return_code: int
    stderror: str = ""
    stdout: str = ""


class MachineRequest(BaseModel):
    """
    Machine Request definition, this will be used as a request to
    create a machine


    :param image: image to be used like debian or custom
    is build as `machine-type`-`random_id`
    :param instance_type: node type in the vendor cloud parlance
    :param location: a general term, cloud providers could use zone, region or both
    :param provider: provider name to be used
    :param name: Name of the machine
    :param startup_script: Startup cript to be used.
    :param volumes: Disks to be attached to the machine creation
    :param gpu: Optional GPU resource
    :param ssh_public_cert: certificate to be added to authorized_keys
    in the remote host, this should be the string version of the certificate.
    :param ssh_user: to which user allow access.
    :param network: virtual network to configurate
    :param labels:  cluster and other properties to be used
    :param tags:  cluster and other properties to be used
    :param external_ip: the external IP address to use. If ‘dynamic’ (default)
    is up to the provider to asign an ip address. If ‘None’,
    then no external address will be used.
    :param internal_ip: the external IP address to use. If ‘dynamic’ (default)
    is up to the provider to asign an ip address. If ‘None’,
    then no external address will be used.
    :param extra: you should try not to use it, but is here as backup for any edge case.

    """
    name: str
    instance_type: str  # size
    location: str
    provider: str
    image: Optional[str] = None
    startup_script: Optional[str] = None
    internal_ip: Union[str, None] = "dynamic"
    external_ip: Union[str, None] = "dynamic"
    volumes: List[StorageRequest] = []
    gpu: Optional[MachineGPU] = None
