import { Component, computed, inject, input } from '@angular/core';
import { RouterLink } from '@angular/router';

import { MunicipalitiesService } from '../../core/services/api.services';
import { ChartComponent } from '../../shared/components/chart.component';
import { KpiCardComponent } from '../../shared/components/kpi-card.component';
import { RiskBadgeComponent } from '../../shared/components/risk-badge.component';
import { loadOnChange } from '../../shared/state/load-state';
import { MunicipalityDetailResponse } from '../../core/models/api.models';
import { StatePanelComponent } from '../../shared/components/state-panel.component';
import { lineChart } from '../../shared/utils/charts';
import { formatInteger, formatPercent, formatPoints, municipalityLabel } from '../../shared/utils/format';

@Component({
  selector: 'app-municipality-detail-page',
  standalone: true,
  imports: [ChartComponent, KpiCardComponent, RiskBadgeComponent, RouterLink, StatePanelComponent],
  template: `
    <section class="page" aria-labelledby="det-title">
      <a routerLink="/municipios">← Municípios</a>
      @let d = detail();
      @if (d.status === 'loading') {
        <app-state-panel kind="loading" />
      } @else if (d.status === 'error') {
        <app-state-panel kind="error" [message]="d.message" [retryable]="true" (retry)="detail.retry()" />
      } @else {
        @let m = d.data.municipality;
        <div>
          <h2 id="det-title" class="page__title">{{ label(m.municipality_name, m.municipality_code) }}</h2>
          <p class="page__lead">Risco médio: <app-risk-badge [value]="m.deficit_class" /></p>
        </div>
        <div class="grid grid--kpi">
          <app-kpi-card label="Cobertura média" [value]="pct(m.mean_coverage)" />
          <app-kpi-card label="Déficit médio" [value]="pts(m.mean_deficit)" />
          <app-kpi-card label="Registros" [value]="int(m.records)" />
        </div>
        @if (chart(); as config) {
          <article class="card">
            <h2>Evolução anual</h2>
            <app-chart [config]="config" ariaLabel="Cobertura e déficit do município por ano" />
          </article>
        }
        @if (d.data.by_immunizer.length > 0) {
          <article class="card">
            <h2>Por imunizante</h2>
            <div class="table-wrap">
              <table class="table">
                <thead><tr><th>Imunizante</th><th class="num">Cobertura</th><th class="num">Déficit</th></tr></thead>
                <tbody>
                  @for (i of d.data.by_immunizer; track i.immunizer) {
                    <tr>
                      <td>{{ i.immunizer }}</td>
                      <td class="num">{{ pct(i.mean_coverage) }}</td>
                      <td class="num">{{ pts(i.mean_deficit) }}</td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          </article>
        }
      }
    </section>
  `,
})
export class MunicipalityDetailPage {
  /** Parâmetro de rota `:code` (via withComponentInputBinding). */
  readonly code = input.required<string>();

  private readonly api = inject(MunicipalitiesService);

  protected readonly detail = loadOnChange(this.code, (code) => this.api.detail(code));

  protected readonly pct = formatPercent;
  protected readonly pts = formatPoints;
  protected readonly int = formatInteger;
  protected readonly label = municipalityLabel;

  protected readonly chart = computed(() => {
    const state = this.detail();
    if (state.status !== 'success' || state.data.history.length === 0) return null;
    const points = state.data.history;
    return lineChart(
      points.map((p) => p.year),
      [
        { label: 'Cobertura (%)', data: points.map((p) => p.mean_coverage), color: '#1f4e79' },
        { label: 'Déficit (p.p.)', data: points.map((p) => p.mean_deficit), color: '#c62828' },
      ],
      'Percentual / pontos percentuais',
    );
  });
}
