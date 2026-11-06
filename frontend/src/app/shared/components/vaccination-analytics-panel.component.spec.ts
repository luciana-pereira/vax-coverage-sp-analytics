import { TestBed } from '@angular/core/testing';
import { of, Subject } from 'rxjs';

import { AnalyticsUploadResponse, VaccinationAnalyticsResponse } from '../../core/models/api.models';
import { VaccinationAnalyticsService } from '../../core/services/api.services';
import { VaccinationAnalyticsPanelComponent } from './vaccination-analytics-panel.component';

describe('VaccinationAnalyticsPanelComponent', () => {
  const response: VaccinationAnalyticsResponse = {
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
      vaccines: [
        { key: '[null,"BCG",null]', code: null, abbreviation: 'BCG', description: null, label: 'BCG' },
      ],
      age_groups: [],
      patient_municipalities: [{ code: '350010', name: 'Adamantina' }],
      application_municipalities: [],
    },
    monthly: [{ month: '2024-01', doses: 245 }],
    by_sex: [],
    by_age_group: [],
    by_vaccine: [
      { key: '[null,"BCG",null]', code: null, abbreviation: 'BCG', description: null, label: 'BCG', doses: 245 },
    ],
    by_patient_municipality: [{ code: '350010', name: 'Adamantina', doses: 245 }],
    by_application_municipality: [],
    warnings: [],
  };

  it('renders the API aggregate and states absent dimensions instead of inventing charts', async () => {
    const api = jasmine.createSpyObj<VaccinationAnalyticsService>(
      'VaccinationAnalyticsService',
      ['analytics', 'upload'],
    );
    api.analytics.and.returnValue(of(response));
    api.upload.and.returnValue(of({ ...response, accepted_rows: 0, source_token: null }));
    TestBed.configureTestingModule({
      imports: [VaccinationAnalyticsPanelComponent],
      providers: [{ provide: VaccinationAnalyticsService, useValue: api }],
    });

    const fixture = TestBed.createComponent(VaccinationAnalyticsPanelComponent);
    fixture.componentRef.setInput('view', 'overview');
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();

    const element = fixture.nativeElement as HTMLElement;
    expect(element.textContent).toContain('PNI JSONL local');
    expect(element.textContent).toContain('245 doses');
    expect(element.textContent).toContain('A fonte selecionada não contém sexo do paciente.');
    expect(element.textContent).toContain('A fonte selecionada não contém idade ou data de nascimento.');
    expect(element.querySelector('canvas[aria-label="Doses de vacinação por mês, dados agregados da fonte selecionada"]')).not.toBeNull();
    expect(api.analytics).toHaveBeenCalled();
    fixture.destroy();
  });

  it('uses the temporary aggregate token after a CSV upload without retaining the file', async () => {
    const api = jasmine.createSpyObj<VaccinationAnalyticsService>(
      'VaccinationAnalyticsService',
      ['analytics', 'upload'],
    );
    api.analytics.and.returnValue(of(response));
    api.upload.and.returnValue(
      of({ ...response, source: 'CSV carregado (agregado em memória)', accepted_rows: 1, source_token: 'opaque-token' }),
    );
    TestBed.configureTestingModule({
      imports: [VaccinationAnalyticsPanelComponent],
      providers: [{ provide: VaccinationAnalyticsService, useValue: api }],
    });

    const fixture = TestBed.createComponent(VaccinationAnalyticsPanelComponent);
    fixture.componentRef.setInput('view', 'overview');
    fixture.detectChanges();
    await fixture.whenStable();
    const input = (fixture.nativeElement as HTMLElement).querySelector('input[type="file"]')!;
    const file = new File(['dt_vacina,sg_imunobiologico\n2024-01-01,BCG'], 'doses.csv', {
      type: 'text/csv',
    });
    Object.defineProperty(input, 'files', { configurable: true, value: [file] });
    input.dispatchEvent(new Event('change'));
    await fixture.whenStable();
    fixture.detectChanges();

    expect(api.upload).toHaveBeenCalledWith(file);
    expect(api.analytics).toHaveBeenCalledWith(jasmine.objectContaining({ source_token: 'opaque-token' }));
    expect((fixture.nativeElement as HTMLElement).textContent).toContain('1 linhas agregadas');
    fixture.destroy();
  });

  it('provides an accessible CSV control and preserves upload progress and errors', async () => {
    const api = jasmine.createSpyObj<VaccinationAnalyticsService>(
      'VaccinationAnalyticsService',
      ['analytics', 'upload'],
    );
    const upload = new Subject<AnalyticsUploadResponse>();
    api.analytics.and.returnValue(of(response));
    api.upload.and.returnValue(upload.asObservable());
    TestBed.configureTestingModule({
      imports: [VaccinationAnalyticsPanelComponent],
      providers: [{ provide: VaccinationAnalyticsService, useValue: api }],
    });

    const fixture = TestBed.createComponent(VaccinationAnalyticsPanelComponent);
    fixture.componentRef.setInput('view', 'overview');
    fixture.detectChanges();
    await fixture.whenStable();
    const element = fixture.nativeElement as HTMLElement;
    const input = element.querySelector<HTMLInputElement>('#analytics-csv')!;
    expect(element.querySelector('#analytics-upload-title')?.textContent).toContain('Carregamento de arquivo via CSV para Análise');
    expect(input.labels?.[0].textContent).toContain('Escolher arquivo CSV');
    expect(input.getAttribute('aria-describedby')).toBe('analytics-upload-description');

    Object.defineProperty(input, 'files', { configurable: true, value: [new File(['test'], 'doses.csv')] });
    input.dispatchEvent(new Event('change'));
    fixture.detectChanges();
    expect(input.disabled).toBeTrue();
    expect(element.querySelector('[role="status"]')?.textContent).toContain('Validando e agregando');
    upload.error(new Error('CSV inválido'));
    fixture.detectChanges();
    expect(input.disabled).toBeFalse();
    expect(element.querySelector('[role="alert"]')?.textContent).toContain('CSV inválido');
    fixture.destroy();
  });

  it('places the missing PostgreSQL driver in accessible details without hiding other warnings', async () => {
    const api = jasmine.createSpyObj<VaccinationAnalyticsService>(
      'VaccinationAnalyticsService',
      ['analytics', 'upload'],
    );
    api.analytics.and.returnValue(of({
      ...response,
      warnings: ['Driver PostgreSQL não instalado.', 'Outro aviso importante.'],
    }));
    TestBed.configureTestingModule({
      imports: [VaccinationAnalyticsPanelComponent],
      providers: [{ provide: VaccinationAnalyticsService, useValue: api }],
    });

    const fixture = TestBed.createComponent(VaccinationAnalyticsPanelComponent);
    fixture.componentRef.setInput('view', 'overview');
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const element = fixture.nativeElement as HTMLElement;
    const details = element.querySelector<HTMLDetailsElement>('.analytics-panel__database-status')!;
    expect(details.open).toBeFalse();
    expect(details.querySelector('summary')?.textContent).toContain('usando fonte local');
    expect(details.querySelector('p')?.textContent).toContain('Driver PostgreSQL não instalado.');
    expect(element.querySelector('.analytics-panel__warning')?.textContent).toContain('Outro aviso importante.');
    fixture.destroy();
  });
});
