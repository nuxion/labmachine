import io
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, Generator, List, Optional, Union

from labmachine import types

# from .types import (AttachStorage, BlockStorage, Bucket, DNSRecord, DNSZone,
#                    StorageRequest, VMInstance, VMRequest)


class ComputeSpec(ABC):
    """
    Interface definition of a cloud provider.

    :param providerid: an unique identifier for the provider

    """
    providerid: str
    keyvar: str

    def __init__(self, keyvar: str):
        self.keyvar = keyvar

    @abstractmethod
    def get_vm(self, vm_name: str, location: Optional[str] = None) \
            -> types.VMInstance:
        pass

    @abstractmethod
    def create_vm(self, vm: types.VMRequest) -> types.VMInstance:
        pass

    @abstractmethod
    def destroy_vm(self, vm: Union[str, types.VMInstance],
                   location: Optional[str] = None):
        pass

    @abstractmethod
    def list_vms(
        self, location: Optional[str] = None, tags: Optional[List[str]] = None
    ) -> List[types.VMInstance]:
        pass

    @abstractmethod
    def get_volume(self, vol_name) -> Union[types.BlockStorage, None]:
        pass

    @abstractmethod
    def create_volume(self, disk: types.StorageRequest) -> types.BlockStorage:
        pass

    @abstractmethod
    def resize_volume(self, name: str, size: str,
                      location: Optional[str] = None) -> bool:
        pass

    @abstractmethod
    def destroy_volume(self, disk: str, location: Optional[str] = None) -> bool:
        pass

    @abstractmethod
    def attach_volume(self, vm: str, attach: types.AttachStorage,
                      location: Optional[str] = None) -> bool:
        pass

    @abstractmethod
    def detach_volume(self, vm: str, disk: str,
                      location: Optional[str] = None) -> bool:
        pass

    @abstractmethod
    def list_volumes(self, location: Optional[str] = None) \
            -> List[types.BlockStorage]:
        pass


class DNSSpec(ABC):
    providerid: str
    keyvar: str

    def __init__(self, keyvar: str):
        self.keyvar = keyvar

    @abstractmethod
    def get_zone(self, zoneid: str):
        pass

    @abstractmethod
    def create_zone(self, zone: types.DNSZone):
        pass

    @abstractmethod
    def list_zones(self) -> List[types.DNSZone]:
        pass

    @abstractmethod
    def get_record(self, zoneid: str, recordid: str) -> types.DNSRecord:
        pass

    @abstractmethod
    def list_records(self, zoneid: str) -> List[types.DNSRecord]:
        pass

    @abstractmethod
    def create_record(self, record: types.DNSRecord) -> Dict[str, Any]:
        pass

    @abstractmethod
    def delete_zone(self, zoneid: str):
        pass

    @abstractmethod
    def delete_record(self, zoneid: str, recordid: str) -> bool:
        pass


class StorageClasses(Enum):
    STANDARD = 0
    MEDIUM = 1
    LOW = 2
    ARCHIVE = 3


class Locations:
    pass


class StorageSpec(ABC):

    providerid: str
    keyvar: str
    filepath: Optional[str] = None

    def __init__(self, bucket=None, *,
                 keyvar: str = None,
                 filepath: str = None):
        self.keyvar = keyvar
        self.filepath = filepath
        if bucket:
            self.bucket: Bucket = self.set_bucket(name)

    @classmethod
    def from_env(cls, keyvar: Optional[str] = None) -> "StorageSpec":
        obj = cls(keyvar=keyvar)
        return obj

    @classmethod
    def from_file(cls, filepath: str) -> "StorageSpec":
        obj = cls(keyvar=None, filepath=filepath)
        return obj

    @abstractmethod
    def create_bucket(self,
                      name: str,
                      storage_class: str,
                      location: str,
                      versioning: bool,
                      labels: Optional[Dict[str, str]] = None) -> types.Bucket:
        raise NotImplementedError()

    @abstractmethod
    def set_bucket(self, name: str):
        raise NotImplementedError()

    @abstractmethod
    def enable_versioning(self, bucket: Optional[str] = None):
        raise NotImplementedError()

    @abstractmethod
    def disable_versioning(self, bucket: Optional[str] = None):
        raise NotImplementedError()

    @abstractmethod
    def make_private(self, bucket: Optional[str] = None):
        raise NotImplementedError()

    def make_public(self, bucket: Optional[str] = None):
        raise NotImplementedError()

    @abstractmethod
    def list_buckets(self, prefix: Optional[str] = None) -> List[types.Bucket]:
        pass

    def list_objects(self, prefix: Optional[str] = None,
                     max_results=None,
                     page_token=None, history: bool = False) -> List[types.Blob]:
        pass

    @abstractmethod
    def put_bytes(self, key: str, *, content: Union[bytes, io.BytesIO],
                  metadata: Optional[Dict[str, str]] = None) -> types.Blob:
        pass

    @abstractmethod
    def put_stream(self, key: str, generator: Generator[bytes, None, None],
                   metadata: Optional[Dict[str, str]] = None) -> bool:
        pass

    @abstractmethod
    def get_bytes(self, key: str, version=None) -> bytes:
        pass

    @abstractmethod
    def get_blob(self, key: str, version=None) -> types.Blob:
        pass

    @abstractmethod
    def get_stream(self, key: str, buffer_size=256*1024) -> Generator[bytes, None, None]:
        pass

    @abstractmethod
    def blob_history(self, key: str, max_results=None, sorted_=True) -> List[types.Blob]:
        pass

    @abstractmethod
    def recover_blob(self, key: str, version=None):
        pass

    @abstractmethod
    def delete_blob(self, key: str, version=None):
        pass

    @abstractmethod
    def delete_bucket(self, bucket=None, recursive=True, timeout_seconds=60):
        pass

    @abstractmethod
    def download_signed(self, key, minutes=15, bucket=None):
        pass

    @abstractmethod
    def upload_signed(self, key, minutes=15, bucket=None,
                      content_type="application/octed-stream"):
        pass


class LogsSpec(ABC):

    providerid: str
    keyvar: str
    filters: Dict[str, str]

    def __init__(self, keyvar: str):
        self.keyvar = keyvar

    @abstractmethod
    def list_logs(self, filter_: str, order_by: str, max_results=None) \
        -> List[types.LogEntry]:
        pass
