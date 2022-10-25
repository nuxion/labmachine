packer {
  required_plugins {
    googlecompute = {
      version = ">= 0.0.1"
      source  = "github.com/hashicorp/googlecompute"
    }
  }
}

source "googlecompute" "labminimal-cpu" {
  project_id        = var.project_id
  source_image      = "debian-11-bullseye-v20220920"
  ssh_username      = "op"
  zone              = var.zone
  disk_size         = 10
  disk_type         = var.disk_type
  image_name        = "lab-minimal-${var.img_version}"
  image_description = "lab on demand"
  image_family      = "labfunctions"
  image_labels      =  { "arch": "cpu" }
  image_storage_locations = ["${var.image_zone}"]
  machine_type      = "${var.machine_type}"
}

build {
  sources = ["sources.googlecompute.labminimal-cpu"]
  # provisioner "file" {
  #   source = "../scripts/docker_mirror.py"
  #   destination = "/tmp/docker_mirror.py"
  # }
  provisioner "shell" {
    inline = [
      "sudo apt-get update",
      "curl -Ls https://raw.githubusercontent.com/nuxion/cloudscripts/0.2.0/install.sh | bash",
      "sudo cscli -i docker",
      "sudo cscli -i caddy",
      "sudo apt-get update -y",
      "sudo apt-get install -y jq",
      "sudo docker pull jupyter/minimal-notebook:python-3.10.6",
    ]
  }
}
