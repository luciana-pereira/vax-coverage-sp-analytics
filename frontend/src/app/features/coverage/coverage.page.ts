import { Component, computed, inject, signal } from '@angular/core';

import { CoverageFilters } from '../../core/models/api.models';
import { CoverageService, MunicipalitiesService } from '../../core/services/api.services';
import { FilterStore } from '../../core/state/filter-store.service';
import { ChartComponent } from '../../shared/components/chart.component';
import { StatePanelComponent } from '../../shared/components/state-panel.component';
import { loadOnChange, loadOnce } from '../../shared/state/load-state';
import { lineChart } from '../../shared/utils/charts';
import { formatPercent, formatPoints, municipalityLabel } from '../../shared/utils/format';

const PALETTE = ['#1f4e79', '#c62828', '#2e7d32', '#6a1b9a', '#ef6c00', '#00838f'];
const MAX_COMPARE = 5;

@Component({
  selector: 'app-coverage-page',
  standalone: true,
  imports: [ChartComponent, StatePanelComponent],
  template: `
    <section class="page" aria-labelledby="cov-title">
      <div>
        <h2 id="cov-title" class="page__title">Histórico de cobertura</h2>
        <p class="page__lead">
          Evolução anual de cobertura e déficit. Selecione até {{ max }} municípios para comparar.
        </p>
      </div>

      <form class="filters" (submit)="$event.preventDefault()" aria-label="Filtros do histórico">
        <div class="field">
          <label for="h-immunizer">Imunizante</label>
          <select id="h-immunizer" [disabled]="immunizers().length === 0" (change)="onImmunizer($event)">
            <option value="">{{ immunizers().length === 0 ? 'Indisponível nos dados' : 'Todos' }}</option>
            @for (i of immunizers(); track i) {
              <option [value]="i" [selected]="store.immunizer() === i">{{ i }}</option>
            }
          </select>
        </div>
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
      </form>

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
        <app-state-panel kind="error" [message]="h.message" />
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

  private readonly filterOptions = loadOnce(() => this.coverageApi.filters());
  private readonly municipalityList = loadOnce(() => this.municipalitiesApi.list({}, 1000, 0));

  private readonly query = computed<CoverageFilters>(() => ({
    immunizer: this.store.immunizer(),
    municipality_code: this.selected(),
  }));
  protected readonly history = loadOnChange(this.query, (q) => this.coverageApi.history(q));

  protected readonly pct = formatPercent;
  protected readonly pts = formatPoints;

  protected readonly immunizers = computed(() => {
    const state = this.filterOptions();
    return state.status === 'success' ? state.data.immunizers : [];
  });

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

  protected nameOf(code: string): string {
    const state = this.municipalityList();
    if (state.status !== 'success') return code;
    const found = state.data.items.find((i) => i.municipality_code === code);
    return found ? municipalityLabel(found.municipality_name, code) : code;
  }

  protected onImmunizer(event: Event): void {
    this.store.immunizer.set((event.target as HTMLSelectElement).value || null);
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
