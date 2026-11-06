import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { fakeAsync, TestBed, tick } from '@angular/core/testing';

import { API_BASE_URL } from '../config/api-config';
import { API_REQUEST_TIMEOUT_MS, errorInterceptor } from '../interceptors/error.interceptor';
import {
  CoverageService,
  MunicipalitiesService,
  VaccinationAnalyticsService,
} from './api.services';

describe('API services', () => {
  let http: HttpTestingController;

  beforeEach(() => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([errorInterceptor])),
        provideHttpClientTesting(),
        { provide: API_BASE_URL, useValue: 'http://api.test/api/v1' },
      ],
    });
    http = TestBed.inject(HttpTestingController);
  });

  afterEach(() => http.verify());

  it('builds the coverage query skipping empty filters', () => {
    TestBed.inject(CoverageService)
      .overview({ year: 2023, immunizer: null, deficit_class: 'alto' }, 5)
      .subscribe();

    const req = http.expectOne((r) => r.url === 'http://api.test/api/v1/coverage');
    expect(req.request.params.get('year')).toBe('2023');
    expect(req.request.params.get('deficit_class')).toBe('alto');
    expect(req.request.params.get('ranking_limit')).toBe('5');
    expect(req.request.params.has('immunizer')).toBeFalse();
    req.flush({});
  });

  it('repeats array parameters for municipality comparison', () => {
    TestBed.inject(CoverageService)
      .history({ municipality_code: ['1100', '2200'] })
      .subscribe();

    const req = http.expectOne((r) => r.url === 'http://api.test/api/v1/coverage/history');
    expect(req.request.params.getAll('municipality_code')).toEqual(['1100', '2200']);
    req.flush({});
  });

  it('requests immunizer coverage with the active filters', () => {
    TestBed.inject(CoverageService).byImmunizer({ year: 2024, deficit_class: 'alto' }).subscribe();

    const req = http.expectOne((r) => r.url === 'http://api.test/api/v1/coverage/immunizers');
    expect(req.request.params.get('year')).toBe('2024');
    expect(req.request.params.get('deficit_class')).toBe('alto');
    req.flush({ status: 'ok', message: null, items: [] });
  });

  it('requests filtered aggregated vaccination analytics', () => {
    TestBed.inject(VaccinationAnalyticsService)
      .analytics({ year: 2024, vaccine: 'key-1', age_group: '0-4', municipality_basis: 'patient' })
      .subscribe();

    const req = http.expectOne('http://api.test/api/v1/analytics?year=2024&vaccine=key-1&age_group=0-4&municipality_basis=patient');
    expect(req.request.method).toBe('GET');
    req.flush({});
  });

  it('uploads CSV bytes directly without retaining a FormData payload', () => {
    const file = new File(['dt_vacina,sg_imunobiologico\n2024-01-01,BCG'], 'doses.csv', { type: 'text/csv' });
    TestBed.inject(VaccinationAnalyticsService).upload(file).subscribe();

    const req = http.expectOne('http://api.test/api/v1/analytics/upload');
    expect(req.request.method).toBe('POST');
    expect(req.request.body).toBe(file);
    expect(req.request.headers.get('Content-Type')).toBe('text/csv');
    expect(req.request.headers.get('X-File-Name')).toBe('doses.csv');
    req.flush({});
  });

  it('encodes the municipality code in the detail path', () => {
    TestBed.inject(MunicipalitiesService).detail('a/b').subscribe();
    http.expectOne('http://api.test/api/v1/municipalities/a%2Fb').flush({});
  });

  it('maps HTTP errors to ApiError with the backend detail', (done) => {
    TestBed.inject(MunicipalitiesService).detail('9999').subscribe({
      error: (error: Error) => {
        expect(error.message).toBe('Município 9999 sem registros.');
        done();
      },
    });
    http
      .expectOne('http://api.test/api/v1/municipalities/9999')
      .flush({ detail: 'Município 9999 sem registros.' }, { status: 404, statusText: 'Not Found' });
  });

  it('reports an unreachable API with a clear message', (done) => {
    TestBed.inject(CoverageService).filters().subscribe({
      error: (error: Error) => {
        expect(error.message).toContain('conectar à API');
        done();
      },
    });
    http.expectOne('http://api.test/api/v1/coverage/filters').error(new ProgressEvent('error'));
  });

  it('turns an API timeout into a recoverable network message', fakeAsync(() => {
    let message = '';
    TestBed.inject(CoverageService).filters().subscribe({ error: (error: Error) => (message = error.message) });
    http.expectOne('http://api.test/api/v1/coverage/filters');

    tick(API_REQUEST_TIMEOUT_MS);

    expect(message).toContain('demorou para responder');
  }));
});
