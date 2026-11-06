import { Component, computed, inject, signal, untracked, effect } from '@angular/core';

import { PredictionsService } from '../../core/services/api.services';
import { ChartComponent } from '../../shared/components/chart.component';
import { KpiCardComponent } from '../../shared/components/kpi-card.component';
import { RiskBadgeComponent } from '../../shared/components/risk-badge.component';
import { StatePanelComponent } from '../../shared/components/state-panel.component';
import { loadOnChange } from '../../shared/state/load-state';
import { barChart } from '../../shared/utils/charts';
import {
  RISK_COLORS,
  RISK_LABELS,
  RISK_ORDER,
  formatInteger,
  formatPercent,
  municipalityLabel,
} from '../../shared/utils/format';

const PAGE_SIZE = 25;

@Component({
  selector: 'app-predictions-page',
  standalone: true,
  imports: [ChartComponent, KpiCardComponent, RiskBadgeComponent, StatePanelComponent],
  template: `
    <section class="page" aria-labelledby="pred-title">
      <div>
        <h2 id="pred-title" class="page__title">Previsões</h2>
        <p class="page__lead">
          Classe de déficit prevista para o ano seguinte, calculada pelo modelo treinado.
        </p>
      </div>

      <form class="filters" (submit)="$event.preventDefault()" aria-label="Filtros das previsões">
        <div class="field">
          <label for="p-class">Classe prevista</label>
          <select id="p-class" (change)="onClass($event)">
            <option value="">Todas</option>
            @for (c of classes; track c) {
              <option [value]="c">{{ labels[c] }}</option>
            }
          </select>
        </div>
        <div class="field">
          <label for="p-code">Código do município</label>
          <input id="p-code" type="text" inputmode="numeric" (change)="onCode($event)" />
        </div>
      </form>

      @let p = predictions();
      @if (p.status === 'loading') {
        <app-state-panel kind="loading" />
      } @else if (p.status === 'error') {
        <app-state-panel kind="error" [message]="p.message" [retryable]="true" (retry)="predictions.retry()" />
      } @else if (p.data.status !== 'ok') {
        <app-state-panel kind="unavailable" [message]="p.data.message" />
      } @else if (p.data.total === 0) {
        <app-state-panel kind="empty" [message]="p.data.message ?? 'Nenhuma previsão para os filtros.'" />
      } @else {
        <div class="grid grid--kpi">
          <app-kpi-card label="Modelo utilizado" [value]="p.data.model_name ?? '—'" />
          <app-kpi-card label="Ano de origem" [value]="'' + p.data.source_year" />
          <app-kpi-card label="Ano previsto" [value]="'' + p.data.target_year" />
          <app-kpi-card label="Combinações" [value]="int(p.data.total)" hint="município x imunizante" />
        </div>

        @if (chart(); as config) {
          <article class="card">
            <h2>Distribuição das classes previstas</h2>
            <app-chart [config]="config" ariaLabel="Quantidade de previsões por classe" />
          </article>
        }

        <article class="card">
          <h2>Previsões por município</h2>
          <div class="table-wrap">
            <table class="table">
              <thead>
                <tr>
                  <th>Município</th><th>Imunizante</th><th>Classe prevista</th>
                  <th class="num">Probabilidade da classe</th>
                </tr>
              </thead>
              <tbody>
                @for (i of p.data.items; track i.municipality_code + '|' + i.immunizer) {
                  <tr>
                    <td>{{ label(i.municipality_name, i.municipality_code) }}</td>
                    <td>{{ i.immunizer ?? '—' }}</td>
                    <td><app-risk-badge [value]="i.predicted_class" /></td>
                    <td class="num">
                      {{ i.probabilities ? pct(i.probabilities[i.predicted_class] * 100) : '—' }}
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
          <div class="pager">
            <span>Página {{ page() + 1 }} de {{ pages(p.data.total) }}</span>
            <button type="button" class="btn" [disabled]="page() === 0" (click)="go(-1)">Anterior</button>
            <button type="button" class="btn" [disabled]="page() + 1 >= pages(p.data.total)" (click)="go(1)">
              Próxima
            </button>
          </div>
        </article>
      }
    </section>
  `,
})
export class PredictionsPage {
  private readonly api = inject(PredictionsService);

  protected readonly classes = RISK_ORDER;
  protected readonly labels = RISK_LABELS;
  protected readonly label = municipalityLabel;
  protected readonly pct = formatPercent;
  protected readonly int = formatInteger;

  protected readonly page = signal(0);
  private readonly predictedClass = signal<string | null>(null);
  private readonly code = signal<string | null>(null);

  private readonly query = computed(() => ({
    predicted_class: this.predictedClass(),
    municipality_code: this.code(),
    limit: PAGE_SIZE,
    offset: this.page() * PAGE_SIZE,
  }));
  protected readonly predictions = loadOnChange(this.query, (q) => this.api.list(q));

  constructor() {
    effect(() => {
      this.predictedClass();
      this.code();
      untracked(() => this.page.set(0));
    });
  }

  protected readonly chart = computed(() => {
    const state = this.predictions();
    if (state.status !== 'success' || state.data.status !== 'ok') return null;
    const distribution = state.data.class_distribution;
    const keys = RISK_ORDER.filter((k) => k in distribution);
    if (keys.length === 0) return null;
    return barChart(
      keys.map((k) => RISK_LABELS[k]),
      [{ label: 'Combinações', data: keys.map((k) => distribution[k]), colors: keys.map((k) => RISK_COLORS[k]) }],
    );
  });

  protected pages(total: number): number {
    return Math.max(1, Math.ceil(total / PAGE_SIZE));
  }

  protected go(step: number): void {
    this.page.update((p) => Math.max(0, p + step));
  }

  protected onClass(event: Event): void {
    this.predictedClass.set((event.target as HTMLSelectElement).value || null);
  }

  protected onCode(event: Event): void {
    this.code.set((event.target as HTMLInputElement).value.trim() || null);
  }
}
