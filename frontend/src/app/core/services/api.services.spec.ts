import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { TestBed } from '@angular/core/testing';

import { API_BASE_URL } from '../config/api-config';
import { errorInterceptor } from '../interceptors/error.interceptor';
import { CoverageService, MunicipalitiesService } from './api.services';

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
});
