# Permissions

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
- `roles/artifactregistry.reader` If artifacts is used for pulling containers


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

