import { InjectionToken } from '@angular/core';

/** URL base da API (definida por environment em `app.config.ts`). */
export const API_BASE_URL = new InjectionToken<string>('API_BASE_URL');
