from typing import List, Optional

from labmachine import types

from google.cloud import compute_v1
from google.cloud.compute_v1.services.instance_group_managers.client import \
    InstanceGroupManagersClient

from .common import GOOGLE_AUTH_ENV, get_auth_conf


class InstanceGroup:
    providerid: str = "gce"
    keyvar: str = GOOGLE_AUTH_ENV
    filepath: Optional[str] = None

    def __init__(self, keyvar: Optional[str] = GOOGLE_AUTH_ENV, filepath=None):
        conf = get_auth_conf(env_var=keyvar, filepath=filepath)

        self.driver = InstanceGroupManagersClient.from_service_account_json(
            conf.CREDENTIALS
        )
        self.keyvar = keyvar
        self.filepath = filepath

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

    def resize(self, instance_group_name: str, projectid: str, size: int, zone: str):
        r = compute_v1.types.ResizeInstanceGroupManagerRequest(
            instance_group_manager=instance_group_name,
            project=projectid,
            size=size,
            zone=zone,
        )

        self.driver.resize(r)

    def list(self, zone: str, projectid: str) -> List[types.InstanceGroupManagerItem]:
        items = []
        for gm in self.driver.list(project=projectid, zone=zone):
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
            items.append(item)

        return items

    def list_instances(
        self, projectid: str, zone: str, instance_group_name: str
    ) -> List[types.ManagedInstance]:
        pages = self.driver.list_managed_instances(
            project=projectid, zone=zone, instance_group_manager=instance_group_name
        )
        instances = [
            types.ManagedInstance(
                id=str(r.id),
                instance_group_name=instance_group_name,
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

    def delete(self, instance_group_name: str, projectid: str, zone: str):
        req = compute_v1.types.DeleteInstanceGroupManagerRequest(
            instance_group_manager=instance_group_name,
            project=projectid,
            zone=zone,
        )
        self.driver.delete(req)

    def recreate_instances(
        self, instance_group_name, projectid, zone, instances: List[str]
    ):
        _instances = [f"zones/{zone}/instances/{i}" for i in instances]
        instances_req = compute_v1.types.InstanceGroupManagersRecreateInstancesRequest(
            instances=_instances
        )

        req = compute_v1.RecreateInstancesInstanceGroupManagerRequest(
            instance_group_manager=instance_group_name,
            instance_group_managers_recreate_instances_request_resource=instances_req,
            project=projectid,
            zone=zone,
        )

        self.driver.recreate_instances(req)
