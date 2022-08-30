.EXPORT_ALL_VARIABLES:
DOCKER_VERSION:=0.10.0-alpha.0
IMG_VERSION:=010
PRJ:=algorinfo

.PHONY: init
init:
	packer init .

.PHONY: validate
validate:
	packer validate -var "img_version=${IMG_VERSION}" -var "project_id=${PRJ}" .

.PHONY: build
build: validate
	packer build -force -var "img_version=${IMG_VERSION}" -var "project_id=${PRJ}" .
