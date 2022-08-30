packer {
  required_plugins {
    googlecompute = {
      version = ">= 0.0.1"
      source  = "github.com/hashicorp/googlecompute"
    }
  }
}

source "googlecompute" "labagent" {
  project_id        = var.project_id
  source_image      = "debian-11-bullseye-v20220406"
  ssh_username      = "op"
  zone              = var.zone
  disk_size         = 10
  disk_type         = var.disk_type
  # image_name        = "lab-agent-${legacy_isotime("2006-01-02")}"
  image_name        = "lab-minimal-${var.img_version}"
  image_description = "lab on demand"
  machine_type      = "e2-micro"
}

build {
  sources = ["sources.googlecompute.labagent"]
  # provisioner "file" {
  #   source = "../scripts/docker_mirror.py"
  #   destination = "/tmp/docker_mirror.py"
  # }
  provisioner "shell" {
    inline = [
      "curl -Ls https://raw.githubusercontent.com/nuxion/cloudscripts/main/install.sh | sh",
      "sudo cscli -i docker",
      "sudo cscli -i caddy",
      "sudo apt-get update -y",
      "sudo apt-get install -y jq",
      "sudo docker pull jupyter/minimal-notebook:python-3.10.6",
    ]
  }
}
