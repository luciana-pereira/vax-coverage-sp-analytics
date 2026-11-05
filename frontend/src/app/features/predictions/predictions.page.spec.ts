import { of } from 'rxjs';
import { TestBed } from '@angular/core/testing';

import { PredictionsService } from '../../core/services/api.services';
import { PredictionResponse } from '../../core/models/api.models';
import { PredictionsPage } from './predictions.page';

describe('PredictionsPage', () => {
  let api: jasmine.SpyObj<PredictionsService>;

  beforeEach(() => {
    api = jasmine.createSpyObj<PredictionsService>('PredictionsService', ['list']);

    TestBed.configureTestingModule({
      imports: [PredictionsPage],
      providers: [{ provide: PredictionsService, useValue: api }],
    });
  });

  function createResponse(overrides: Partial<PredictionResponse> = {}): PredictionResponse {
    return {
      status: 'ok',
      message: null,
      model_name: 'RandomForest',
      source_year: 2023,
      target_year: 2024,
      total: 2,
      class_distribution: {
        baixo: 1,
        moderado: 1,
      },
      items: [
        {
          municipality_code: '3550308',
          municipality_name: 'São Paulo',
          immunizer: 'BCG',
          source_year: 2023,
          predicted_class: 'baixo',
          probabilities: {
            baixo: 0.8,
            moderado: 0.15,
            alto: 0.05,
          },
        },
      ],
      ...overrides,
    };
  }

  it('shows unavailable state when the model is unavailable', () => {
    api.list.and.returnValue(
      of(
        createResponse({
          status: 'model_unavailable',
          message: 'Modelo ainda não treinado.',
          model_name: null,
          source_year: null,
          target_year: null,
          total: 0,
          class_distribution: {},
          items: [],
        }),
      ),
    );

    const fixture = TestBed.createComponent(PredictionsPage);

    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('Modelo ainda não treinado.');
  });

  it('renders prediction data when the API succeeds', () => {
    api.list.and.returnValue(of(createResponse()));

    const fixture = TestBed.createComponent(PredictionsPage);

    fixture.detectChanges();

    expect(fixture.nativeElement.textContent).toContain('RandomForest');
    expect(fixture.nativeElement.textContent).toContain('2023');
    expect(fixture.nativeElement.textContent).toContain('2024');
    expect(fixture.nativeElement.textContent).toContain('São Paulo');
    expect(api.list).toHaveBeenCalledWith({
      predicted_class: null,
      municipality_code: null,
      limit: 25,
      offset: 0,
    });
  });

  it('updates the query when the class filter changes', () => {
    api.list.and.returnValue(of(createResponse()));

    const fixture = TestBed.createComponent(PredictionsPage);

    fixture.detectChanges();

    const select = fixture.nativeElement.querySelector('#p-class') as HTMLSelectElement;
    select.value = 'alto';
    select.dispatchEvent(new Event('change'));

    fixture.detectChanges();

    expect(api.list).toHaveBeenCalledWith({
      predicted_class: 'alto',
      municipality_code: null,
      limit: 25,
      offset: 0,
    });
  });

  it('moves to the next page', () => {
    api.list.and.returnValue(
      of(
        createResponse({
          total: 50,
        }),
      ),
    );

    const fixture = TestBed.createComponent(PredictionsPage);

    fixture.detectChanges();

    const next = fixture.nativeElement.querySelectorAll('.pager button')[1] as HTMLButtonElement;
    next.click();

    fixture.detectChanges();

    expect(api.list).toHaveBeenCalledWith({
      predicted_class: null,
      municipality_code: null,
      limit: 25,
      offset: 25,
    });
  });
});