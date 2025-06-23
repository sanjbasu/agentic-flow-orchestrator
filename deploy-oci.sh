#!/bin/bash

# OCI Deployment Script for Agentic Flow Orchestrator
# This script deploys the application to Oracle Cloud Infrastructure

set -e

# Configuration
PROJECT_NAME="agentic-flow"
OCI_REGION="us-phoenix-1"
COMPARTMENT_ID="${OCI_COMPARTMENT_ID}"
SSH_KEY_PATH="${HOME}/.ssh/id_rsa.pub"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Check dependencies
check_dependencies() {
    log_info "Checking dependencies..."
    
    if ! command -v oci &> /dev/null; then
        log_error "OCI CLI not found. Please install it first."
        exit 1
    fi
    
    if ! command -v docker &> /dev/null; then
        log_error "Docker not found. Please install it first."
        exit 1
    fi
    
    if ! command -v docker-compose &> /dev/null; then
        log_error "Docker Compose not found. Please install it first."
        exit 1
    fi
}

# Create compute instance
create_instance() {
    log_info "Creating OCI compute instance..."
    
    local instance_name="${PROJECT_NAME}-instance"
    local image_id="ocid1.image.oc1.phx.aaaaaaaa6hooptnlbfwr5lwemqjbu3uqzqntc6rz4wj36hkb44t4o6j3k2ta" # Ubuntu 22.04
    local shape="VM.Standard.E2.1.Micro" # Always Free eligible
    local subnet_id="${OCI_SUBNET_ID}"
    
    # Check if instance already exists
    existing_instance=$(oci compute instance list \
        --compartment-id "${COMPARTMENT_ID}" \
        --display-name "${instance_name}" \
        --lifecycle-state RUNNING \
        --query 'data[0].id' \
        --raw-output 2>/dev/null || echo "null")
    
    if [ "${existing_instance}" != "null" ]; then
        log_warn "Instance ${instance_name} already exists with ID: ${existing_instance}"
        INSTANCE_ID="${existing_instance}"
        return
    fi
    
    # Create instance
    local create_output=$(oci compute instance launch \
        --availability-domain "${OCI_AVAILABILITY_DOMAIN}" \
        --compartment-id "${COMPARTMENT_ID}" \
        --display-name "${instance_name}" \
        --image-id "${image_id}" \
        --shape "${shape}" \
        --subnet-id "${subnet_id}" \
        --ssh-authorized-keys-file "${SSH_KEY_PATH}" \
        --user-data-file cloud-init.yaml \
        --wait-for-state RUNNING)
    
    INSTANCE_ID=$(echo "${create_output}" | jq -r '.data.id')
    log_info "Instance created with ID: ${INSTANCE_ID}"
}

# Get instance public IP
get_instance_ip() {
    log_info "Getting instance public IP..."
    
    INSTANCE_IP=$(oci compute instance list-vnics \
        --instance-id "${INSTANCE_ID}" \
        --query 'data[0]."public-ip"' \
        --raw-output)
    
    log_info "Instance IP: ${INSTANCE_IP}"
}

# Deploy application
deploy_application() {
    log_info "Deploying application to instance..."
    
    # Wait for instance to be ready
    log_info "Waiting for instance to be ready..."
    sleep 60
    
    # Copy files to instance
    log_info "Copying files to instance..."
    scp -o StrictHostKeyChecking=no -r . ubuntu@"${INSTANCE_IP}":/home/ubuntu/agentic-flow/
    
    # Install dependencies and start services
    log_info "Installing dependencies and starting services..."
    ssh -o StrictHostKeyChecking=no ubuntu@"${INSTANCE_IP}" << 'EOF'
        cd /home/ubuntu/agentic-flow
        
        # Update system
        sudo apt-get update
        sudo apt-get install -y docker.io docker-compose-plugin
        
        # Add user to docker group
        sudo usermod -aG docker ubuntu
        
        # Start docker
        sudo systemctl start docker
        sudo systemctl enable docker
        
        # Build and start services
        sudo docker compose up -d --build
        
        # Check services
        sudo docker compose ps
EOF
    
    log_info "Application deployed successfully!"
    log_info "Access the application at: http://${INSTANCE_IP}"
}

# Create cloud-init configuration
create_cloud_init() {
    log_info "Creating cloud-init configuration..."
    
    cat > cloud-init.yaml << 'EOF'
#cloud-config
package_update: true
package_upgrade: true

packages:
  - docker.io
  - docker-compose-plugin
  - git
  - curl
  - wget
  - unzip

runcmd:
  - systemctl start docker
  - systemctl enable docker
  - usermod -aG docker ubuntu
  - mkdir -p /home/ubuntu/agentic-flow
  - chown ubuntu:ubuntu /home/ubuntu/agentic-flow

write_files:
  - path: /etc/docker/daemon.json
    content: |
      {
        "log-driver": "json-file",
        "log-opts": {
          "max-size": "10m",
          "max-file": "3"
        }
      }
    owner: root:root
    permissions: '0644'

final_message: "Cloud-init setup complete!"
EOF
}

# Main deployment function
main() {
    log_info "Starting OCI deployment for ${PROJECT_NAME}..."
    
    # Check required environment variables
    if [ -z "${OCI_COMPARTMENT_ID}" ]; then
        log_error "OCI_COMPARTMENT_ID environment variable is required"
        exit 1
    fi
    
    if [ -z "${OCI_SUBNET_ID}" ]; then
        log_error "OCI_SUBNET_ID environment variable is required"
        exit 1
    fi
    
    if [ -z "${OCI_AVAILABILITY_DOMAIN}" ]; then
        log_error "OCI_AVAILABILITY_DOMAIN environment variable is required"
        exit 1
    fi
    
    check_dependencies
    create_cloud_init
    create_instance
    get_instance_ip
    deploy_application
    
    log_info "Deployment completed successfully!"
    log_info "Application URL: http://${INSTANCE_IP}"
    log_info "SSH command: ssh ubuntu@${INSTANCE_IP}"
}

# Cleanup function
cleanup() {
    log_info "Cleaning up resources..."
    
    if [ -n "${INSTANCE_ID}" ]; then
        log_info "Terminating instance ${INSTANCE_ID}..."
        oci compute instance terminate --instance-id "${INSTANCE_ID}" --force
    fi
    
    # Clean up local files
    rm -f cloud-init.yaml
}

# Handle script arguments
case "${1:-deploy}" in
    "deploy")
        main
        ;;
    "cleanup")
        cleanup
        ;;
    "help")
        echo "Usage: $0 [deploy|cleanup|help]"
        echo "  deploy  - Deploy the application (default)"
        echo "  cleanup - Clean up resources"
        echo "  help    - Show this help message"
        ;;
    *)
        log_error "Unknown command: $1"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac
