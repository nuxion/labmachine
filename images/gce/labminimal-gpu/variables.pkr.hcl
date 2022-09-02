variable "project_id" {
	type = string
}


variable "img_version" {
  type = string
}

variable "zone" {
	type = string
	default = "us-east1-c"
}

variable "disk_type" {
	type = string
	default = "pd-standard"
}

variable "machine_type" {
	type = string
	default = "n1-standard-1"
}
