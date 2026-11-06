declare const __API_BASE_URL__: string | undefined;

export const environment = {
  production: true,
  apiBaseUrl: typeof __API_BASE_URL__ !== 'undefined' ? __API_BASE_URL__ : 'http://localhost:8000/api/v1',
};
