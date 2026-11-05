import { HttpClient, HttpParams } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { API_BASE_URL } from '../config/api-config';

export type QueryValue = string | number | boolean | null | undefined | readonly (string | number)[];

/** Cliente HTTP único: nenhum componente conhece a URL da API. */
@Injectable({ providedIn: 'root' })
export class ApiClient {
  private readonly http = inject(HttpClient);
  private readonly baseUrl = inject(API_BASE_URL);

  get<T>(path: string, query: Record<string, QueryValue> = {}): Observable<T> {
    return this.http.get<T>(`${this.baseUrl}${path}`, { params: this.toParams(query) });
  }

  private toParams(query: Record<string, QueryValue>): HttpParams {
    let params = new HttpParams();
    for (const [key, value] of Object.entries(query)) {
      if (value === null || value === undefined || value === '') continue;
      if (Array.isArray(value)) {
        for (const item of value) params = params.append(key, String(item));
      } else {
        params = params.append(key, String(value));
      }
    }
    return params;
  }
}
