import { Injectable, inject, signal } from '@angular/core';
import { Observable } from 'rxjs';

import {
  CoverageFilterOptions,
  CoverageByImmunizerResponse,
  CoverageFilters,
  CoverageHistoryResponse,
  CoverageResponse,
  VaccinationAnalyticsQuery,
  VaccinationAnalyticsResponse,
  AnalyticsUploadResponse,
  DataQualityResponse,
  GeoResponse,
  ModelResponse,
  MunicipalityDetailResponse,
  MunicipalityListResponse,
  PredictionResponse,
} from '../models/api.models';
import { ApiClient, QueryValue } from './api-client.service';

function filterQuery(filters: CoverageFilters): Record<string, QueryValue> {
  return {
    year: filters.year,
    year_from: filters.year_from,
    year_to: filters.year_to,
    immunizer: filters.immunizer,
    deficit_class: filters.deficit_class,
    municipality_code: filters.municipality_code,
  };
}

@Injectable({ providedIn: 'root' })
export class CoverageService {
  private readonly api = inject(ApiClient);

  overview(filters: CoverageFilters, rankingLimit = 10): Observable<CoverageResponse> {
    return this.api.get('/coverage', { ...filterQuery(filters), ranking_limit: rankingLimit });
  }

  byImmunizer(filters: CoverageFilters): Observable<CoverageByImmunizerResponse> {
    return this.api.get('/coverage/immunizers', filterQuery(filters));
  }

  filters(): Observable<CoverageFilterOptions> {
    return this.api.get('/coverage/filters');
  }

  history(filters: CoverageFilters): Observable<CoverageHistoryResponse> {
    return this.api.get('/coverage/history', filterQuery(filters));
  }
}

@Injectable({ providedIn: 'root' })
export class MunicipalitiesService {
  private readonly api = inject(ApiClient);

  list(filters: CoverageFilters, limit = 100, offset = 0): Observable<MunicipalityListResponse> {
    return this.api.get('/municipalities', { ...filterQuery(filters), limit, offset });
  }

  detail(code: string, filters: CoverageFilters = {}): Observable<MunicipalityDetailResponse> {
    return this.api.get(`/municipalities/${encodeURIComponent(code)}`, filterQuery(filters));
  }
}

export interface PredictionQuery {
  year?: number | null;
  municipality_code?: string | null;
  immunizer?: string | null;
  predicted_class?: string | null;
  limit?: number;
  offset?: number;
}

@Injectable({ providedIn: 'root' })
export class PredictionsService {
  private readonly api = inject(ApiClient);

  list(query: PredictionQuery = {}): Observable<PredictionResponse> {
    return this.api.get('/predictions', { ...query });
  }
}

@Injectable({ providedIn: 'root' })
export class ModelsService {
  private readonly api = inject(ApiClient);

  report(): Observable<ModelResponse> {
    return this.api.get('/models');
  }
}

@Injectable({ providedIn: 'root' })
export class DataQualityService {
  private readonly api = inject(ApiClient);

  report(): Observable<DataQualityResponse> {
    return this.api.get('/data-quality');
  }
}

@Injectable({ providedIn: 'root' })
export class GeoService {
  private readonly api = inject(ApiClient);

  municipalities(): Observable<GeoResponse> {
    return this.api.get('/geo/municipalities');
  }
}

@Injectable({ providedIn: 'root' })
export class VaccinationAnalyticsService {
  private readonly api = inject(ApiClient);

  analytics(query: VaccinationAnalyticsQuery = {}): Observable<VaccinationAnalyticsResponse> {
    return this.api.get('/analytics', { ...query });
  }

  upload(file: File): Observable<AnalyticsUploadResponse> {
    return this.api.post('/analytics/upload', file, {
      'Content-Type': 'text/csv',
      'X-File-Name': file.name,
    });
  }
}

@Injectable({ providedIn: 'root' })
export class VaccinationAnalyticsSession {
  private readonly tokenState = signal<string | null>(null);
  readonly sourceToken = this.tokenState.asReadonly();

  useSourceToken(token: string | null): void {
    this.tokenState.set(token);
  }
}
