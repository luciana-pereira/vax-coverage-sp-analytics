import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';

import { DataQualityService } from '../../core/services/api.services';
import { DataQualityResponse } from '../../core/models/api.models';
import { DataQualityPage } from './data-quality.page';

describe('DataQualityPage', () => {
  let api: jasmine.SpyObj<DataQualityService>;

  beforeEach(() => {
    api = jasmine.createSpyObj<DataQualityService>('DataQualityService', ['report']);

    TestBed.configureTestingModule({
      imports: [DataQualityPage],
      providers: [{ provide: DataQualityService, useValue: api }],
    });
  });

  function createResponse(
    overrides: Partial<DataQualityResponse> = {},
  ): DataQualityResponse {
    return {
      status: 'ok',
      artifacts: [
        {
          name: 'features',
          description: 'Features Parquet',
          path: 'data/gold/features.parquet',
          exists: true,
          size_bytes: 1024,
        },
        {
          name: 'model',
          description: 'Modelo treinado',
          path: 'ml/models/model.joblib',
          exists: false,
          size_bytes: null,
        },
      ],
      dataset: {
        rows: 100,
        municipalities: 20,
        year_min: 2020,
        year_max: 2024,
        duplicate_rows: 0,
        missing_columns: [],
        records_by_year: [
          { year: 2020, records: 20 },
          { year: 2024, records: 80 },
        ],
        columns: [
          {
            name: 'coverage',
            null_count: 2,
            null_ratio: 0.02,
          },
        ],
      },
      known_gaps: [],
      ...overrides,
    };
  }

  it('shows unavailable state when the dataset is not generated', () => {
    api.report.and.returnValue(
      of(
        createResponse({
          dataset: null,
        }),
      ),
    );

    const fixture = TestBed.createComponent(DataQualityPage);

    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain(
      'Dataset de features ainda não gerado.',
    );
  });

  it('renders dataset quality information', () => {
    api.report.and.returnValue(of(createResponse()));

    const fixture = TestBed.createComponent(DataQualityPage);

    fixture.detectChanges();

    const text = fixture.nativeElement.textContent;

    expect(text).toContain('100');
    expect(text).toContain('20');
    expect(text).toContain('2020');
    expect(text).toContain('2024');
    expect(text).toContain('coverage');
    expect(text).toContain('Features Parquet');
    expect(text).toContain('Modelo treinado');
    expect(
      (fixture.nativeElement as HTMLElement).querySelector(
        'canvas[aria-label="Proporção de valores nulos por coluna"]',
      ),
    ).not.toBeNull();
    expect(
      (fixture.nativeElement as HTMLElement).querySelector(
        'canvas[aria-label="Quantidade de registros por ano"]',
      ),
    ).not.toBeNull();
  });

  it('highlights duplicated rows as an alert', () => {
    api.report.and.returnValue(
      of(
        createResponse({
          dataset: {
            ...createResponse().dataset!,
            duplicate_rows: 5,
          },
        }),
      ),
    );

    const fixture = TestBed.createComponent(DataQualityPage);

    fixture.detectChanges();

    const text = fixture.nativeElement.textContent;
    expect(text).toContain('5');

    const alert = fixture.nativeElement.querySelector('.badge--missing, .tone--alert');
    expect(alert).toBeTruthy();
  });

  it('shows missing columns as unavailable', () => {
    api.report.and.returnValue(
      of(
        createResponse({
          dataset: {
            ...createResponse().dataset!,
            missing_columns: ['coverage', 'deficit_class'],
          },
        }),
      ),
    );

    const fixture = TestBed.createComponent(DataQualityPage);

    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain(
      'Colunas ausentes: coverage, deficit_class',
    );
  });

  it('shows artifact presence status', () => {
    api.report.and.returnValue(of(createResponse()));

    const fixture = TestBed.createComponent(DataQualityPage);

    fixture.detectChanges();

    const text = fixture.nativeElement.textContent;

    expect(text).toContain('Presente');
    expect(text).toContain('Ausente');
  });
});