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
- `roles/storage.admin`
- `roles/storage.objectAdmin`

TODO: Review permissions

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

## Appendix I: Debugging permissions

List SA accounts available in your project:

```
gcloud iam service-accounts list
```

List Roles assigned to an account:
```
gcloud projects get-iam-policy $PROJECT_ID --flatten="bindings[].members" --format='table(bindings.role)' --filter="bindings.members:$SA_ACCOUNT@$PROJECT_ID.iam.gserviceaccount.com"
```

## Appendix II: Scopes

For google artifacts:
https://cloud.google.com/artifact-registry/docs/access-control#compute

General understanding of scopes: https://cloud.google.com/sdk/gcloud/reference/beta/compute/instances/set-scopes


## Appendix III: Testing Artifact permissions

Repository URL will be:

https://$ZONE-docker.pkg.dev


```
root@lab-y7g3p:~#  gcloud auth print-access-token  | docker login -u oauth2accesstoken  --password-stdin https://us-central1-docker.pkg.dev
WARNING! Your password will be stored unencrypted in /root/.docker/config.json.
Configure a credential helper to remove this warning. See
https://docs.docker.com/engine/reference/commandline/login/#credentials-store

Login Succeeded
```

Listing repositories:
```
 gcloud artifacts repositories list
```
