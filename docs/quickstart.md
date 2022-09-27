# Quick start

This quickstart works on google cloud platform.

## Permissions

If you are using google, a SA Account is needed. Also a env variable should be configurated. 

A helper script is provided for the key creation of SA account:

```
./scripts/gce_auth_key.sh <ACCOUNT>@<PROJECT_ID>.iam.gserviceaccount.com
mv gce.json ${HOME}/.ssh/gce.json
export GOOGLE_APPLICATION_CREDENTIALS=${HOME}/.ssh/gce.json
```

Run `gcloud iam service-accounts list` to see SA availables in your project. 


The minimal roles required for a instance creation are:

- `roles/compute.instanceAdmin.v1`
- `roles/iam.serviceAccountUser`
- `roles/dns.admin` check https://cloud.google.com/dns/docs/access-control


check [permissions](permissions.md) for more details. 

## Installing cli

Because we will use labmachine on google cloud platform we need to install google dependecies

```
pip install labmachine[google]
```


## Init project

After library installation a project should be initilized (similar to git)
Go to the root of your project and run:

```
jupctl init -d <DNS_ZONE_ID> -l <LOCATION> -s <FILEPATH_TO_STORE_STATE>
```

**What is happening here?**

1. `DNS_ZONE_ID`: is the zone id of your dns provider
2. `LOCATION`: related to your cloud provider, this is the zone and region where jupyter will run. 
3. `FILEPATH_TO_STORE_STATE`: Is the final path where the state of jupyter lab will be tracked. According to the path, it will identify if is a local path, a google storage path or other one. For instance:

```
jupctl init -d <DNS_ZONE_ID> -l <LOCATION> -s gs://my-bucket/my-project/state.json
```

In that case it will use google object storage. 

**Note**: Managing infraestructure could be overwhelming. `jupctl` does their best to make it easier whatever is possible, for instance to find the `DNS_ZONE_ID` you can do:

```
jupctl list-dns
```

Other options are available under `jupctl list-*`

## Creating a Jupyter Lab instance

Now that it's initialized, you can create your first jupyter instance. 

There are multiple ways to create an instance: 

1. Using the cli, but passing each parameter (container, boot_image, ram, etc)
2. Using the cli, but passing a file that contains all the information needed
3. As library

Here we will see an example using a file that contains the configuration needed for us, download the file:

```
mkdir examples/
curl -sL https://raw.githubusercontent.com/nuxion/labmachine/main/examples/lab_cpu.py > examples/lab_cpu.py
```

And then run it:

```
jupctl up --from-module examples.lab_cpu --wait
```

**Note**: because is a module and not a path, we use dots `.` instead of slashes `/`

Once finalized we will see a URL with a token to be used. 

Finally when finished, you can destroy the lab:

```
jupctl destroy
```

This will destroy the vm machine, delete the dns record, and destroy the boot disk but it will keep unteched extra volumes created, usually to be used as `/data` folder inside docker container. 

