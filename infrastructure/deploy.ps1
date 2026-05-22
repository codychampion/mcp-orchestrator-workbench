# PowerShell deployment script for MCP Orchestrator infrastructure

param(
    [string]$Environment = "dev",
    [string]$ResourceGroup = "mcp-orchestrator-$Environment",
    [string]$Location = "eastus",
    [bool]$EnableAuth = $true
)

Write-Host "Deploying MCP Orchestrator to Azure..." -ForegroundColor Green
Write-Host "Environment: $Environment"
Write-Host "Resource Group: $ResourceGroup"
Write-Host "Location: $Location"
Write-Host "Enable Auth: $EnableAuth"

# Check for required environment variables
if (-not $env:AZURE_CLIENT_ID) {
    Write-Error "AZURE_CLIENT_ID environment variable is required"
    exit 1
}

if ($EnableAuth -and -not $env:AZURE_CLIENT_SECRET) {
    Write-Error "AZURE_CLIENT_SECRET environment variable is required when auth is enabled"
    exit 1
}

if (-not $env:GITHUB_TOKEN) {
    Write-Error "GITHUB_TOKEN environment variable is required"
    exit 1
}

# Create resource group if it doesn't exist
Write-Host "Creating resource group..." -ForegroundColor Yellow
az group create --name $ResourceGroup --location $Location

# Deploy infrastructure
Write-Host "Deploying infrastructure..." -ForegroundColor Yellow
az deployment group create `
    --resource-group $ResourceGroup `
    --template-file main.bicep `
    --parameters `
        environment=$Environment `
        enableAuth=$EnableAuth `
        clientId=$env:AZURE_CLIENT_ID `
        clientSecret=$env:AZURE_CLIENT_SECRET `
        githubToken=$env:GITHUB_TOKEN

# Get outputs
Write-Host "Deployment complete!" -ForegroundColor Green
Write-Host "Fetching deployment outputs..." -ForegroundColor Yellow

$frontendUrl = az deployment group show `
    --resource-group $ResourceGroup `
    --name main `
    --query properties.outputs.frontendUrl.value `
    --output tsv

Write-Host "Frontend URL: $frontendUrl" -ForegroundColor Green
Write-Host "Deployment successful!" -ForegroundColor Green
