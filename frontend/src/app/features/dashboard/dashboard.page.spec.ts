import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { API_BASE_URL } from '../../core/config/api-config';
import { DashboardPage } from './dashboard.page';

const BASE = 'http://api.test/api/v1';
const analyticsResponse = {
  status: 'ok',
  message: null,
  source: 'PNI JSONL local',
  source_updated_at: '2024-12-31T12:00:00Z',
  generated_at: '2025-01-01T12:00:00Z',
  year: 2024,
  period_start: '2024-01',
  period_end: '2024-01',
  total_doses: 245,
  statewide: false,
  dimensions: {
    sex: false,
    age: false,
    vaccine_code: false,
    vaccine_abbreviation: true,
    vaccine_description: false,
    patient_municipality: true,
    application_municipality: false,
    municipality_comparison: false,
  },
  filters: {
    years: [2024],
    vaccines: [{ key: '[null,"BCG",null]', code: null, abbreviation: 'BCG', description: null, label: 'BCG' }],
    age_groups: [],
    patient_municipalities: [{ code: '350010', name: 'Adamantina' }],
    application_municipalities: [],
  },
  monthly: [{ month: '2024-01', doses: 245 }],
  by_sex: [],
  by_age_group: [],
  by_vaccine: [{ key: '[null,"BCG",null]', code: null, abbreviation: 'BCG', description: null, label: 'BCG', doses: 245 }],
  by_patient_municipality: [{ code: '350010', name: 'Adamantina', doses: 245 }],
  by_application_municipality: [],
  warnings: [],
};

describe('DashboardPage', () => {
  let fixture: ComponentFixture<DashboardPage>;
  let http: HttpTestingController;

  const text = (): string => (fixture.nativeElement as HTMLElement).textContent ?? '';

  async function settle(): Promise<void> {
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
  }

  const answer = (path: string, body: object): void => {
    for (const req of http.match((r) => r.url === `${BASE}${path}`)) req.flush(body);
  };

  beforeEach(async () => {
    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: API_BASE_URL, useValue: BASE },
      ],
    });
    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(DashboardPage);
    await settle();
  });

  afterEach(() => http.verify());

  it('shows the unavailable state when the API has no dataset', async () => {
    answer('/coverage', {
      status: 'data_unavailable',
      message: 'Dataset de features ausente.',
      summary: null,
      deficit_distribution: [],
      top_deficit_municipalities: [],
    });
    answer('/analytics', analyticsResponse);
    answer('/coverage/filters', { status: 'data_unavailable', years: [], immunizers: [], deficit_classes: [] });
    answer('/coverage/immunizers', { status: 'data_unavailable', message: 'sem imunizantes', items: [] });
    answer('/coverage/history', { status: 'data_unavailable', series: [] });
    answer('/municipalities', { status: 'data_unavailable', total: 0, limit: 1000, offset: 0, items: [] });
    answer('/geo/municipalities', { status: 'data_unavailable', message: 'sem geojson', geojson: null });
    answer('/predictions', { status: 'model_unavailable', message: 'Modelo não treinado.', total: 0, items: [], class_distribution: {} });
    await settle();

    expect(text()).toContain('Dados indisponíveis');
    expect(text()).toContain('Dataset de features ausente.');
    expect(text()).toContain('Modelo não treinado.');
  });

  it('renders KPIs and ranking from the API response', async () => {
    answer('/coverage', {
      status: 'ok',
      message: null,
      summary: {
        records: 5,
        municipalities: 3,
        mean_coverage: 79.2,
        mean_deficit: 16,
        municipalities_below_target: 3,
        critical_municipalities: 2,
      },
      deficit_distribution: [
        { deficit_class: 'baixo', count: 2 },
        { deficit_class: 'alto', count: 2 },
      ],
      top_deficit_municipalities: [
        { municipality_code: '3300', municipality_name: 'Gamma', mean_coverage: 60, mean_deficit: 35 },
      ],
    });
    answer('/analytics', analyticsResponse);
    answer('/coverage/filters', { status: 'ok', years: [2022, 2023], immunizers: [], deficit_classes: ['baixo', 'alto'] });
    answer('/coverage/immunizers', {
      status: 'ok',
      message: null,
      items: [{ immunizer: 'BCG', mean_coverage: 80, mean_deficit: 15 }],
    });
    answer('/coverage/history', {
      status: 'ok',
      series: [{ key: 'all', label: 'Todos', points: [{ year: 2022, mean_coverage: 80, mean_deficit: 15, records: 2 }] }],
    });
    answer('/municipalities', { status: 'ok', total: 0, limit: 1000, offset: 0, items: [] });
    answer('/geo/municipalities', { status: 'data_unavailable', message: 'sem geojson', geojson: null });
    answer('/predictions', { status: 'ok', total: 0, items: [], class_distribution: {}, message: null });
    await settle();

    expect(text()).toContain('79,2%');
    expect(text()).toContain('16,0 p.p.');
    expect(text()).toContain('Gamma (3300)');
    expect(text()).toContain('Situação crítica');
    expect(text()).toContain('Cobertura média por imunizante');
    expect(text()).toContain('PNI JSONL local');
    expect(
      fixture.nativeElement.querySelector(
        'canvas[aria-label="Doses de vacinação por mês, dados agregados da fonte selecionada"]',
      ),
    ).not.toBeNull();
    expect(fixture.nativeElement.querySelector('canvas[aria-label="Cobertura média por imunizante, em percentual"]'))
      .not.toBeNull();
  });

  it('shows an error panel when the request fails', async () => {
    for (const req of http.match((r) => r.url === `${BASE}/coverage`)) {
      req.flush({ detail: 'erro interno' }, { status: 500, statusText: 'Server Error' });
    }
    answer('/coverage/filters', { status: 'ok', years: [], immunizers: [], deficit_classes: [] });
    answer('/analytics', analyticsResponse);
    answer('/coverage/immunizers', { status: 'data_unavailable', message: 'sem imunizantes', items: [] });
    answer('/coverage/history', { status: 'ok', series: [] });
    answer('/municipalities', { status: 'ok', total: 0, limit: 1000, offset: 0, items: [] });
    answer('/geo/municipalities', { status: 'data_unavailable', message: null, geojson: null });
    answer('/predictions', { status: 'ok', total: 0, items: [], class_distribution: {}, message: null });
    await settle();

    expect(text()).toContain('Não foi possível carregar os dados');
  });
});
