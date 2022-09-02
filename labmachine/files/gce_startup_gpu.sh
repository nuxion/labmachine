#!/bin/bash

DOCKER_LISTEN=127.0.0.1:8888
DEVICE=/dev/disk/by-id/google
DEFAULT_VOL=/opt/volumes/labdata
NOTEBOOKS_DIR=${DEFAULT_VOL}/notebooks
DATA_DIR=${DEFAULT_VOL}/data
WORKAREA=/workarea
CHECK_EVERY=30

command_exists() {
	command -v "$@" > /dev/null 2>&1
}



if ! command_exists "cscli" &> /dev/null
then
    curl -Ls https://raw.githubusercontent.com/nuxion/cloudscripts/main/install.sh | sh
fi
if ! command_exists "caddy" &> /dev/null
then
    cscli -i caddy
fi
if ! command_exists "docker" &> /dev/null
then
    cscli -i docker
fi
if ! command_exists "nvidia-smi" &> /dev/null
then
    cscli -i nvidia-docker
fi

if ! command_exists "jq" &> /dev/null
then
    apt-get install -y jq
fi

LAB_URL=`curl -s "http://metadata.google.internal/computeMetadata/v1/instance/attributes/?recursive=true" -H "Metadata-Flavor: Google" | jq .laburl | tr -d '"'`
# NAME=`curl -s "http://metadata.google.internal/computeMetadata/v1/instance/name" -H "Metadata-Flavor: Google"`
IMAGE=`curl -s "http://metadata.google.internal/computeMetadata/v1/instance/attributes/?recursive=true" -H "Metadata-Flavor: Google" | jq .labimage | tr -d '"'`
TOKEN=`curl -s "http://metadata.google.internal/computeMetadata/v1/instance/attributes/?recursive=true" -H "Metadata-Flavor: Google" | jq .labtoken | tr -d '"'`
USERID=`curl -s "http://metadata.google.internal/computeMetadata/v1/instance/attributes/?recursive=true" -H "Metadata-Flavor: Google" | jq .labuid | tr -d '"'`
# DOCKER_USER=`curl -s "http://metadata.google.internal/computeMetadata/v1/instance/attributes/?recursive=true" -H "Metadata-Flavor: Google" | jq .dockeruser | tr -d '"'`
LAB_VOL=`curl -s "http://metadata.google.internal/computeMetadata/v1/instance/attributes/?recursive=true" -H "Metadata-Flavor: Google" | jq .labvol | tr -d '"'`
LAB_TS=`curl -s "http://metadata.google.internal/computeMetadata/v1/instance/attributes/?recursive=true" -H "Metadata-Flavor: Google" | jq .labtimeout | tr -d '"'` # in minutes

check_disk_formated() {
    lsblk -f ${DEVICE}-${1} | grep ext4
}

format_disk() {
    mkfs.ext4 ${DEVICE}-${1}
}

check_folders() {
    if [ ! -d ${DATA_DIR} ]
    then
        mkdir ${DATA_DIR}
    fi

    chown ${USERID} ${DATA_DIR}
    chmod 750 ${DATA_DIR}
    if [ ! -d ${NOTEBOOKS_DIR} ]
    then
        mkdir ${NOTEBOOKS_DIR}
    fi
    chown ${USERID} ${NOTEBOOKS_DIR}
    chmod 750 ${NOTEBOOKS_DIR}

}

check_pull(){
    docker images | grep $1
    status=$?
    if [ "${status}" -gt 0 ];
    then
	docker pull ${1}
    fi
}

if [ "${LAB_VOL}" != "null" ];
then
   mkdir -p ${DEFAULT_VOL}
   check_disk_formated ${LAB_VOL}
   status=$?
   if [ "${status}" -ne 0 ];
   then
      format_disk ${LAB_VOL}
   fi
   mount ${DEVICE}-${LAB_VOL} ${DEFAULT_VOL}
fi
check_folders
check_pull $IMAGE
docker run --rm \
	   --name jupyter-gpu \
       --gpus all \
	   -v ${DATA_DIR}:${WORKAREA}/data \
       -v ${NOTEBOOKS_DIR}:${WORKAREA}/notebooks \
	   -e BASE_PATH=${WORKAREA} \
       -p ${DOCKER_LISTEN}:8888 \
       ${IMAGE} jupyter lab --ip=0.0.0.0 --port=8888 --notebook-dir=${WORKAREA} --ServerApp.token=${TOKEN} --ServerApp.shutdown_no_activity_timeout=${LAB_TS} > /tmp/jupyter.log 2>&1 &

cat <<EOT > /etc/Caddyfile
${LAB_URL} {
	reverse_proxy ${DOCKER_LISTEN}
}
EOT

sleep 5
caddy run --config /etc/Caddyfile > /tmp/caddy.log 2>&1 &
running=`docker ps | grep jupyter | wc -l`
echo JUPYTER Running: ${running}
while [ $running -gt 0 ]
do
    echo "Still running jupyter"
    running=`docker ps | grep jupyter | wc -l`
    sleep $CHECK_EVERY
done

echo "Shuting down"
shutdown -h now
