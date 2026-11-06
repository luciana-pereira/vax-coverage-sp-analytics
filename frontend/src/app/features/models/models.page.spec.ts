import { provideHttpClient } from '@angular/common/http';
import { HttpTestingController, provideHttpClientTesting } from '@angular/common/http/testing';
import { ComponentFixture, TestBed } from '@angular/core/testing';

import { API_BASE_URL } from '../../core/config/api-config';
import { ModelsPage } from './models.page';

const BASE = 'http://api.test/api/v1';

const METRICS = {
  accuracy: 0.8,
  precision_macro: 0.7,
  precision_weighted: 0.8,
  recall_macro: 0.6,
  recall_weighted: 0.8,
  f1_macro: 0.65,
  f1_weighted: 0.79,
  confusion_matrix: [
    [5, 1],
    [2, 4],
  ],
};

describe('ModelsPage', () => {
  let fixture: ComponentFixture<ModelsPage>;
  let http: HttpTestingController;

  const text = (): string => (fixture.nativeElement as HTMLElement).textContent ?? '';

  beforeEach(async () => {
    TestBed.configureTestingModule({
      providers: [provideHttpClient(), provideHttpClientTesting(), { provide: API_BASE_URL, useValue: BASE }],
    });
    http = TestBed.inject(HttpTestingController);
    fixture = TestBed.createComponent(ModelsPage);
    fixture.detectChanges();
  });

  afterEach(() => http.verify());

  it('explains that no model has been trained', async () => {
    http.expectOne(`${BASE}/models`).flush({
      status: 'not_trained',
      message: "Relatório ausente. Execute 'python -m ml.cli train'.",
      models: [],
      features: [],
      classes: [],
      feature_importance: [],
    });
    await fixture.whenStable();
    fixture.detectChanges();
    expect(text()).toContain('Dados indisponíveis');
    expect(text()).toContain('ml.cli train');
  });

  it('shows metrics, confusion matrix and the selected model', async () => {
    http.expectOne(`${BASE}/models`).flush({
      status: 'ok',
      message: null,
      generated_at: '2024-01-01T00:00:00+00:00',
      target: 'deficit_class_next',
      features: ['coverage'],
      classes: ['baixo', 'alto'],
      split: {
        scheme: 'temporal',
        train_years: [2020],
        validation_year: null,
        test_year: 2021,
        n_train: 10,
        n_validation: 0,
        n_test: 12,
      },
      selection: { criterion: 'f1_macro', split: 'test', note: 'Menos de 3 períodos.' },
      best_model: 'random_forest',
      models: [
        { name: 'random_forest', is_best: true, validation: null, test: METRICS },
        { name: 'logistic_regression', is_best: false, validation: null, test: METRICS },
      ],
      baseline: { description: 'persistência', test: METRICS },
      feature_importance: [{ feature: 'num__coverage', importance: 0.9 }],
    });
    await fixture.whenStable();
    fixture.detectChanges();

    expect(text()).toContain('Random Forest');
    expect(text()).toContain('(selecionado)');
    expect(text()).toContain('0,650');
    expect(text()).toContain('Menos de 3 períodos.');
    expect(text()).toContain('Baseline (persistência)');
    expect(text()).toContain('Comparação das métricas no teste');
    expect(
      (fixture.nativeElement as HTMLElement).querySelector(
        'canvas[aria-label="F1, precision, recall e acurácia por modelo no teste"]',
      ),
    ).not.toBeNull();
    const cells = (fixture.nativeElement as HTMLElement).querySelectorAll('table.matrix tbody tr');
    expect(cells.length).toBe(2);
  });
});
