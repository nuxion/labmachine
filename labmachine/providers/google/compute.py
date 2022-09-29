import json
import os
import sys
import time
from copy import deepcopy
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from labmachine.base import ComputeSpec
from labmachine.types import (AttachStorage, BlockStorage, StorageRequest,
                              VMInstance, VMRequest)
from labmachine.utils import generate_random
from libcloud.common import google
from libcloud.compute.base import Node, NodeLocation
from libcloud.compute.providers import get_driver
from libcloud.compute.types import Provider

from .common import GOOGLE_AUTH_ENV, get_auth_conf


def generic_zone(name, driver) -> NodeLocation:
    return NodeLocation(id=None, name=name, country=None, driver=driver)


class Compute(ComputeSpec):
    providerid = "gce"

    def __init__(self, keyvar: str = GOOGLE_AUTH_ENV):
        super().__init__(keyvar=keyvar)
        conf = get_auth_conf(env_var=self.keyvar)
        G = get_driver(Provider.GCE)
        # _env_creds = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
        # if _env_creds:
        #     conf.credential_file = _env_creds
        self._project = conf.PROJECT
        self._location = conf.LOCATION
        self._account = conf.SERVICE_ACCOUNT
        self._conf = conf

        self.driver = G(
            conf.SERVICE_ACCOUNT,
            conf.CREDENTIALS,
            project=conf.PROJECT,
            datacenter=conf.LOCATION,
        )

    def _vm_id(self, vm_name, *, location):
        return f"{self.providerid}/{location}/{vm_name}"

    def _attach_disks(self, node, attached_disks: List[AttachStorage]) \
            -> List[str]:
        _volumes = self.driver.list_volumes()
        attached = []
        for v in attached_disks:
            to_attach = [_v for _v in _volumes if _v.name == v.disk_name]
            if len(to_attach) > 0:
                _attached = self.driver.attach_volume(
                    node,
                    to_attach[0],
                    device=v.device_name or v.disk_name,
                    ex_mode=v.mode,
                    ex_auto_delete=v.auto_delete,
                )
                if _attached:
                    attached.append(v.disk_name)
        return attached

    def get_vm(self, vm_name: str, location: Optional[str] = None) \
            -> VMInstance:
        node = self.driver.ex_get_node(vm_name, zone=location)
        disks = [d.get("deviceName") for d in node.extra["disks"]]
        public_ips = None
        if len(node.public_ips) > 1:
            public_ips = node.public_ips
        vm = VMInstance(
            vm_id=self._vm_id(node.name, location=node.extra["zone"].name),
            vm_name=node.name,
            state=node.state,
            location=node.extra["zone"].name,
            labels=node.extra.get("labels"),
            tags=node.extra.get("tags"),
            private_ips=node.private_ips,
            public_ips=public_ips,
            volumes=disks,
        )
        return vm

    def _transform_meta(self, data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """ It getts a dict of key and values from the VMRequest
        and converts it to a valid format for google
        """
        items = []
        for k, v in data.items():
            items.append(
                {"key": k, "value": v}
            )
        return items

    def create_vm(self, vm: VMRequest) -> VMInstance:
        items = self._transform_meta(vm.metadata)
        meta = None
        if vm.ssh_user and vm.ssh_public_cert:
            keys = {
                "key": "ssh-keys",
                "value": f"{vm.ssh_user}: {vm.ssh_public_cert}"
            }
            items.append(keys)
        if vm.startup_script:
            items.append({
                "key": "startup-script",
                "value": vm.startup_script
            })

        if items:
            meta = {"items": items}

        maintence_policy = None
        accelerator_type = None
        accelerator_count = None
        if vm.gpu:
            maintence_policy = "TERMINATE"
            accelerator_type = vm.gpu.gpu_type
            accelerator_count = vm.gpu.count
        scopes = None
        if vm.permissions:
            scopes = [{"email": vm.permissions.account,
                       "scopes": vm.permissions.roles}]
        instance = self.driver.create_node(
            vm.name,
            size=vm.instance_type,
            location=vm.location,
            # boot disk
            image=vm.boot.image,
            ex_disk_size=int(vm.boot.size),
            ex_disk_type=vm.boot.disk_type,
            ex_disk_auto_delete=vm.boot.auto_delete,
            # network
            ex_network=vm.network,
            external_ip=vm.external_ip,
            internal_ip=vm.internal_ip,
            # meta
            ex_metadata=meta,
            ex_tags=vm.tags,
            ex_labels=vm.labels,
            ex_service_accounts=scopes,
            # gpu
            ex_accelerator_type=accelerator_type,
            ex_accelerator_count=accelerator_count,
            ex_on_host_maintenance=maintence_policy,
        )

        attached = []
        if vm.attached_disks:
            attached = self._attach_disks(instance, vm.attached_disks)

        res = VMInstance(
            vm_id=self._vm_id(vm.name, location=vm.location),
            vm_name=vm.name,
            location=vm.location,
            state=instance.state,
            volumes=attached,
            private_ips=instance.private_ips,
            public_ips=instance.public_ips,
        )
        return res

    def list_vms(
        self, location: Optional[str] = None, tags: Optional[List[str]] = None
    ) -> List[VMInstance]:
        nodes = self.driver.list_nodes(ex_zone=location)
        filtered_nodes = []
        if tags:
            for n in nodes:
                if n.extra["tags"]:
                    for t in tags:
                        if t in n.extra["tags"]:
                            filtered_nodes.append(n)
        else:
            filtered_nodes = nodes
        final = []
        for n in filtered_nodes:
            # _lbl = n.extra["labels"] if n.extra["labels"] else {}
            # labels = {"tags": n.extra["tags"], **_lbl}

            disks = [d.get("deviceName") for d in n.extra["disks"]]
            public_ips = None
            if len(n.public_ips) > 1:
                public_ips = n.public_ips
            _n = VMInstance(
                vm_id=self._vm_id(n.name, location=n.extra["zone"].name),
                vm_name=n.name,
                state=n.state,
                location=n.extra["zone"].name,
                labels=n.extra.get("labels"),
                tags=n.extra.get("tags"),
                private_ips=n.private_ips,
                public_ips=public_ips,
                volumes=disks,
            )
            final.append(_n)
        return final

    def destroy_vm(self, vm: Union[str, VMInstance],
                   location: Optional[str] = None):
        name = vm
        if isinstance(vm, VMInstance):
            name = vm.vm_name
        _node = self.driver.ex_get_node(name, zone=location)
        _node.destroy()

    def get_volume(self, disk: str, location: Optional[str] = None) \
            -> Union[BlockStorage, None]:
        try:
            v = self.driver.ex_get_volume(disk, zone=location)
            loc = v.extra['zone'].name
            stat = v.extra['status']
            mount = v.extra['labels'].get("mount")
            source = v.extra['sourceImage']
            return BlockStorage(
                id=f"{self.providerid}/{loc}/{v.name}",
                name=v.name,
                size=v.size,
                location=loc,
                status=stat,
                mount=mount,
                source_image=source,
                description=v.extra["description"],
                storage_type=v.extra["type"],
                labels=v.extra["labels"],
            )
        except google.ResourceNotFoundError:
            return None

    def create_volume(self, disk: StorageRequest) -> BlockStorage:
        vol = self.driver.create_volume(
            disk.size,
            disk.name,
            location=disk.location,
            snapshot=disk.snapshot,
            ex_disk_type=disk.storage_type,
        )
        block = BlockStorage(
            id=vol.id, status=vol.extra["status"], **disk.dict())
        # block.extra = vol.extra
        return block

    def resize_volume(self, name: str, size: str,
                      location: Optional[str] = None) -> bool:
        vol = self.driver.ex_get_volume(name, zone=location)

        was_ok = self.driver.ex_resize_volume(
            vol,
            int(size),
        )
        # block.extra = vol.extra
        return was_ok

    def destroy_volume(self, disk: str, location: Optional[str] = None) \
            -> bool:
        vol = self.driver.ex_get_volume(disk, zone=location)
        if vol:
            rsp = self.driver.destroy_volume(vol)
            return rsp
        return False

    def attach_volume(self, vm: str, attach: AttachStorage,
                      location: Optional[str] = None) -> bool:
        _node = self.driver.ex_get_node(vm)
        vol = self.driver.ex_get_volume(attach.disk_name, zone=location)
        if _node and vol:
            res = self.driver.attach_volume(
                _node,
                vol,
                device=attach.device_name or attach.disk_name,
                ex_mode=attach.mode,
                ex_auto_delete=attach.auto_delete,
            )
            return res
        return False

    def detach_volume(self, vm: str, disk: str,
                      location: Optional[str] = None) -> bool:
        res = False
        _node = self.driver.ex_get_node(vm)
        vol = self.driver.ex_get_volume(disk, zone=location)
        if _node and vol:
            res = self.driver.detach_volume(vol, _node)
            return res
        return res

    def list_volumes(self, location: Optional[str] = None) -> List[BlockStorage]:
        vols = self.driver.list_volumes(ex_zone=location)
        volumes = []
        for v in vols:
            loc = v.extra['zone'].name
            stat = v.extra['status']
            mount = v.extra['labels'].get("mount")
            source = v.extra['sourceImage']
            _vol = BlockStorage(
                id=f"{self.providerid}/{loc}/{v.name}",
                name=v.name,
                size=v.size,
                location=loc,
                status=stat,
                mount=mount,
                source_image=source,
                description=v.extra["description"],
                storage_type=v.extra["type"],
                labels=v.extra["labels"],
            )
            volumes.append(_vol)
        return volumes
