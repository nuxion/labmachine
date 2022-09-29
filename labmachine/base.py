from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union

from .types import (AttachStorage, BlockStorage, DNSRecord, DNSZone,
                    StorageRequest, VMInstance, VMRequest)


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
            -> VMInstance:
        pass

    @abstractmethod
    def create_vm(self, vm: VMRequest) -> VMInstance:
        pass

    @abstractmethod
    def destroy_vm(self, vm: Union[str, VMInstance],
                   location: Optional[str] = None):
        pass

    @abstractmethod
    def list_vms(
        self, location: Optional[str] = None, tags: Optional[List[str]] = None
    ) -> List[VMInstance]:
        pass

    @abstractmethod
    def get_volume(self, vol_name) -> Union[BlockStorage, None]:
        pass

    @abstractmethod
    def create_volume(self, disk: StorageRequest) -> BlockStorage:
        pass

    @abstractmethod
    def resize_volume(self, name: str, size: str,
                      location: Optional[str] = None) -> bool:
        pass

    @abstractmethod
    def destroy_volume(self, disk: str, location: Optional[str] = None) -> bool:
        pass

    @abstractmethod
    def attach_volume(self, vm: str, attach: AttachStorage,
                      location: Optional[str] = None) -> bool:
        pass

    @abstractmethod
    def detach_volume(self, vm: str, disk: str,
                      location: Optional[str] = None) -> bool:
        pass

    @abstractmethod
    def list_volumes(self, location: Optional[str] = None) \
            -> List[BlockStorage]:
        pass


class DNSSpec(ABC):
    providerid: str
    keyvar: str

    def __init__(self, keyvar: str):
        self.keyvar = keyvar

    def get_zone(self, zoneid: str):
        pass

    def create_zone(self, zone: DNSZone):
        pass

    def list_zones(self) -> List[DNSZone]:
        pass

    def get_record(self, zoneid: str, recordid: str) -> DNSRecord:
        pass

    def list_records(self, zoneid: str) -> List[DNSRecord]:
        pass

    def create_record(self, record: DNSRecord) -> Dict[str, Any]:
        pass

    def delete_zone(self, zoneid: str):
        pass

    def delete_record(self, zoneid: str, recordid: str) -> bool:
        pass
