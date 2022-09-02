packer {
  required_plugins {
    googlecompute = {
      version = ">= 0.0.1"
      source  = "github.com/hashicorp/googlecompute"
    }
  }
}

source "googlecompute" "labminimal-gpu" {
  project_id        = var.project_id
  source_image      = "debian-11-bullseye-v20220406"
  ssh_username      = "op"
  zone              = var.zone
  disk_size         = 20
  disk_type         = var.disk_type
  # image_name        = "lab-nvidia-${legacy_isotime("2006-01-02")}"
  image_name        = "lab-minimal-${var.img_version}-gpu"
  image_description = "lab on demand with NVIDIA/GPU support"
  machine_type      = "n1-standard-1"
  accelerator_type  = "projects/${var.project_id}/zones/${var.zone}/acceleratorTypes/nvidia-tesla-t4"
  accelerator_count = 1
  on_host_maintenance = "TERMINATE" # needed for instances with gpu 
}

build {
  sources = ["sources.googlecompute.labminimal-gpu"]
  # provisioner "file" {
  #   source = "../scripts/docker_mirror.py"
  #   destination = "/tmp/docker_mirror.py"
  # }
  # docker image based on github.com/nuxion/containers
  provisioner "shell" {
    inline = [
      "curl -Ls https://raw.githubusercontent.com/nuxion/cloudscripts/main/install.sh | sh",
      "sudo cscli -i docker",
      "sudo cscli -i nvidia-docker",
      "sudo cscli -i caddy",
      "sudo usermod -aG docker `echo $USER`",
      "sudo usermod -aG op `echo $USER`",
      "sudo apt-get update -y",
      "sudo apt-get install -y jq",
      "sudo docker pull nuxion/minimal-jupyter-gpu:0.1.0-cuda11.5",
    ]
  }
}
