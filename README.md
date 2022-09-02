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

## Next work

- [x] Provisioning GPU 
- [ ] State sync
- [ ] Maybe a cli
- [ ] Cloudflare dns
- [ ] import state
- [ ] clean old code
- [ ] startup script documentation
