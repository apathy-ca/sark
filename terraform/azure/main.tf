provider "azurerm" {
  features {
    key_vault {
      purge_soft_delete_on_destroy = true
    }
  }
}

# Resource Group
resource "azurerm_resource_group" "main" {
  name     = var.resource_group_name
  location = var.location

  tags = merge(
    var.tags,
    {
      Environment = var.environment
    }
  )
}

# Virtual Network
resource "azurerm_virtual_network" "main" {
  name                = "${var.cluster_name}-vnet"
  address_space       = var.vnet_address_space
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name

  tags = var.tags
}

# Subnet for AKS
resource "azurerm_subnet" "aks" {
  name                 = "${var.cluster_name}-subnet"
  resource_group_name  = azurerm_resource_group.main.name
  virtual_network_name = azurerm_virtual_network.main.name
  address_prefixes     = var.subnet_address_prefixes
}

# Log Analytics Workspace for monitoring
resource "azurerm_log_analytics_workspace" "main" {
  count = var.enable_monitoring ? 1 : 0

  name                = "${var.cluster_name}-logs"
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  sku                 = "PerGB2018"
  retention_in_days   = 30

  tags = var.tags
}

# AKS Cluster
resource "azurerm_kubernetes_cluster" "main" {
  name                = var.cluster_name
  location            = azurerm_resource_group.main.location
  resource_group_name = azurerm_resource_group.main.name
  dns_prefix          = var.cluster_name
  kubernetes_version  = var.kubernetes_version

  # Managed identity
  identity {
    type = "SystemAssigned"
  }

  # Default node pool
  default_node_pool {
    name                = "default"
    vm_size             = var.node_vm_size
    vnet_subnet_id      = azurerm_subnet.aks.id
    os_disk_size_gb     = var.os_disk_size_gb
    type                = "VirtualMachineScaleSets"
    enable_auto_scaling = var.enable_auto_scaling
    node_count          = var.node_count
    min_count           = var.enable_auto_scaling ? var.node_min_count : null
    max_count           = var.enable_auto_scaling ? var.node_max_count : null
    max_pods            = 110

    upgrade_settings {
      max_surge = "10%"
    }

    tags = var.tags
  }

  # Network profile
  network_profile {
    network_plugin    = var.network_plugin
    network_policy    = var.network_policy
    load_balancer_sku = "standard"
    outbound_type     = "loadBalancer"
  }

  # Azure Monitor
  dynamic "oms_agent" {
    for_each = var.enable_monitoring ? [1] : []
    content {
      log_analytics_workspace_id = azurerm_log_analytics_workspace.main[0].id
    }
  }

  # Azure Policy add-on
  dynamic "azure_policy_enabled" {
    for_each = var.enable_azure_policy ? [1] : []
    content {
      azure_policy_enabled = true
    }
  }

  # Auto-upgrade channel
  automatic_channel_upgrade = "stable"

  # Maintenance window
  maintenance_window {
    allowed {
      day   = "Sunday"
      hours = [3, 4]
    }
  }

  # RBAC and Azure AD
  azure_active_directory_role_based_access_control {
    managed            = true
    azure_rbac_enabled = true
  }

  tags = var.tags
}

# Container Registry
resource "azurerm_container_registry" "main" {
  name                = replace("${var.cluster_name}acr", "-", "")
  resource_group_name = azurerm_resource_group.main.name
  location            = azurerm_resource_group.main.location
  sku                 = "Standard"
  admin_enabled       = false

  identity {
    type = "SystemAssigned"
  }

  tags = var.tags
}

# Grant AKS access to ACR
resource "azurerm_role_assignment" "acr_pull" {
  principal_id                     = azurerm_kubernetes_cluster.main.kubelet_identity[0].object_id
  role_definition_name             = "AcrPull"
  scope                            = azurerm_container_registry.main.id
  skip_service_principal_aad_check = true
}

# Configure kubectl
provider "kubernetes" {
  host                   = azurerm_kubernetes_cluster.main.kube_config[0].host
  client_certificate     = base64decode(azurerm_kubernetes_cluster.main.kube_config[0].client_certificate)
  client_key             = base64decode(azurerm_kubernetes_cluster.main.kube_config[0].client_key)
  cluster_ca_certificate = base64decode(azurerm_kubernetes_cluster.main.kube_config[0].cluster_ca_certificate)
}

provider "helm" {
  kubernetes {
    host                   = azurerm_kubernetes_cluster.main.kube_config[0].host
    client_certificate     = base64decode(azurerm_kubernetes_cluster.main.kube_config[0].client_certificate)
    client_key             = base64decode(azurerm_kubernetes_cluster.main.kube_config[0].client_key)
    cluster_ca_certificate = base64decode(azurerm_kubernetes_cluster.main.kube_config[0].cluster_ca_certificate)
  }
}

# Install cert-manager
resource "helm_release" "cert_manager" {
  name       = "cert-manager"
  repository = "https://charts.jetstack.io"
  chart      = "cert-manager"
  namespace  = "cert-manager"
  version    = "v1.13.0"

  create_namespace = true

  set {
    name  = "installCRDs"
    value = "true"
  }

  depends_on = [azurerm_kubernetes_cluster.main]
}

# Install metrics-server
resource "helm_release" "metrics_server" {
  name       = "metrics-server"
  repository = "https://kubernetes-sigs.github.io/metrics-server/"
  chart      = "metrics-server"
  namespace  = "kube-system"
  version    = "3.11.0"

  depends_on = [azurerm_kubernetes_cluster.main]
}

# Install Azure Application Gateway Ingress Controller (optional)
# Uncomment if using Application Gateway
# resource "helm_release" "agic" {
#   name       = "ingress-azure"
#   repository = "https://appgwingress.blob.core.windows.net/ingress-azure-helm-package/"
#   chart      = "ingress-azure"
#   namespace  = "default"
#   version    = "1.7.0"
#
#   depends_on = [azurerm_kubernetes_cluster.main]
# }
