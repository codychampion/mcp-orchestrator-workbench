// Shared API configuration
export const API_BASE = window.location.hostname === 'localhost'
  ? 'http://localhost:8100'
  : `http://${window.location.hostname}:8100`;
