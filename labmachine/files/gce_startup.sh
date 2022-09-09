#!/bin/bash
set -o nounset
# set -o errexit
# set -x
export DEBIAN_FRONTEND=noninteractive
DOCKER_CMD="docker run"
DOCKER_LISTEN=127.0.0.1:8888
DEVICE=/dev/disk/by-id/google
DEFAULT_VOL=/opt/volumes/labdata
NOTEBOOKS_DIR=${DEFAULT_VOL}/notebooks
DATA_DIR=${DEFAULT_VOL}/data
WORKAREA=/workarea
CHECK_EVERY=30
LOG_FILE=/var/log/jupyter_startup.log
exec 3>&1 1>>${LOG_FILE} 2>&1

_log() {
   echo "$(date): $@" | tee /dev/fd/3
}

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
    _log "Installing docker"
    cscli -i docker
fi
if ! command_exists "jq" &> /dev/null
then
    apt-get install -y jq
fi

META=`curl -s "http://metadata.google.internal/computeMetadata/v1/instance/attributes/?recursive=true" -H "Metadata-Flavor: Google"`
LAB_URL=`echo $META | jq .laburl | tr -d '"'`
# NAME=`curl -s "http://metadata.google.internal/computeMetadata/v1/instance/name" -H "Metadata-Flavor: Google"`
IMAGE=`echo $META | jq .labimage | tr -d '"'`
TOKEN=`echo $META | jq .labtoken | tr -d '"'`
USERID=`echo $META | jq .labuid | tr -d '"'`
# DOCKER_USER=`curl -s "http://metadata.google.internal/computeMetadata/v1/instance/attributes/?recursive=true" -H "Metadata-Flavor: Google" | jq .dockeruser | tr -d '"'`
LAB_VOL=`echo $META | jq .labvol | tr -d '"'`
LAB_TS=`echo $META | jq .labtimeout | tr -d '"'` # in minutes
GPU=`echo $META | jq .gpu | tr -d '"'`
DEBUG=`echo $META | jq .debug | tr -d '"'`

check_disk_formated() {
    lsblk -f ${DEVICE}-${1} | grep ext4
}

format_disk() {
    mkfs.ext4 ${DEVICE}-${1}
}

check_folders() {
    if [ ! -d ${DATA_DIR} ]
    then
        _log "creating DATA_DIR ${DATA_DIR}"
        mkdir ${DATA_DIR}
        chown ${USERID} ${DATA_DIR}
        chmod 750 ${DATA_DIR}
    fi

    if [ ! -d ${NOTEBOOKS_DIR} ]
    then
        _log "creating NOTEBOOKS_DIR ${NOTEBOOKS_DIR}"
       mkdir ${NOTEBOOKS_DIR}
       chown ${USERID} ${NOTEBOOKS_DIR}
       chmod 750 ${NOTEBOOKS_DIR}
    fi
}

check_pull(){
    docker images | grep $1
    status=$?
    if [ "${status}" -lt 1 ];
    then
        _log "Pulling docker image ${1}"
	docker pull ${1} | tee /dev/fd/3
    fi
}

if [ "${LAB_VOL}" != "null" ];
then
   _log "Configuring LAB_VOL (${LAB_VOL}) in $DEFAULT_VOL"
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
if [ $GPU = "yes" ]
then
    DOCKER_CMD="docker run --gpus all "
fi
echo "RUN jup"
$DOCKER_CMD --name jupyter -d \
	-v ${DATA_DIR}:${WORKAREA}/data \
    -v ${NOTEBOOKS_DIR}:${WORKAREA}/notebooks \
	-e BASE_PATH=${WORKAREA} \
    -p ${DOCKER_LISTEN}:8888 \
    ${IMAGE} jupyter lab --ip=0.0.0.0 --port=8888 --notebook-dir=${WORKAREA} --ServerApp.token=${TOKEN} --ServerApp.shutdown_no_activity_timeout=${LAB_TS}  | tee /dev/fd/3
docker logs jupyter | tee /dev/fd/3

cat <<EOT > /etc/Caddyfile
${LAB_URL} {
	reverse_proxy ${DOCKER_LISTEN}
}
EOT
sleep 5
caddy run --config /etc/Caddyfile > /var/log/caddy.log 2>&1 &
running=`docker ps | grep jupyter | wc -l`
_log "JUPYTER Running: ${running}"
while [ $running -gt 0 ]
do
    _log "Still running jupyter"
    running=`docker ps | grep jupyter | wc -l`
    sleep $CHECK_EVERY
done
if [ $DEBUG = "yes" ]
then
    echo "Shutdown -h now"
else
    _log "Shutdown -h now"
    shutdown -h now | tee /dev/fd/3
fi
