.EXPORT_ALL_VARIABLES:
IMG_VERSION:=050
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

.PHONY: build
build-debug: validate
	packer build -force -on-error=abort -var "img_version=${IMG_VERSION}" -var "project_id=${PRJ}" .
