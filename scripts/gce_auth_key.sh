#!/bin/bash
# Creates a key for an existing service-account.
# To list existing accounts run: gcloud iam service-accounts list
SA_NAME=$1
KEY=${2:-gce.json}
gcloud iam service-accounts keys create .secrets/${KEY} --iam-account=${SA_NAME} --key-file-type="json"
echo Key created into .secrets/${KEY}
