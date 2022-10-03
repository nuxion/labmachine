# Volumes

Volumes are disks that can be attached to the jupyter instance. A project could have multiple disks available but only one at the same time will be mounted into the jupyter instance. 

Note: The process to attach a disk into docker could be complex because it requires to be mounted first in the VM where docker is running, the into docker. Finally, ermissions and mount point should match. In the case of the mount point, what is important to know, is that `Labmachine` mount the disk into the `/data` folder. 

About permissions, check your docker image. 

Jupctl allows to run different command related to volumes check:

```
jupctl volumes --help
```

`import` and `unlink` operations only affects metata. 

An `import` operation will add and existing disk to `state.json`

An `unlink` operation will remove the disk metadata from `state.json` but the disk will continue in the cloud provider. 





