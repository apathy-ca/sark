variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region"
  type        = string
  default     = "us-central1"
}

variable "cluster_name" {
  description = "GKE cluster name"
  type        = string
  default     = "sark-cluster"
}

variable "cluster_location" {
  description = "GKE cluster location (region or zone)"
  type        = string
  default     = "us-central1"
}

variable "kubernetes_version" {
  description = "Kubernetes version"
  type        = string
  default     = "1.28"
}

variable "environment" {
  description = "Environment name"
  type        = string
  default     = "production"
}

variable "network_name" {
  description = "VPC network name"
  type        = string
  default     = "sark-network"
}

variable "subnet_cidr" {
  description = "Subnet CIDR range"
  type        = string
  default     = "10.0.0.0/24"
}

variable "pods_cidr" {
  description = "Secondary IP range for pods"
  type        = string
  default     = "10.1.0.0/16"
}

variable "services_cidr" {
  description = "Secondary IP range for services"
  type        = string
  default     = "10.2.0.0/16"
}

variable "node_machine_type" {
  description = "Machine type for nodes"
  type        = string
  default     = "e2-medium"
}

variable "node_count" {
  description = "Initial number of nodes"
  type        = number
  default     = 3
}

variable "node_min_count" {
  description = "Minimum number of nodes"
  type        = number
  default     = 1
}

variable "node_max_count" {
  description = "Maximum number of nodes"
  type        = number
  default     = 10
}

variable "disk_size_gb" {
  description = "Disk size in GB for nodes"
  type        = number
  default     = 50
}

variable "disk_type" {
  description = "Disk type for nodes"
  type        = string
  default     = "pd-standard"
}

variable "enable_monitoring" {
  description = "Enable GKE monitoring"
  type        = bool
  default     = true
}

variable "enable_logging" {
  description = "Enable GKE logging"
  type        = bool
  default     = true
}

variable "enable_autopilot" {
  description = "Enable GKE Autopilot mode"
  type        = bool
  default     = false
}

variable "labels" {
  description = "Labels to apply to resources"
  type        = map(string)
  default = {
    project    = "sark"
    managed-by = "terraform"
  }
}
