from typing import List

from labmachine import types
from labmachine.base import LogsSpec

from google.cloud import logging_v2
from google.cloud.logging import DESCENDING

from .common import GOOGLE_AUTH_ENV, get_auth_conf

# https://cloud.google.com/logging/docs/view/logging-query-language


class Logs(LogsSpec):
    providerid = "gce"
    keyvar: str = GOOGLE_AUTH_ENV
    filters = {
        "by-resource": 'labels."compute.googleapis.com/resource_name" = {}',
        "by-instance": "resource.labels.instance_id = {}",
        "by-name": "logName:{}",
        "by-severity": "severity = {}",
        "timestamp": 'timestamp >= "{}"'

    }

    def __init__(self, keyvar=GOOGLE_AUTH_ENV):
        super().__init__(keyvar=keyvar)
        self._conf = get_auth_conf(GOOGLE_AUTH_ENV)
        self.driver = logging_v2.Client()

    def _to_log(self, obj) -> types.LogEntry:
        payload = obj.payload
        if not isinstance(obj.payload, dict):
            payload = {"msg": obj.payload}

        return types.LogEntry(
            logid=obj.insert_id,
            log_name=obj.log_name,
            labels=obj.labels,
            level=obj.severity,
            timestamp=obj.timestamp,
            payload=payload
        )

    def list_logs(self, filter_=None, order_by=DESCENDING, max_results=None) \
            -> List[types.LogEntry]:
        logs = []
        for log in self.driver.list_entries(
                filter_=filter_, order_by=order_by, max_results=max_results):
            logs.append(self._to_log(log))
        return logs
