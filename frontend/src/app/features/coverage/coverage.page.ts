import { Component, computed, inject, signal } from '@angular/core';

import { CoverageFilters } from '../../core/models/api.models';
import { CoverageService, MunicipalitiesService } from '../../core/services/api.services';
import { FilterStore } from '../../core/state/filter-store.service';
import { ChartComponent } from '../../shared/components/chart.component';
import { FiltersBarComponent } from '../../shared/components/filters-bar.component';
import { StatePanelComponent } from '../../shared/components/state-panel.component';
import { VaccinationAnalyticsPanelComponent } from '../../shared/components/vaccination-analytics-panel.component';
import { loadOnChange, loadOnce } from '../../shared/state/load-state';
import { barChart, lineChart } from '../../shared/utils/charts';
import { formatPercent, formatPoints, municipalityLabel } from '../../shared/utils/format';

const PALETTE = ['#1f4e79', '#c62828', '#2e7d32', '#6a1b9a', '#ef6c00', '#00838f'];
const MAX_COMPARE = 5;

@Component({
  selector: 'app-coverage-page',
  standalone: true,
  imports: [ChartComponent, FiltersBarComponent, StatePanelComponent, VaccinationAnalyticsPanelComponent],
  template: `
    <section class="page" aria-labelledby="cov-title">
      <div>
        <h2 id="cov-title" class="page__title">Histórico de cobertura</h2>
        <p class="page__lead">
          Evolução anual de cobertura e déficit. Selecione até {{ max }} municípios para comparar.
        </p>
      </div>

      <app-filters-bar />
      <app-vaccination-analytics-panel view="history" />
      <div class="filters" aria-label="Opções da comparação histórica">
        <div class="field">
          <label for="h-metric">Indicador</label>
          <select id="h-metric" (change)="onMetric($event)">
            <option value="coverage" selected>Cobertura média (%)</option>
            <option value="deficit">Déficit médio (p.p.)</option>
          </select>
        </div>
        <div class="field">
          <label for="h-muni">Adicionar município</label>
          <select id="h-muni" (change)="onAdd($event)" [disabled]="options().length === 0">
            <option value="">{{ options().length === 0 ? 'Indisponível' : 'Selecionar…' }}</option>
            @for (o of options(); track o.code) {
              <option [value]="o.code">{{ o.label }}</option>
            }
          </select>
        </div>
      </div>

      @if (selected().length > 0) {
        <ul class="chips" aria-label="Municípios selecionados">
          @for (code of selected(); track code) {
            <li class="chip">
              {{ nameOf(code) }}
              <button type="button" (click)="remove(code)" [attr.aria-label]="'Remover ' + nameOf(code)">×</button>
            </li>
          }
        </ul>
      }

      @let h = history();
      @let config = chart();
      @if (h.status === 'loading') {
        <app-state-panel kind="loading" />
      } @else if (h.status === 'error') {
        <app-state-panel kind="error" [message]="h.message" [retryable]="true" (retry)="history.retry()" />
      } @else if (h.data.status !== 'ok') {
        <app-state-panel kind="unavailable" [message]="h.data.message" />
      } @else if (config) {
        <article class="card">
          <h2>{{ metric() === 'coverage' ? 'Cobertura média por ano' : 'Déficit médio por ano' }}</h2>
          <app-chart [config]="config" ariaLabel="Série histórica por ano" />
        </article>
        <article class="card">
          <h2>Valores por período</h2>
          <div class="table-wrap">
            <table class="table">
              <thead>
                <tr>
                  <th>Série</th><th>Ano</th><th class="num">Cobertura</th><th class="num">Déficit</th>
                  <th class="num">Registros</th>
                </tr>
              </thead>
              <tbody>
                @for (s of h.data.series; track s.key) {
                  @for (p of s.points; track p.year) {
                    <tr>
                      <td>{{ s.key === 'all' ? s.label : nameOf(s.key) }}</td>
                      <td>{{ p.year }}</td>
                      <td class="num">{{ pct(p.mean_coverage) }}</td>
                      <td class="num">{{ pts(p.mean_deficit) }}</td>
                      <td class="num">{{ p.records }}</td>
                    </tr>
                  }
                }
              </tbody>
            </table>
          </div>
        </article>
      } @else {
        <app-state-panel kind="empty" message="Sem série histórica para os filtros." />
      }

      <article class="card">
        <h2>Comparação dos municípios selecionados</h2>
        @if (selected().length < 2) {
          <app-state-panel kind="empty" message="Selecione pelo menos dois municípios para comparar." />
        } @else {
          @if (comparisonChart(); as comparison) {
            <app-chart
              [config]="comparison"
              [ariaLabel]="metric() === 'coverage' ? 'Comparação de cobertura por município no último ano disponível' : 'Comparação de déficit por município no último ano disponível'"
            />
          } @else {
            <app-state-panel kind="empty" message="Não há valores válidos para os municípios selecionados." />
          }
        }
      </article>
    </section>
  `,
})
export class CoveragePage {
  protected readonly store = inject(FilterStore);
  private readonly coverageApi = inject(CoverageService);
  private readonly municipalitiesApi = inject(MunicipalitiesService);

