# labmachine

This a POC about creating a jupyter instance on demand and registering it into a dns provider and HTTPS. 

Right now only works for Google Cloud but should be easy expand to other providers. 


For examples, see [examples](examples/)
There you can see `infra_[cpu|gpu].py` and `lab_[cpu|gpu].py`

infra files are raw implementacion of the cluster library. 
lab files are abstractions built over this library for jupyter lab provisioning. 


For authentication the google app cred variable should be defined:
```
./scripts/gce_auth_key.sh <ACCOUNT>@<PROJECT_ID>.iam.gserviceaccount.com
mv gce.json ${HOME}/.ssh/gce.json
export GOOGLE_APPLICATION_CREDENTIALS=${HOME}/.ssh/gce.json
```

Run `gcloud iam service-accounts list` to see SA available in your project. 

### Suggested approach:

If you don't have a SA already created, you can take this strategy to create one and asign permissions to it.

```
gcloud iam service-accounts create labcreator
    --description="Jupyter lab creator" \
    --display-name="lab-creator"
```

Then add the following roles to the account:

	- `roles/compute.instanceAdmin.v1`
	- `roles/iam.serviceAccountUser`
  - `roles/dns.admin` check https://cloud.google.com/dns/docs/access-control

DNS role is needed only if the google dns provider is used

**Warning**: those roles can be too permissive, please check [this for more information](https://cloud.google.com/compute/docs/access/iam)

```
roles="roles/compute.instanceAdmin.v1 roles/iam.serviceAccountUser"
for $perm in `cat $roles`; do
	gcloud projects add-iam-policy-binding PROJECT_ID \
  	  --member="serviceAccount:labcreator@PROJECT_ID.iam.gserviceaccount.com" \
    	--role=$perm
done
``` 

## Destroy lab

```
python3 examples/destroy_lab.py
```

## Next work

See https://trello.com/b/F2Smw3QO/labmachine

