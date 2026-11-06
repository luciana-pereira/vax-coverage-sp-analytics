import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

import {
  CoverageFilterOptions,
  CoverageHistoryResponse,
  MunicipalityListResponse,
  VaccinationAnalyticsResponse,
} from '../../core/models/api.models';
import {
  CoverageService,
  MunicipalitiesService,
  VaccinationAnalyticsService,
} from '../../core/services/api.services';
import { FilterStore } from '../../core/state/filter-store.service';
import { CoveragePage } from './coverage.page';

describe('CoveragePage', () => {
  let coverageApi: jasmine.SpyObj<CoverageService>;
  let municipalitiesApi: jasmine.SpyObj<MunicipalitiesService>;
  let analyticsApi: jasmine.SpyObj<VaccinationAnalyticsService>;

  const analyticsResponse: VaccinationAnalyticsResponse = {
    status: 'ok', message: null, source: 'PNI JSONL local', source_updated_at: null,
    generated_at: '2025-01-01T00:00:00Z', year: 2024, period_start: '2024-01', period_end: '2024-01', total_doses: 1, statewide: false,
    dimensions: {},
    filters: { years: [2024], vaccines: [], age_groups: [], patient_municipalities: [], application_municipalities: [] },
    monthly: [{ month: '2024-01', doses: 1 }], by_sex: [], by_age_group: [], by_vaccine: [],
    by_patient_municipality: [], by_application_municipality: [], warnings: [],
  };

  const filters: CoverageFilterOptions = {
    status: 'ok',
    message: null,
    years: [2022, 2023],
    immunizers: ['BCG', 'Hepatite B'],
    deficit_classes: ['baixo', 'moderado', 'alto'],
  };

  const municipalities: MunicipalityListResponse = {
    status: 'ok',
    message: null,
    total: 2,
    limit: 1000,
    offset: 0,
    items: [
      {
        municipality_code: '3550308',
        municipality_name: 'São Paulo',
        mean_coverage: 80,
        mean_deficit: 20,
        deficit_class: 'moderado',
        records: 10,
      },
      {
        municipality_code: '3509502',
        municipality_name: 'Campinas',
        mean_coverage: 90,
        mean_deficit: 10,
        deficit_class: 'baixo',
        records: 10,
      },
      {
        municipality_code: '3500100',
        municipality_name: 'Adamantina',
        mean_coverage: 88,
        mean_deficit: 12,
        deficit_class: 'baixo',
        records: 10,
    },
    {
    municipality_code: '3500209',
    municipality_name: 'Adolfo',
    mean_coverage: 87,
    mean_deficit: 13,
    deficit_class: 'baixo',
    records: 10,
    },
    {
    municipality_code: '3500308',
    municipality_name: 'Aguaí',
    mean_coverage: 86,
    mean_deficit: 14,
    deficit_class: 'moderado',
    records: 10,
    },
    {
    municipality_code: '3500407',
    municipality_name: 'Águas da Prata',
    mean_coverage: 85,
    mean_deficit: 15,
    deficit_class: 'moderado',
    records: 10,
    },
    ],
  };

  function createHistory(
    overrides: Partial<CoverageHistoryResponse> = {},
  ): CoverageHistoryResponse {
    return {
      status: 'ok',
      message: null,
      series: [
        {
          key: 'all',
          label: 'Todos os municípios',
          points: [
            {
              year: 2022,
              mean_coverage: 80,
              mean_deficit: 20,
              records: 10,
            },
            {
              year: 2023,
              mean_coverage: 85,
              mean_deficit: 15,
              records: 10,
            },
          ],
        },
      ],
      ...overrides,
    };
  }

  beforeEach(() => {
    coverageApi = jasmine.createSpyObj<CoverageService>(
      'CoverageService',
      ['filters', 'history'],
    );

    municipalitiesApi = jasmine.createSpyObj<MunicipalitiesService>(
      'MunicipalitiesService',
      ['list'],
    );
    analyticsApi = jasmine.createSpyObj<VaccinationAnalyticsService>(
      'VaccinationAnalyticsService',
      ['analytics', 'upload'],
    );

    coverageApi.filters.and.returnValue(of(filters));
    coverageApi.history.and.returnValue(of(createHistory()));
    municipalitiesApi.list.and.returnValue(of(municipalities));
    analyticsApi.analytics.and.returnValue(of(analyticsResponse));

    TestBed.configureTestingModule({
      imports: [CoveragePage],
      providers: [
        { provide: CoverageService, useValue: coverageApi },
        { provide: MunicipalitiesService, useValue: municipalitiesApi },
        { provide: VaccinationAnalyticsService, useValue: analyticsApi },
      ],
    });
  });

  it('renders the historical coverage data', () => {
    const fixture = TestBed.createComponent(CoveragePage);
    fixture.detectChanges();

    const text = fixture.nativeElement.textContent;

    expect(text).toContain('Todos os municípios');
    expect(text).toContain('2022');
    expect(text).toContain('2023');
    expect(text).toContain('80');
    expect(text).toContain('85');

    expect(coverageApi.history).toHaveBeenCalledWith({
      year: null,
      immunizer: null,
      deficit_class: null,
      municipality_code: [],
    });
  });

  it('changes the chart metric from coverage to deficit', () => {
    const fixture = TestBed.createComponent(CoveragePage);
    fixture.detectChanges();

    const select = fixture.nativeElement.querySelector(
      '#h-metric',
    ) as HTMLSelectElement;

    select.value = 'deficit';
    select.dispatchEvent(new Event('change'));
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain(
      'Déficit médio por ano',
    );
  });

  it('compares selected municipalities in bars using their latest available year', () => {
    coverageApi.history.and.returnValue(
      of(
        createHistory({
          series: [
            {
              key: '3550308',
              label: '3550308',
              points: [
                { year: 2022, mean_coverage: 75, mean_deficit: 20, records: 2 },
                { year: 2023, mean_coverage: 80, mean_deficit: 15, records: 2 },
              ],
            },
            {
              key: '3509502',
              label: '3509502',
              points: [{ year: 2022, mean_coverage: 90, mean_deficit: 5, records: 1 }],
            },
          ],
        }),
      ),
    );

    const fixture = TestBed.createComponent(CoveragePage);
    fixture.detectChanges();
    const select = fixture.nativeElement.querySelector('#h-muni') as HTMLSelectElement;

    for (const code of ['3550308', '3509502']) {
      select.value = code;
      select.dispatchEvent(new Event('change'));
      fixture.detectChanges();
    }

    expect(fixture.nativeElement.textContent).toContain(
      'Comparação dos municípios selecionados',
    );
    expect(
      fixture.nativeElement.querySelector(
        'canvas[aria-label="Comparação de cobertura por município no último ano disponível"]',
      ),
    ).not.toBeNull();
  });

    it('adds municipalities and does not exceed the maximum of five', () => {
        const fixture = TestBed.createComponent(CoveragePage);
        fixture.detectChanges();

        const select = fixture.nativeElement.querySelector(
            '#h-muni',
        ) as HTMLSelectElement;

        const codes = [
            '3550308',
            '3509502',
            '3500100',
            '3500209',
            '3500308',
            '3500407',
        ];

        for (const code of codes) {
            select.value = code;
            select.dispatchEvent(new Event('change'));
            fixture.detectChanges();
        }

        const chips = fixture.nativeElement.querySelectorAll('.chip');

        expect(chips.length).toBe(5);
    });

  it('removes a selected municipality', () => {
    const fixture = TestBed.createComponent(CoveragePage);
    fixture.detectChanges();

    const select = fixture.nativeElement.querySelector(
      '#h-muni',
    ) as HTMLSelectElement;

    select.value = '3550308';
    select.dispatchEvent(new Event('change'));
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('São Paulo');

    const removeButton = fixture.nativeElement.querySelector(
      '.chip button',
    ) as HTMLButtonElement;

    removeButton.click();
    fixture.detectChanges();

    expect(fixture.nativeElement.querySelector('.chip')).toBeNull();
  });

  it('shows unavailable state when historical data is unavailable', () => {
    coverageApi.history.and.returnValue(
      of(
        createHistory({
          status: 'data_unavailable',
          message: 'Dados históricos indisponíveis.',
          series: [],
        }),
      ),
    );

    const fixture = TestBed.createComponent(CoveragePage);
    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain(
      'Dados históricos indisponíveis.',
    );
  });
});