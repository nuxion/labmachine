import io
from datetime import timedelta
from typing import Dict, Generator, List, Optional, Union

from labmachine import types
from labmachine.base import StorageSpec
from labmachine.errors import BlobNotFound, BucketForbidden, BucketNotFound
from smart_open import open

from google.api_core.exceptions import Forbidden
from google.cloud.storage import Client
from google.cloud.storage import blob as gblob
from google.cloud.storage.bucket import Bucket as GoogleBucket

from .common import GOOGLE_AUTH_ENV, get_auth_conf


LOCS = {
    types.BucketLocation.ASIA.value: "ASIA",
    types.BucketLocation.US.value: "US",
    types.BucketLocation.EU.value: "EU",
    types.BucketLocation.US_CENTRAL.value: "US-CENTRAL1",
    types.BucketLocation.US_EAST1.value: "US-EAST1"
}


# class Storage(StorageSpec):
class Storage(StorageSpec):
    providerid: str = "gce"
    keyvar: str = GOOGLE_AUTH_ENV
    filepath: Optional[str] = None

    def __init__(self, bucket=None, *,
                 keyvar: Optional[str] = GOOGLE_AUTH_ENV,
                 filepath=None):

        conf = get_auth_conf(env_var=keyvar, filepath=filepath)

        self.driver = Client.from_service_account_json(conf.CREDENTIALS)
        super().__init__(keyvar=keyvar, filepath=filepath)

    def set_bucket(self, name: str) -> types.Bucket:
        try:
            b = self.driver.get_bucket(name)
        except Forbidden:
            raise BucketForbidden(name)
        except gblob.exceptions.NotFound:
            self._bucket = b

        return self._to_bucket(b)

    def create_bucket(self,
                      name: str,
                      storage_class: str,
                      location: str,
                      versioning: bool,
                      labels: Optional[Dict[str, str]] = None) -> types.Bucket:

        _b = self.driver.create_bucket(
            name=name,
            storage_class=storage_class,
            location=location,
            labels=labels,
        )
        _bucket = self._to_bucket(_b)
        if versioning:
            self.enable_versioning(name)
            _bucket.versioning = True
        return _bucket

    def _current_or_get_bucket(self, bucket=None) -> GoogleBucket:
        if bucket:
            _b = self.driver.get_bucket(bucket)
        else:
            _b = self._bucket

        return _b

    def enable_versioning(self, bucket: Optional[str] = None):
        _b = self._current_or_get_bucket(bucket)
        _b.versioning_enable = True
        _b.patch()

    def disable_versioning(self, bucket: Optional[str] = None):
        _b = self._current_or_get_bucket(bucket)
        _b.versioning_enable = False
        _b.patch()

    def make_public(self, bucket: Optional[str] = None):
        pass

    def make_private(self, bucket: Optional[str] = None):
        pass

    def _to_bucket(self, b: GoogleBucket) -> types.Bucket:
        _bucket = types.Bucket(
            name=b.name,
            storage_class=b.storage_class,
            location=b.location,
            url=f"gs://{b.name}",
            versioning=b.versioning_enabled,
            labels=b.labels,
            created_at=b.time_created,
        )
        return _bucket

    def _to_blob(self, obj) -> types.Blob:
        return types.Blob(
            id=obj.id,
            name=obj.name,
            providerid=self.providerid,
            size=obj.size,
            bucket=self.bucket.name,
            content_type=obj.content_type,
            metadata=obj.metadata,
            version=str(obj.generation),
            md5hash=obj.md5_hash,
            public_url=obj.public_url,
            created_at=obj.time_created,
        )

    def list_buckets(self, prefix: Optional[str] = None) -> List[types.Bucket]:
        buckets = [
            self._to_bucket(b)
            for b in self.driver.list_buckets(prefix=prefix)]
        return buckets

    def list_objects(self, prefix: Optional[str] = None,
                     max_results=None,
                     page_token=None, history: bool = False) -> List[types.Blob]:
        _blobs = self._bucket.list_blobs(prefix=prefix,
                                         max_results=max_results,
                                         page_token=page_token,
                                         versions=history)
        blobs = [self._to_blob(b) for b in _blobs]
        return blobs

    def put_bytes(self, key: str, *, content: Union[bytes, io.BytesIO],
                  metadata: Optional[Dict[str, str]] = None) -> types.Blob:
        blob = self._bucket.blob(key)
        blob.metdata = metadata
        if isinstance(content, bytes):
            blob.upload_from_file(io.BytesIO(content))
        else:
            blob.upload_from_file(content)
        return self._to_blob(blob)

    def put_stream(self, key: str, generator: Generator[bytes, None, None],
                   metadata: Optional[Dict[str, str]] = None) -> bool:
        with open(f"gs://{self.bucket.name}/{key}",
                  "wb", client=self.driver) as f:
            data = True
            while data:
                try:
                    _data = generator.__next__()
                    f.write(_data)
                except StopIteration:
                    data = False
        if metadata:
            blob = self._bucket.get_blob(key)
            blob.metadata = metadata
            blob.patch()

        return True

    def get_bytes(self, key: str, version=None) -> bytes:
        blob = self._bucket.blob(key)
        try:
            obj = blob.download_as_bytes()
        except gblob.exceptions.NotFound:
            raise BlobNotFound(bucket=self.bucket.name, key=key)

        return obj

    def get_blob(self, key: str, version=None) -> types.Blob:
        _blob = self._bucket.get_blob(key, generation=version)
        try:
            _id = _blob.id
        except AttributeError:
            raise BlobNotFound(bucket=self.bucket.name, key=key)

        return self._to_blob(_blob)

    def get_stream(self, key: str, buffer_size=256*1024) -> Generator[bytes, None, None]:
        for chunk in open(f"gs://{self.bucket.name}/{key}",
                          "rb",
                          client=self.driver, buffer_size=buffer_size):
            yield chunk

    def blob_history(self, key: str, max_results=None, sorted_=True) -> List[types.Blob]:
        rows = self._bucket.list_blobs(
            prefix=key, max_results=max_results, versions=True)
        blobs = [self._to_blob(r) for r in rows
                 if r.name == key]
        if sorted_:
            return sorted(blobs, reverse=True)
        return blobs

    def recover_blob(self, key: str, version=None):
        if version:
            _version = version
        else:
            history = self.blob_history(key)
            if not history:
                raise BlobNotFound(self._bucket.name, key)
            _version = history[0].version

        source_blob = self._bucket.blob(key, generation=version)

        try:
            self._bucket.copy_blob(source_blob, self._bucket, key,
                                   source_generation=_version)

        except gblob.exceptions.NotFound:
            raise BlobNotFound(self._bucket.name, key)

    def delete_blob(self, key: str, version=None):
        self._bucket.delete_blob(key, generation=version)

    def delete_bucket(self, bucket=None, recursive=True, timeout_seconds=60):
        _b = self._current_or_get_bucket(bucket)
        _b.delete(force=recursive, timeout=timeout_seconds)

    def download_signed(self, key, minutes=15, bucket=None):
        _b = self._current_or_get_bucket(bucket)
        blob = _b.blob(key)
        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=minutes),
            method="GET",
        )
        return url

    def upload_signed(self, key, minutes=15, bucket=None,
                      content_type="application/octed-stream"):
        """
        curl -X PUT -H 'Content-Type: application/octet-stream' "
        "--upload-file my-file '{url}'
        """

        _b = self._current_or_get_bucket(bucket)
        blob = _b.blob(key)
        url = blob.generate_signed_url(
            version="v4",
            expiration=timedelta(minutes=minutes),
            method="PUT",
            content_type=content_type
        )
        return url
