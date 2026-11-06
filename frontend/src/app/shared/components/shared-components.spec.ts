import { ComponentFixture, TestBed } from '@angular/core/testing';
import { ChartConfiguration } from 'chart.js';

import { ChartComponent } from './chart.component';
import { KpiCardComponent } from './kpi-card.component';
import { StatePanelComponent } from './state-panel.component';

describe('ChartComponent', () => {
  it('renders an accessible table alternative from chart values', () => {
    const fixture = TestBed.createComponent(ChartComponent);
    const config: ChartConfiguration = {
      type: 'line',
      data: {
        labels: ['2023', '2024'],
        datasets: [{ label: 'Cobertura (%)', data: [82.5, null] }],
      },
    };
    fixture.componentRef.setInput('config', config);
    fixture.componentRef.setInput('ariaLabel', 'Cobertura por ano');
    fixture.detectChanges();

    const element = fixture.nativeElement as HTMLElement;
    expect(element.querySelector('canvas')?.getAttribute('aria-label')).toBe('Cobertura por ano');
    expect(element.querySelector('caption')?.textContent?.trim()).toBe('Cobertura por ano');
    expect(element.querySelector('tbody')?.textContent).toContain('82,5');
    expect(element.querySelector('tbody')?.textContent).toContain('Sem dados');

    fixture.destroy();
  });
});

describe('KpiCardComponent', () => {
  it('renders label, value and hint', () => {
    const fixture = TestBed.createComponent(KpiCardComponent);
    fixture.componentRef.setInput('label', 'Cobertura média');
    fixture.componentRef.setInput('value', '79,2%');
    fixture.componentRef.setInput('hint', 'todos os anos');
    fixture.detectChanges();

    const text = (fixture.nativeElement as HTMLElement).textContent ?? '';
    expect(text).toContain('Cobertura média');
    expect(text).toContain('79,2%');
    expect(text).toContain('todos os anos');
  });

  it('marks alert tone', () => {
    const fixture = TestBed.createComponent(KpiCardComponent);
    fixture.componentRef.setInput('label', 'Crítico');
    fixture.componentRef.setInput('value', '2');
    fixture.componentRef.setInput('tone', 'alert');
    fixture.detectChanges();
    expect((fixture.nativeElement as HTMLElement).querySelector('.kpi--alert')).not.toBeNull();
  });
});

describe('StatePanelComponent', () => {
  let fixture: ComponentFixture<StatePanelComponent>;

  beforeEach(() => {
    fixture = TestBed.createComponent(StatePanelComponent);
  });

  it('announces errors with role=alert', () => {
    fixture.componentRef.setInput('kind', 'error');
    fixture.componentRef.setInput('message', 'Falha de rede');
    fixture.detectChanges();

    const panel = (fixture.nativeElement as HTMLElement).querySelector('.state-panel')!;
    expect(panel.getAttribute('role')).toBe('alert');
    expect(panel.textContent).toContain('Falha de rede');
  });

  it('uses status role for empty and loading states', () => {
    fixture.componentRef.setInput('kind', 'empty');
    fixture.detectChanges();
    const panel = (fixture.nativeElement as HTMLElement).querySelector('.state-panel')!;
    expect(panel.getAttribute('role')).toBe('status');
    expect(panel.textContent).toContain('Sem resultados');
  });

  it('emits a retry action when enabled on an error state', () => {
    fixture.componentRef.setInput('kind', 'error');
    fixture.componentRef.setInput('retryable', true);
    let retried = false;
    fixture.componentInstance.retry.subscribe(() => (retried = true));
    fixture.detectChanges();

    (fixture.nativeElement as HTMLElement).querySelector('button')!.click();

    expect(retried).toBeTrue();
  });
});
