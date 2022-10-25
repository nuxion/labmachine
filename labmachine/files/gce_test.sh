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
CHECK_EVERY=5
LOG_FILE=/var/log/startup.log
LOG_BUCKET="labmachine"
exec 3>&1 1>>${LOG_FILE} 2>&1


_log() {
    echo "$(date): $@" | tee /dev/fd/3
    payload="${HOSTNAME} -- $@"
    gcloud logging write $LOG_BUCKET "${payload}" --severity=INFO
}

command_exists() {
	command -v "$@" > /dev/null 2>&1
}

if ! command_exists "cscli" &> /dev/null
then
    curl -Ls https://raw.githubusercontent.com/nuxion/cloudscripts/0.6.0/install.sh | bash
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

# INSTANCE= curl -s "http://metadata.google.internal/computeMetadata/v1/?recursive=true" -H "Metadata-Flavor: Google" | jq ".instance.name"
META=`curl -s "http://metadata.google.internal/computeMetadata/v1/instance/attributes/?recursive=true" -H "Metadata-Flavor: Google"`
REGISTRY=`echo $META | jq .registry | tr -d '"'`
IMAGE=`echo $META | jq .image | tr -d '"'`
GPU=`echo $META | jq .gpu | tr -d '"'`
DEBUG=`echo $META | jq .debug | tr -d '"'`
IMG_RGB=`echo $META | jq .rgb | tr -d '"'`
IMG_NIR=`echo $META | jq .nir | tr -d '"'`
NIR_OUT=`echo $META | jq .output | tr -d '"'`
BUCKET=`echo $META | jq .bucket | tr -d '"'`

login_docker() {
    # https://${LOCATION}-docker.pkg.dev
    gcloud auth print-access-token  | docker login -u oauth2accesstoken  --password-stdin https://${REGISTRY}
}


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
if [ ! -z "${REGISTRY}" ];
then
   login_docker
   IMAGE=${REGISTRY}/${IMAGE}
   _log "Final image is ${IMAGE}"
fi
check_pull $IMAGE
if [ $GPU = "yes" ]
then
    DOCKER_CMD="docker run --gpus all "
fi

mkdir -p /data/in
mkdir -p /data/out
mkdir -p /data/web
chmod -R 777 /data


cat <<EOT > /tmp/otb.sh
#!/bin/bash
IMG_RGB=${IMG_RGB}
IMG_NIR=${IMG_NIR}
NIR_OUT=${NIR_OUT}
source /opt/OTB/otbenv.profile
otbcli_Superimpose -inr /in/${IMG_RGB} -inm /in/${IMG_NIR} -out "/out/${NIR_OUT}?gdal:co:COMPRESS=LZW&gdal:co:TILED=YES&gdal:co:BIGTIFF=IF_SAFER&gdal:co:GDAL_CACHEMAX=512" uint8
EOT
chmod +x /tmp/otb.sh
# BUCKET=gs://dym-temp/imagenes-gcba/tif/2017
if [ ! -f "/data/in/$IMG_RGB" ];then
	gsutil cp ${BUCKET}/${IMG_RGB} /data/in/
	gsutil cp ${BUCKET}/${IMG_NIR} /data/in/
fi
nohup python3 -m http.server --directory /data/web 80 &
write_status(){
cat <<EOT > /data/web/status
mem_used=$(free -t -m -h | grep Mem | awk '{print $3}')
mem_total=$(free -t -m -h | grep Mem | awk '{print $2}')
EOT

}

wait_output(){
    while [ ! -f /data/web/finish ]
    do
        echo "Waiting for OTB"
	write_status
        sleep $CHECK_EVERY
    done

}
wait_output &
WAIT_PID=$!
$DOCKER_CMD --rm \
	-v /tmp/otb.sh:/tmp/otb.sh \
	-v /data/in/:/in\
	-v /data/out/:/out\
	$IMAGE /tmp/otb.sh > /data/web/otb.log

gsutil cp /data/out/${NIR_OUT} ${BUCKET}/${NIR_OUT}
touch /data/web/finish
kill $WAIT_PID >/dev/null 2>&1
_log "Ended"
