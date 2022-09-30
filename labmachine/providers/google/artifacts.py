from typing import List, Optional

from pydantic import BaseModel

from google.cloud import artifactregistry_v1

from .common import GOOGLE_AUTH_ENV, get_auth_conf


class Repository(BaseModel):
    name: str
    kind: str
    description: Optional[str]


class ContainerImage(BaseModel):
    name: str
    uri: str
    tags: List[str]
    media_type: str
    image_size_bytes: Optional[int] = None


class Artifacts:

    providerid = "gce"

    def __init__(self, keyvar=GOOGLE_AUTH_ENV):
        """ 
        GOOGLE_APPLICATION_CREDENTIALS must be set.

        """
        self._conf = get_auth_conf(GOOGLE_AUTH_ENV)
        self.driver = artifactregistry_v1.ArtifactRegistryClient()

    def list_respositories(self, project=None, location=None) -> List[Repository]:
        """a
        from https://github.com/googleapis/python-artifact-registry/issues/118
        parent="projects/PROJECT/locations/LOCATION"
        """
        _parent = f"projects/{project}/locations/{location}"
        if not project and not location:
            _parent = f"projects/{self._conf.PROJECT}/locations/{self._conf.LOCATION}"
        req = artifactregistry_v1.ListRepositoriesRequest(
            parent=_parent)
        result = self.driver.list_repositories(request=req)
        repos = [Repository(name=r.name, description=r.description, kind=r.format_)
                 for r in result]
        return repos

    def list_docker_images(self, repo_name: str, *, project=None, location=None) \
            -> List[ContainerImage]:
        _parent = f"projects/{project}/locations/{location}/repositories/{repo_name}"
        if not project and not location:
            _parent = f"projects/{self._conf.PROJECT}/locations/{self._conf.LOCATION}/repositories/{repo_name}"

        req = artifactregistry_v1.ListDockerImagesRequest(
            parent=_parent,
        )
        res = self.driver.list_docker_images(request=req)

        images = []
        for r in res:
            uri = r.uri.split("@")[0]
            name = uri.rsplit("/", maxsplit=1)[1]
            img = ContainerImage(name=name,
                                 uri=uri,
                                 tags=list(r.tags),
                                 media_type=r.media_type,
                                 image_size_bytes=r.image_size_bytes)
            images.append(img)
        return images
