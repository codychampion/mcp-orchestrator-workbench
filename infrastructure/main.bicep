// Main Bicep template for MCP Orchestrator
// Deploys: Container Apps, Container Registry, Log Analytics, App Insights, Key Vault

targetScope = 'resourceGroup'

@description('The environment name (dev, staging, prod)')
param environment string = 'dev'

@description('The Azure region for all resources')
param location string = resourceGroup().location

@description('The base name for all resources')
param baseName string = 'mcp-orchestrator'

@description('Enable Azure AD authentication')
param enableAuth bool = true

@description('Azure AD Tenant ID')
param tenantId string = subscription().tenantId

@description('Azure AD Client ID for authentication')
@secure()
param clientId string

@description('Azure AD Client Secret for authentication')
@secure()
param clientSecret string

@description('GitHub token for accessing models')
@secure()
param githubToken string

// Variables
var uniqueSuffix = uniqueString(resourceGroup().id)
var containerRegistryName = '${replace(baseName, '-', '')}${uniqueSuffix}'
var logAnalyticsName = '${baseName}-logs-${environment}'
var appInsightsName = '${baseName}-insights-${environment}'
var keyVaultName = '${replace(baseName, '-', '')}kv${uniqueSuffix}'
var containerAppEnvName = '${baseName}-env-${environment}'

// Log Analytics Workspace
resource logAnalytics 'Microsoft.OperationalInsights/workspaces@2022-10-01' = {
  name: logAnalyticsName
  location: location
  properties: {
    sku: {
      name: 'PerGB2018'
    }
    retentionInDays: 30
  }
}

// Application Insights
resource appInsights 'Microsoft.Insights/components@2020-02-02' = {
  name: appInsightsName
  location: location
  kind: 'web'
  properties: {
    Application_Type: 'web'
    WorkspaceResourceId: logAnalytics.id
  }
}

// Container Registry
resource containerRegistry 'Microsoft.ContainerRegistry/registries@2023-01-01-preview' = {
  name: containerRegistryName
  location: location
  sku: {
    name: 'Basic'
  }
  properties: {
    adminUserEnabled: true
  }
}

// Key Vault for secrets
resource keyVault 'Microsoft.KeyVault/vaults@2023-02-01' = {
  name: keyVaultName
  location: location
  properties: {
    sku: {
      family: 'A'
      name: 'standard'
    }
    tenantId: tenantId
    accessPolicies: []
    enableRbacAuthorization: true
  }
}

// Store secrets in Key Vault
resource clientSecretSecret 'Microsoft.KeyVault/vaults/secrets@2023-02-01' = if (enableAuth) {
  parent: keyVault
  name: 'client-secret'
  properties: {
    value: clientSecret
  }
}

resource githubTokenSecret 'Microsoft.KeyVault/vaults/secrets@2023-02-01' = {
  parent: keyVault
  name: 'github-token'
  properties: {
    value: githubToken
  }
}

// Container App Environment
resource containerAppEnvironment 'Microsoft.App/managedEnvironments@2023-05-01' = {
  name: containerAppEnvName
  location: location
  properties: {
    appLogsConfiguration: {
      destination: 'log-analytics'
      logAnalyticsConfiguration: {
        customerId: logAnalytics.properties.customerId
        sharedKey: logAnalytics.listKeys().primarySharedKey
      }
    }
  }
}

// MCP Server Container App
resource mcpServerApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: '${baseName}-mcp-server-${environment}'
  location: location
  properties: {
    managedEnvironmentId: containerAppEnvironment.id
    configuration: {
      ingress: {
        external: false
        targetPort: 8000
        transport: 'http'
      }
      registries: [
        {
          server: containerRegistry.properties.loginServer
          username: containerRegistry.name
          passwordSecretRef: 'registry-password'
        }
      ]
      secrets: [
        {
          name: 'registry-password'
          value: containerRegistry.listCredentials().passwords[0].value
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'mcp-server'
          image: '${containerRegistry.properties.loginServer}/mcp-server:latest'
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
}

// Orchestrator Service Container App
resource orchestratorApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: '${baseName}-orchestrator-${environment}'
  location: location
  properties: {
    managedEnvironmentId: containerAppEnvironment.id
    configuration: {
      ingress: {
        external: false
        targetPort: 8100
        transport: 'http'
      }
      registries: [
        {
          server: containerRegistry.properties.loginServer
          username: containerRegistry.name
          passwordSecretRef: 'registry-password'
        }
      ]
      secrets: [
        {
          name: 'registry-password'
          value: containerRegistry.listCredentials().passwords[0].value
        }
        {
          name: 'github-token'
          keyVaultUrl: '${keyVault.properties.vaultUri}secrets/github-token'
          identity: 'system'
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'orchestrator'
          image: '${containerRegistry.properties.loginServer}/orchestrator:latest'
          resources: {
            cpu: json('0.5')
            memory: '1Gi'
          }
          env: [
            {
              name: 'MCP_SERVER_URL'
              value: 'http://${mcpServerApp.properties.configuration.ingress.fqdn}/mcp'
            }
            {
              name: 'GITHUB_TOKEN'
              secretRef: 'github-token'
            }
            {
              name: 'LLM_PROVIDER'
              value: 'github'
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 5
      }
    }
  }
  identity: {
    type: 'SystemAssigned'
  }
}

// Frontend Container App with optional authentication
resource frontendApp 'Microsoft.App/containerApps@2023-05-01' = {
  name: '${baseName}-frontend-${environment}'
  location: location
  properties: {
    managedEnvironmentId: containerAppEnvironment.id
    configuration: {
      ingress: {
        external: true
        targetPort: 80
        transport: 'http'
        allowInsecure: false
      }
      registries: [
        {
          server: containerRegistry.properties.loginServer
          username: containerRegistry.name
          passwordSecretRef: 'registry-password'
        }
      ]
      secrets: [
        {
          name: 'registry-password'
          value: containerRegistry.listCredentials().passwords[0].value
        }
      ]
    }
    template: {
      containers: [
        {
          name: 'frontend'
          image: '${containerRegistry.properties.loginServer}/frontend:latest'
          resources: {
            cpu: json('0.25')
            memory: '0.5Gi'
          }
          env: [
            {
              name: 'VITE_API_URL'
              value: 'https://${orchestratorApp.properties.configuration.ingress.fqdn}'
            }
            {
              name: 'VITE_AUTH_ENABLED'
              value: enableAuth ? 'true' : 'false'
            }
          ]
        }
      ]
      scale: {
        minReplicas: 1
        maxReplicas: 3
      }
    }
  }
}

// Role assignments for Key Vault access
resource orchestratorKeyVaultAccess 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(keyVault.id, orchestratorApp.id, 'Key Vault Secrets User')
  scope: keyVault
  properties: {
    roleDefinitionId: subscriptionResourceId('Microsoft.Authorization/roleDefinitions', '4633458b-17de-408a-b874-0445c86b69e6') // Key Vault Secrets User
    principalId: orchestratorApp.identity.principalId
    principalType: 'ServicePrincipal'
  }
}

// Outputs
output frontendUrl string = 'https://${frontendApp.properties.configuration.ingress.fqdn}'
output orchestratorUrl string = 'https://${orchestratorApp.properties.configuration.ingress.fqdn}'
output containerRegistryLoginServer string = containerRegistry.properties.loginServer
output keyVaultName string = keyVault.name
output logAnalyticsWorkspaceId string = logAnalytics.id
output appInsightsConnectionString string = appInsights.properties.ConnectionString
