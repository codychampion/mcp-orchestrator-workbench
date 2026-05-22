#!/bin/bash

# Deployment script for MCP Orchestrator infrastructure

set -e

# Parse arguments
ENVIRONMENT=${1:-dev}
RESOURCE_GROUP=${2:-mcp-orchestrator-$ENVIRONMENT}
LOCATION=${3:-eastus}
ENABLE_AUTH=${4:-true}

echo "Deploying MCP Orchestrator to Azure..."
echo "Environment: $ENVIRONMENT"
echo "Resource Group: $RESOURCE_GROUP"
echo "Location: $LOCATION"
echo "Enable Auth: $ENABLE_AUTH"

# Check for required environment variables
if [ -z "$AZURE_CLIENT_ID" ]; then
  echo "Error: AZURE_CLIENT_ID environment variable is required"
  exit 1
fi

if [ "$ENABLE_AUTH" = "true" ] && [ -z "$AZURE_CLIENT_SECRET" ]; then
  echo "Error: AZURE_CLIENT_SECRET environment variable is required when auth is enabled"
  exit 1
fi

if [ -z "$GITHUB_TOKEN" ]; then
  echo "Error: GITHUB_TOKEN environment variable is required"
  exit 1
fi

# Create resource group if it doesn't exist
echo "Creating resource group..."
az group create --name $RESOURCE_GROUP --location $LOCATION

# Deploy infrastructure
echo "Deploying infrastructure..."
az deployment group create \
  --resource-group $RESOURCE_GROUP \
  --template-file main.bicep \
  --parameters \
    environment=$ENVIRONMENT \
    enableAuth=$ENABLE_AUTH \
    clientId=$AZURE_CLIENT_ID \
    clientSecret=$AZURE_CLIENT_SECRET \
    githubToken=$GITHUB_TOKEN

# Get outputs
echo "Deployment complete!"
echo "Fetching deployment outputs..."

FRONTEND_URL=$(az deployment group show \
  --resource-group $RESOURCE_GROUP \
  --name main \
  --query properties.outputs.frontendUrl.value \
  --output tsv)

echo "Frontend URL: $FRONTEND_URL"
echo "Deployment successful!"
