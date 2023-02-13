from typing import List, Optional

from labmachine import types

from google.cloud import compute_v1
from google.cloud.compute_v1.services.instance_group_managers.client import \
    InstanceGroupManagersClient
from google.cloud.compute_v1.services.instance_templates import \
    InstanceTemplatesClient

from .common import GOOGLE_AUTH_ENV, get_auth_conf
from labmachine.base import InstanceGroupManagerSpec


class InstanceGroupManager(InstanceGroupManagerSpec):
    providerid: str = "gce"
    keyvar: str = GOOGLE_AUTH_ENV
    filepath: Optional[str] = None

    def __init__(
        self,
        keyvar: Optional[str] = GOOGLE_AUTH_ENV,
        filepath=None,
    ):
        conf = get_auth_conf(env_var=keyvar, filepath=filepath)

        self.driver = InstanceGroupManagersClient.from_service_account_json(
            conf.CREDENTIALS
        )
        self.keyvar = keyvar
        self.filepath = filepath
        self.tpl = InstanceTemplatesClient.from_service_account_json(conf.CREDENTIALS)

    def create(self, req: types.InstanceGroupManagerRequest):
        gm = compute_v1.types.InstanceGroupManager(
            base_instance_name=req.base_instance_name,
            description=req.description,
            instance_template=req.template_uri,
            name=req.name,
            target_size=req.target_size,
            zone=req.zone,
        )

        r = compute_v1.types.InsertInstanceGroupManagerRequest(
            instance_group_manager_resource=gm, project=req.projectid, zone=req.zone
        )
        self.driver.insert(r)

    def resize(self, *, name: str, projectid: str, size: int, zone: str):
        r = compute_v1.types.ResizeInstanceGroupManagerRequest(
            instance_group_manager=name,
            project=projectid,
            size=size,
            zone=zone,
        )

        self.driver.resize(r)

    def _to_item(self, gm, projectid, zone) -> types.InstanceGroupManagerItem:
        item = types.InstanceGroupManagerItem(
            name=gm.name,
            base_instance_name=gm.base_instance_name,
            target_size=gm.target_size,
            projectid=projectid,
            zone=zone,
            template_uri=gm.instance_template,
            description=gm.description,
            status=types.InstanceGroupStatus(
                is_stable=gm.status.is_stable,
                abandoning=gm.current_actions.abandoning,
                creating=gm.current_actions.creating,
                deleting=gm.current_actions.deleting,
                none=gm.current_actions.none,
                recreating=gm.current_actions.recreating,
                refreshing=gm.current_actions.refreshing,
                restarting=gm.current_actions.restarting,
                resuming=gm.current_actions.resuming,
                starting=gm.current_actions.starting,
                stopping=gm.current_actions.stopping,
                suspending=gm.current_actions.suspending,
                verifying=gm.current_actions.verifying,
            ),
        )
        return item

    def get(
        self, *, name: str, projectid: str, zone: str
    ) -> types.InstanceGroupManagerItem:
        obj = self.driver.get(project=projectid, zone=zone, instance_group_manager=name)
        return self._to_item(obj, projectid, zone)

    def list(
        self, *, projectid: str, zone: str
    ) -> List[types.InstanceGroupManagerItem]:
        items = []
        for gm in self.driver.list(project=projectid, zone=zone):
            item = self._to_item(gm, projectid, zone)
            items.append(item)

        return items

    def list_instances(
        self, *, name: str, projectid: str, zone: str
    ) -> List[types.ManagedInstance]:
        pages = self.driver.list_managed_instances(
            project=projectid, zone=zone, instance_group_manager=name
        )
        instances = [
            types.ManagedInstance(
                id=str(r.id),
                instance_group_name=name,
                projectid=projectid,
                zone=zone,
                instance=r.instance.rsplit("/", maxsplit=1)[1],
                status=r.instance_status,
                template=r.version.instance_template,
                current_action=r.current_action,
            )
            for r in pages
        ]
        return instances

    def delete(self, *, name: str, projectid: str, zone: str):
        req = compute_v1.types.DeleteInstanceGroupManagerRequest(
            instance_group_manager=name,
            project=projectid,
            zone=zone,
        )
        self.driver.delete(req)

    def recreate_instances(
        self, *, name: str, projectid, zone: str, instances: List[str]
    ):
        _instances = [f"zones/{zone}/instances/{i}" for i in instances]
        instances_req = compute_v1.types.InstanceGroupManagersRecreateInstancesRequest(
            instances=_instances
        )

        req = compute_v1.RecreateInstancesInstanceGroupManagerRequest(
            instance_group_manager=name,
            instance_group_managers_recreate_instances_request_resource=instances_req,
            project=projectid,
            zone=zone,
        )

        self.driver.recreate_instances(req)

    def delete_instances(
        self, *, name: str, projectid: str, zone: str, instances: List[str]
    ):
        _instances = [f"zones/{zone}/instances/{i}" for i in instances]
        ireq = compute_v1.types.InstanceGroupManagersDeleteInstancesRequest(
            instances=_instances
        )
        self.driver.delete_instances(
            project=projectid,
            zone=zone,
            instance_group_manager=name,
            instance_group_managers_delete_instances_request_resource=ireq,
        )

    def list_templates(self, *, projectid: str) -> List[types.InstanceTemplate]:
        tpls = [
            types.InstanceTemplate(
                name=r.name,
                template_uri=r.self_link,
                machine_type=r.properties.machine_type,
                spot_instance=r.properties.scheduling.preemptible,
            )
            for r in self.tpl.list(project=projectid)
        ]
        return tpls