  protected readonly max = MAX_COMPARE;
  protected readonly metric = signal<'coverage' | 'deficit'>('coverage');
  protected readonly selected = signal<string[]>([]);

  private readonly municipalityList = loadOnce(() => this.municipalitiesApi.list({}, 1000, 0));

  private readonly query = computed<CoverageFilters>(() => ({
    ...this.store.filters(),
    municipality_code: this.selected(),
  }));
  protected readonly history = loadOnChange(this.query, (q) => this.coverageApi.history(q));

  protected readonly pct = formatPercent;
  protected readonly pts = formatPoints;

  protected readonly options = computed(() => {
    const state = this.municipalityList();
    if (state.status !== 'success') return [];
    return state.data.items
      .filter((i) => !this.selected().includes(i.municipality_code))
      .map((i) => ({ code: i.municipality_code, label: municipalityLabel(i.municipality_name, i.municipality_code) }));
  });

  protected readonly chart = computed(() => {
    const state = this.history();
    if (state.status !== 'success' || state.data.status !== 'ok') return null;
    const series = state.data.series.filter((s) => s.points.length > 0);
    if (series.length === 0) return null;
    const years = [...new Set(series.flatMap((s) => s.points.map((p) => p.year)))].sort();
    const metric = this.metric();
    return lineChart(
      years,
      series.map((s, index) => ({
        label: s.key === 'all' ? s.label : this.nameOf(s.key),
        color: PALETTE[index % PALETTE.length],
        data: years.map((y) => {
          const point = s.points.find((p) => p.year === y);
          return point ? (metric === 'coverage' ? point.mean_coverage : point.mean_deficit) : null;
        }),
      })),
      metric === 'coverage' ? 'Cobertura (%)' : 'Déficit (p.p.)',
    );
  });

  protected readonly comparisonChart = computed(() => {
    const state = this.history();
    if (
      state.status !== 'success' ||
      state.data.status !== 'ok' ||
      this.selected().length < 2
    ) {
      return null;
    }

    const metric = this.metric() === 'coverage' ? 'mean_coverage' : 'mean_deficit';
    const items = state.data.series.flatMap((series) => {
      const points = series.points
        .filter((point) => point[metric] !== null)
        .sort((left, right) => left.year - right.year);
      const latest = points.at(-1);
      return latest?.[metric] === null || latest === undefined
        ? []
        : [{ label: `${this.nameOf(series.key)} (${latest.year})`, value: latest[metric] as number }];
    });
    if (items.length < 2) return null;

    return barChart(
      items.map((item) => item.label),
      [
        {
          label: metric === 'mean_coverage' ? 'Cobertura (%)' : 'Déficit (p.p.)',
          data: items.map((item) => item.value),
          colors: items.map((_, index) => PALETTE[index % PALETTE.length]),
        },
      ],
      {
        horizontal: true,
        yTitle: metric === 'mean_coverage' ? 'Cobertura (%)' : 'Déficit (p.p.)',
      },
    );
  });

  protected nameOf(code: string): string {
    const state = this.municipalityList();
    if (state.status !== 'success') return code;
    const found = state.data.items.find((i) => i.municipality_code === code);
    return found ? municipalityLabel(found.municipality_name, code) : code;
  }

  protected onMetric(event: Event): void {
    this.metric.set((event.target as HTMLSelectElement).value as 'coverage' | 'deficit');
  }

  protected onAdd(event: Event): void {
    const select = event.target as HTMLSelectElement;
    const code = select.value;
    select.value = '';
    if (code && this.selected().length < MAX_COMPARE) this.selected.update((c) => [...c, code]);
  }

  protected remove(code: string): void {
    this.selected.update((codes) => codes.filter((c) => c !== code));
  }
}
