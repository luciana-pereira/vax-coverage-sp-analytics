import { ComponentFixture, TestBed } from '@angular/core/testing';

import { KpiCardComponent } from './kpi-card.component';
import { StatePanelComponent } from './state-panel.component';

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
});
