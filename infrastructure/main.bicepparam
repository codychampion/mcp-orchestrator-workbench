using './main.bicep'

param environment = 'dev'
param baseName = 'mcp-orchestrator'
param enableAuth = true

// These should be provided via Azure DevOps variable groups or command line
param clientId = readEnvironmentVariable('AZURE_CLIENT_ID', '')
param clientSecret = readEnvironmentVariable('AZURE_CLIENT_SECRET', '')
param githubToken = readEnvironmentVariable('GITHUB_TOKEN', '')
