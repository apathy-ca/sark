# SARK Terraform Infrastructure

Infrastructure as Code (IaC) for deploying SARK to major cloud providers using Terraform.

## Overview

This directory contains Terraform configurations to provision production-ready Kubernetes clusters and supporting infrastructure on:

- **AWS EKS** - Amazon Elastic Kubernetes Service
- **GCP GKE** - Google Kubernetes Engine
- **Azure AKS** - Azure Kubernetes Service

## Directory Structure

```
terraform/
├── aws/                    # AWS EKS configuration
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── versions.tf
│   └── terraform.tfvars.example
├── gcp/                    # GCP GKE configuration
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── versions.tf
│   └── terraform.tfvars.example
├── azure/                  # Azure AKS configuration
│   ├── main.tf
│   ├── variables.tf
│   ├── outputs.tf
│   ├── versions.tf
│   └── terraform.tfvars.example
└── README.md              # This file
```

## Prerequisites

### Required Tools

- [Terraform](https://www.terraform.io/downloads) >= 1.6.0
- Cloud provider CLI:
  - **AWS**: [AWS CLI](https://aws.amazon.com/cli/) >= 2.0
  - **GCP**: [gcloud CLI](https://cloud.google.com/sdk/docs/install)
  - **Azure**: [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli) >= 2.0
- [kubectl](https://kubernetes.io/docs/tasks/tools/) >= 1.28
- [helm](https://helm.sh/docs/intro/install/) >= 3.0

### Cloud Provider Authentication

#### AWS
```bash
# Configure AWS credentials
aws configure

# Or use environment variables
export AWS_ACCESS_KEY_ID="your-access-key"
export AWS_SECRET_ACCESS_KEY="your-secret-key"
export AWS_DEFAULT_REGION="us-west-2"
```

#### GCP
```bash
# Authenticate with GCP
gcloud auth application-default login

# Set project
gcloud config set project your-project-id
```

#### Azure
```bash
# Login to Azure
az login

# Set subscription
az account set --subscription "your-subscription-id"
```

## Quick Start

### AWS EKS

```bash
# Navigate to AWS directory
cd terraform/aws

# Copy and edit terraform.tfvars
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

# Initialize Terraform
terraform init

# Plan deployment
terraform plan

# Apply configuration
terraform apply

# Configure kubectl
aws eks --region us-west-2 update-kubeconfig --name sark-cluster

# Verify cluster access
kubectl get nodes
```

### GCP GKE

```bash
# Navigate to GCP directory
cd terraform/gcp

# Copy and edit terraform.tfvars
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

# Initialize Terraform
terraform init

# Plan deployment
terraform plan

# Apply configuration
terraform apply

# Configure kubectl
gcloud container clusters get-credentials sark-cluster --region us-central1

# Verify cluster access
kubectl get nodes
```

### Azure AKS

```bash
# Navigate to Azure directory
cd terraform/azure

# Copy and edit terraform.tfvars
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your values

# Initialize Terraform
terraform init

# Plan deployment
terraform plan

# Apply configuration
terraform apply

# Configure kubectl
az aks get-credentials --resource-group sark-rg --name sark-cluster

# Verify cluster access
kubectl get nodes
```

## What Gets Deployed

### AWS EKS

**Networking:**
- VPC with public and private subnets across 3 AZs
- NAT Gateways for private subnet internet access
- VPC endpoints for AWS services

**Kubernetes:**
- EKS cluster with managed control plane
- EKS managed node group with auto-scaling (1-10 nodes)
- IAM roles and policies for cluster and nodes
- KMS encryption for secrets and EBS volumes

**Container Registry:**
- ECR repository with image scanning
- Lifecycle policies to manage image retention

**Add-ons:**
- AWS Load Balancer Controller
- Metrics Server
- Prometheus (optional)

**Estimated Monthly Cost:** $200-400 (3 t3.medium nodes, NAT gateways, EKS control plane)

### GCP GKE

**Networking:**
- VPC network with custom subnet
- Cloud Router and Cloud NAT
- Secondary IP ranges for pods and services

**Kubernetes:**
- GKE Standard or Autopilot cluster
- Node pool with auto-scaling (1-10 nodes)
- Workload Identity enabled
- Binary Authorization configured

**Container Registry:**
- Artifact Registry repository for Docker images

**Features:**
- GKE Monitoring and Logging
- Managed Prometheus (GMP)
- Network Policy (enabled)
- Shielded GKE nodes

**Add-ons:**
- cert-manager
- Metrics Server (for Standard clusters)

**Estimated Monthly Cost:** $220-450 (3 e2-medium nodes, GKE management fee)

### Azure AKS

**Networking:**
- Virtual Network (VNet)
- Subnet for AKS nodes
- Azure CNI networking

**Kubernetes:**
- AKS cluster with managed control plane
- Virtual Machine Scale Set for nodes
- Auto-scaling enabled (1-10 nodes)
- Azure AD integration for RBAC

**Container Registry:**
- Azure Container Registry (ACR)
- Managed identity integration

**Monitoring:**
- Azure Monitor for containers
- Log Analytics workspace

**Add-ons:**
- cert-manager
- Metrics Server
- Azure Policy (optional)

**Estimated Monthly Cost:** $200-380 (3 Standard_D2s_v3 nodes, no control plane fee)

## Remote State Management

### AWS S3 Backend

Create S3 bucket and DynamoDB table:

```bash
# Create S3 bucket
aws s3api create-bucket \
  --bucket your-terraform-state-bucket \
  --region us-west-2 \
  --create-bucket-configuration LocationConstraint=us-west-2

# Enable versioning
aws s3api put-bucket-versioning \
  --bucket your-terraform-state-bucket \
  --versioning-configuration Status=Enabled

# Create DynamoDB table for state locking
aws dynamodb create-table \
  --table-name terraform-state-lock \
  --attribute-definitions AttributeName=LockID,AttributeType=S \
  --key-schema AttributeName=LockID,KeyType=HASH \
  --billing-mode PAY_PER_REQUEST
```

Uncomment backend configuration in `terraform/aws/versions.tf`.

### GCP GCS Backend

Create GCS bucket:

```bash
# Create bucket
gcloud storage buckets create gs://your-terraform-state-bucket \
  --project=your-project-id \
  --location=us-central1 \
  --uniform-bucket-level-access

# Enable versioning
gcloud storage buckets update gs://your-terraform-state-bucket \
  --versioning
```

Uncomment backend configuration in `terraform/gcp/versions.tf`.

### Azure Storage Backend

Create storage account and container:

```bash
# Create resource group
az group create --name terraform-state-rg --location eastus

# Create storage account
az storage account create \
  --name terraformstate \
  --resource-group terraform-state-rg \
  --location eastus \
  --sku Standard_LRS

# Create container
az storage container create \
  --name tfstate \
  --account-name terraformstate
```

Uncomment backend configuration in `terraform/azure/versions.tf`.

## Configuration Variables

### Common Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `cluster_name` | Kubernetes cluster name | `sark-cluster` |
| `environment` | Environment name | `production` |
| `node_count` | Initial number of nodes | `3` |
| `node_min_count` | Minimum nodes (auto-scaling) | `1` |
| `node_max_count` | Maximum nodes (auto-scaling) | `10` |
| `enable_monitoring` | Enable monitoring/logging | `true` |

See provider-specific `variables.tf` for complete lists.

## Deploying the SARK Application

After provisioning infrastructure:

1. **Configure kubectl** (output from Terraform)
2. **Push container image** to the container registry
3. **Deploy using Helm**:

```bash
# Update image in values file
helm install sark ../../helm/sark \
  --set image.repository=<registry-url>/sark \
  --set image.tag=v0.1.0 \
  --namespace production \
  --create-namespace
```

See [DEPLOYMENT.md](../docs/DEPLOYMENT.md) for detailed instructions.

## Updating Infrastructure

```bash
# Make changes to terraform.tfvars or *.tf files

# Plan changes
terraform plan

# Apply changes
terraform apply

# Terraform will show what will change before applying
```

## Destroying Infrastructure

**⚠️ WARNING: This will delete all resources including data!**

```bash
# Destroy all resources
terraform destroy

# Or destroy specific resources
terraform destroy -target=module.eks
```

## Multi-Environment Setup

### Option 1: Separate Directories

```
terraform/
├── aws/
│   ├── production/
│   ├── staging/
│   └── development/
```

### Option 2: Terraform Workspaces

```bash
# Create workspaces
terraform workspace new production
terraform workspace new staging
terraform workspace new development

# Switch between workspaces
terraform workspace select production

# Use workspace name in configuration
locals {
  environment = terraform.workspace
}
```

### Option 3: Multiple tfvars Files

```bash
# Create environment-specific tfvars
terraform apply -var-file="production.tfvars"
terraform apply -var-file="staging.tfvars"
```

## Troubleshooting

### Terraform State Lock

```bash
# Force unlock (use carefully)
terraform force-unlock <lock-id>
```

### Provider Authentication Issues

```bash
# AWS
aws sts get-caller-identity

# GCP
gcloud auth list
gcloud config list

# Azure
az account show
```

### Cluster Access Issues

```bash
# Reconfigure kubectl
# See "configure_kubectl" output from terraform

# Verify credentials
kubectl cluster-info
kubectl get nodes
```

### Resource Quota Exceeded

Check cloud provider quotas:
- AWS: Service Quotas console
- GCP: IAM & Admin > Quotas
- Azure: Subscriptions > Usage + quotas

## Security Best Practices

1. **Never commit credentials** - Use `.gitignore` for sensitive files
2. **Use remote state** - Enable encryption and versioning
3. **Enable state locking** - Prevent concurrent modifications
4. **Rotate credentials** - Regularly rotate access keys and tokens
5. **Use least privilege** - Grant minimal required permissions
6. **Enable encryption** - KMS/CMK for secrets and disks
7. **Enable audit logging** - CloudTrail/Cloud Audit Logs/Activity Log
8. **Use private endpoints** - Restrict cluster API access
9. **Scan container images** - Enable image scanning in registries
10. **Review changes** - Always run `terraform plan` before `apply`

## Cost Optimization

1. **Right-size instances** - Start small and scale as needed
2. **Use spot/preemptible instances** - For non-critical workloads
3. **Enable auto-scaling** - Scale down during off-hours
4. **Clean up unused resources** - Remove old AMIs, snapshots, images
5. **Use resource tags** - Track costs by project/environment
6. **Set budget alerts** - Get notified of unexpected costs
7. **Review regularly** - Use cloud provider cost analysis tools

## Support

- **Terraform Issues**: Check Terraform and provider documentation
- **Cloud Provider Issues**: Consult respective cloud provider support
- **SARK Application Issues**: See [docs/](../docs/) directory

## Additional Resources

- [Terraform AWS Provider](https://registry.terraform.io/providers/hashicorp/aws/latest/docs)
- [Terraform Google Provider](https://registry.terraform.io/providers/hashicorp/google/latest/docs)
- [Terraform Azure Provider](https://registry.terraform.io/providers/hashicorp/azurerm/latest/docs)
- [EKS Best Practices](https://aws.github.io/aws-eks-best-practices/)
- [GKE Best Practices](https://cloud.google.com/kubernetes-engine/docs/best-practices)
- [AKS Best Practices](https://learn.microsoft.com/en-us/azure/aks/best-practices)
