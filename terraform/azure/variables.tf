variable "resource_group_name" {
  description = "Resource group name"
  type        = string
  default     = "sark-rg"
}

variable "location" {
  description = "Azure region"
  type        = string
  default     = "East US"
}

variable "cluster_name" {
  description = "AKS cluster name"
  type        = string
  default     = "sark-cluster"
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

variable "vnet_address_space" {
  description = "Virtual network address space"
  type        = list(string)
  default     = ["10.0.0.0/16"]
}

variable "subnet_address_prefixes" {
  description = "Subnet address prefixes"
  type        = list(string)
  default     = ["10.0.1.0/24"]
}

variable "node_vm_size" {
  description = "VM size for nodes"
  type        = string
  default     = "Standard_D2s_v3"
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

variable "os_disk_size_gb" {
  description = "OS disk size in GB"
  type        = number
  default     = 50
}

variable "enable_auto_scaling" {
  description = "Enable cluster auto scaling"
  type        = bool
  default     = true
}

variable "enable_monitoring" {
  description = "Enable Azure Monitor for containers"
  type        = bool
  default     = true
}

variable "enable_azure_policy" {
  description = "Enable Azure Policy add-on"
  type        = bool
  default     = true
}

variable "network_plugin" {
  description = "Network plugin (azure or kubenet)"
  type        = string
  default     = "azure"
}

variable "network_policy" {
  description = "Network policy (calico or azure)"
  type        = string
  default     = "azure"
}

variable "tags" {
  description = "Tags to apply to resources"
  type        = map(string)
  default = {
    Project    = "sark"
    ManagedBy  = "terraform"
  }
}
