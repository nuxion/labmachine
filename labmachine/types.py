from binascii import crc32
from typing import Any, Dict, List, NewType, Optional, Set, Tuple, Union

from pydantic import BaseModel, BaseSettings

ExtraField = NewType("ExtraField", Dict[str, Any])
AGENT_HOMEDIR = "/home/op"
USER = "op"
DOCKER_UID = "1000"
DOCKER_GID = "997"
AGENT_DOCKER_IMG = "nuxion/labfunctions"


class Permissions(BaseModel):
    account: str
    roles: Optional[List[str]] = None


class InstanceType(BaseModel):
    name: str
    cpu: int
    ram: int
    gpu: Optional[str] = None
    desc: Optional[str] = None
    price: Optional[float] = None


class DNSRecord(BaseModel):
    zoneid: str
    record_type: str
    data: List[str]
    id: Optional[str] = None
    name: Optional[str] = None
    ttl: int = 14400  # 4 hours for an update
    extra: Optional[ExtraField] = None


class DNSZone(BaseModel):
    domain: str
    zone_type: str = "master"
    ttl: Optional[int] = None
    id: Optional[str] = None
    extra: Optional[ExtraField] = None


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

    def __hash__(self):
        return crc32(self.id.encode())


class AttachStorage(BaseModel):
    """
    :param disk_name: as resource
    :param mode: Either READ ONLY or READ_WRITE
    :param device_name: Name with which the attached disk will be accessible
    under /dev/disk/by-id/google-*
    :param auto_delete:  If set, the disk will be auto-deleted
    if the parent node/instance is deleted.
    It could depends on the provider also.
    :param as_boot: If true disk will be attached as boot disk.
    It could depends on the provider.
    """
    disk_name: str
    mode: str
    device_name: Optional[str] = None
    auto_delete: bool = False
    as_boot: bool = False


class StorageRequest(BaseModel):
    """
    A generic representation of a disk, potentially the mount_point could
    be used to identify if this will be a boot disk (needed in GCE)
    """

    name: str
    size: Union[int, str]
    location: str
    snapshot: Optional[str] = None
    labels: Dict[str, Any] = {"mount": "/"}
    description: Optional[str] = None
    storage_type: Optional[str] = None
    extra: Optional[ExtraField] = None


class SSHKey(BaseModel):
    """
    It represents a SSHKey configuration,
    it will have the paths to public and private key
    and user associated to that key
    """

    public_path: str
    private_path: Optional[str] = None
    user: str = "op"


class GPURequest(BaseModel):
    """A generic representation of GPU resource"""

    name: str
    gpu_type: str
    count: int = 1
    extra: Optional[ExtraField] = None


class VMInstance(BaseModel):
    vm_id: str
    vm_name: str
    location: str
    state: str
    private_ips: List[str]
    public_ips: Optional[List[str]] = None
    permissions: Optional[Permissions] = None
    volumes: List[str] = []
    labels: Dict[str, Any] = {}
    tags: List[str] = []
    pool: str = "default"
    extra: Optional[ExtraField] = None


class SSHResult(BaseModel):
    command: str
    return_code: int
    stderror: str = ""
    stdout: str = ""


class BootDiskRequest(BaseModel):
    """
    :param image: image to be used like debian or custom
    is build as `machine-type`-`random_id`
    """

    image: str
    size: str
    disk_type: str
    auto_delete: bool = True


class VMRequest(BaseModel):
    """
    Machine Request definition, this will be used as a request to
    create a machine


    :param name: Name of the machine
    :param instance_type: vm type in the vendor cloud parlance
    :param location: a general term to refer to location,
    cloud providers could use zone, region or both
    :param provider: name of the provider to be used
    :param boot: Different providers has different strategies, but the idea
    is that any machine will need a boot disk with some params.
    :param preemptible: use inestable instances or fixed
    (spot instance in aws, preemptible in gcp)
    :param metadata: metadata tag to be used for the server
    :param startup_script: Startup script to be used.
    Implementation could change between providers.
    :param ssh_public_cert: certificate to be added to authorized_keys
    in the remote host, this should be the string version of the certificate.
    :param ssh_user: to which user allow access.
    :param attached_disks: Disks to be attached after machine creation
    :param gpu: Optional GPU resource
    :param network: virtual network to configurate
    :param labels:  cluster and other properties to be used
    :param tags:  cluster and other properties to be used
    :param external_ip: the external IP address to use. If ‘dynamic’ (default)
    is up to the provider to asign an ip address. If ‘None’,
    then no external address will be used.
    :param internal_ip: the external IP address to use. If ‘dynamic’ (default)
    is up to the provider to asign an ip address. If ‘None’,
    then no external address will be used.
    :param extra: you should try not to use it, but is here as a safeguard
    for any edge case.

    """
    name: str
    instance_type: str  # size
    location: str
    provider: str
    boot: BootDiskRequest
    preemptible: bool = False
    metadata: Dict[str, Any] = {}
    startup_script: Optional[str] = None
    ssh_user: Optional[str] = None
    ssh_public_cert: Optional[str]
    permissions: Optional[Permissions] = None
    network: str = "default"
    internal_ip: Union[str, None] = None
    external_ip: Union[str, None] = None
    attached_disks: List[AttachStorage] = []
    gpu: Optional[GPURequest] = None
    labels: Dict[str, Any] = {}
    tags: Optional[List[str]] = None
    extra: Optional[ExtraField] = None
