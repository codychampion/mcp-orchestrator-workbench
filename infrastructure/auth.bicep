// Authentication configuration for Azure AD
// This module configures Easy Auth for Container Apps

@description('The name of the Container App')
param containerAppName string

@description('The location of resources')
param location string

@description('Azure AD Tenant ID')
param tenantId string

@description('Azure AD Client ID')
param clientId string

@description('Azure AD Client Secret (from Key Vault)')
@secure()
param clientSecret string

@description('Enable authentication')
param enableAuth bool

@description('The redirect URI base (Container App FQDN)')
param redirectUriBase string

// Only apply auth configuration if enabled
resource authConfig 'Microsoft.App/containerApps/authConfigs@2023-05-01' = if (enableAuth) {
  name: '${containerAppName}/current'
  properties: {
    platform: {
      enabled: true
    }
    globalValidation: {
      redirectToProvider: 'azureactivedirectory'
      unauthenticatedClientAction: 'RedirectToLoginPage'
    }
    identityProviders: {
      azureActiveDirectory: {
        enabled: true
        registration: {
          clientId: clientId
          clientSecretSettingName: 'microsoft-provider-authentication-secret'
          openIdIssuer: 'https://login.microsoftonline.com/${tenantId}/v2.0'
        }
        validation: {
          allowedAudiences: [
            'api://${clientId}'
          ]
        }
      }
    }
    login: {
      tokenStore: {
        enabled: true
      }
    }
  }
}

output authConfigured bool = enableAuth
