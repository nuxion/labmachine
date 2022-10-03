# Quick start

This quickstart works on google cloud platform.


## Requirements

if you are starting a new project from google cloud, some resources should exists before a Jupyter Lab machine could be created. 

1. Firts of all a public DNS Zone must exist.
2. A SA Account is needed with the right permissions. 
3. Firewall rules for http and https traffic, in this example we use the tag `http-server` for the firewall rule. 
4. A bucket accesible for the SA account created in the step 2 must exist. 

For steps 2,3 and 4 we have a helper script:

```
python3 scripts/google_setup.py --name <SA_ACCOUNT> --project <PROJECT_ID> --bucket <BUCKET_NAME>
```

After this you will will need to create and export the key of the <SA_ACCOUNT> to your local machine, for that do the following:
```
./scripts/gce_auth_key.sh <ACCOUNT>@<PROJECT_ID>.iam.gserviceaccount.com
mv .secrets/gce.json ${HOME}/.ssh/gce.json
```

Finally you will need to setup the credentials:
```
export GOOGLE_APPLICATION_CREDENTIALS=${HOME}/.ssh/gce.json
export JUP_COMPUTE_KEY=${HOME}/.ssh/gce.json
```

Note: `JUP_COMPUTE_KEY` is used by labmachine for authentication against cloud provider. In the case of Google, instead of `GOOGLE_APPLICATION_CREDENTIALS` env var, JUP_COMPUTE_KEY is used. This change is because some use cases may need to decouple DNS provisioning from Compute Provisioning in different accounts. 

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

