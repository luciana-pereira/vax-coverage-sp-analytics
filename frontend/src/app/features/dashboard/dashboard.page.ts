import { Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';

import { MunicipalityItem } from '../../core/models/api.models';
import {
  CoverageService,
  GeoService,
  MunicipalitiesService,
  PredictionsService,
} from '../../core/services/api.services';
import { FilterStore } from '../../core/state/filter-store.service';
import { ChartComponent } from '../../shared/components/chart.component';
import { ChoroplethMapComponent, MapMetric } from '../../shared/components/choropleth-map.component';
import { FiltersBarComponent } from '../../shared/components/filters-bar.component';
import { KpiCardComponent } from '../../shared/components/kpi-card.component';
import { RiskBadgeComponent } from '../../shared/components/risk-badge.component';
import { StatePanelComponent } from '../../shared/components/state-panel.component';
import { loadOnChange, loadOnce } from '../../shared/state/load-state';
import { barChart, doughnutChart, lineChart } from '../../shared/utils/charts';
import {
  RISK_COLORS,
  RISK_LABELS,
  RISK_ORDER,
  formatInteger,
  formatPercent,
  formatPoints,
  municipalityLabel,
  riskColor,
} from '../../shared/utils/format';

@Component({
  selector: 'app-dashboard-page',
  standalone: true,
  imports: [
    ChartComponent,
    ChoroplethMapComponent,
    FiltersBarComponent,
    KpiCardComponent,
    RiskBadgeComponent,
    RouterLink,
    StatePanelComponent,
  ],
  template: `
    <section class="page" aria-labelledby="dash-title">
      <div>
        <h2 id="dash-title" class="page__title">Visão geral</h2>
        <p class="page__lead">Cobertura vacinal e déficit por município — {{ periodLabel() }}.</p>
      </div>

      <app-filters-bar />

      @let cov = coverage();
      @if (cov.status === 'loading') {
        <app-state-panel kind="loading" />
      } @else if (cov.status === 'error') {
        <app-state-panel kind="error" [message]="cov.message" />
      } @else if (cov.data.status !== 'ok' || !cov.data.summary) {
        <app-state-panel kind="unavailable" [message]="cov.data.message">
          <a routerLink="/qualidade-dados">Ver o que falta na página de qualidade dos dados</a>
        </app-state-panel>
      } @else {
        @let s = cov.data.summary;
        <div class="grid grid--kpi">
          <app-kpi-card label="Cobertura média" [value]="pct(s.mean_coverage)" [hint]="periodLabel()" />
          <app-kpi-card label="Déficit médio" [value]="pts(s.mean_deficit)" hint="Média simples das linhas" />
          <app-kpi-card label="Municípios analisados" [value]="int(s.municipalities)" />
          <app-kpi-card label="Abaixo da meta" [value]="int(s.municipalities_below_target)" hint="Déficit maior que zero" />
          <app-kpi-card label="Situação crítica" [value]="int(s.critical_municipalities)" hint="Classe de déficit alto" tone="alert" />
        </div>

        <div class="grid grid--map">
          <article class="card">
            <h2>Mapa de municípios</h2>
            <div class="toolbar">
              <label for="metric">Indicador</label>
              <select id="metric" (change)="onMetric($event)">
                <option value="risk" selected>Classificação de risco</option>
                <option value="coverage">Cobertura média</option>
                <option value="deficit">Déficit médio</option>
              </select>
            </div>
            @let list = municipalities();
            @if (list.status === 'loading') {
              <app-state-panel kind="loading" />
            } @else if (list.status === 'error') {
              <app-state-panel kind="error" [message]="list.message" />
            } @else {
              <app-choropleth-map
                [geo]="geoData()"
                [items]="list.data.items"
                [metric]="metric()"
                [selected]="selectedCode()"
                (selectMunicipality)="selectedCode.set($event)"
              />
            }
            @if (selected(); as m) {
              <p class="page__lead">
                <strong>{{ label(m) }}</strong>: cobertura {{ pct(m.mean_coverage) }}, déficit
                {{ pts(m.mean_deficit) }} <app-risk-badge [value]="m.deficit_class" />
                <a [routerLink]="['/municipios', m.municipality_code]">Detalhes</a>
              </p>
            }
          </article>
          <article class="card">
            <h2>Distribuição do déficit</h2>
            @if (distribution(); as chart) {
              <app-chart [config]="chart" ariaLabel="Distribuição de linhas por classe de déficit" />
            } @else {
              <app-state-panel kind="empty" message="Sem classes de déficit para os filtros." />
            }
          </article>
        </div>

        <div class="grid grid--two">
          <article class="card">
            <h2>Evolução temporal</h2>
            @let hist = history();
            @let histConfig = historyChart();
            @if (hist.status === 'loading') {
              <app-state-panel kind="loading" />
            } @else if (hist.status === 'error') {
              <app-state-panel kind="error" [message]="hist.message" />
            } @else if (histConfig) {
              <app-chart [config]="histConfig" ariaLabel="Cobertura e déficit médios por ano" />
            } @else {
              <app-state-panel kind="empty" message="Sem série histórica." />
            }
          </article>
          <article class="card">
            <h2>Municípios com maior déficit</h2>
            @if (s.records === 0 || cov.data.top_deficit_municipalities.length === 0) {
              <app-state-panel kind="empty" />
            } @else {
              <div class="table-wrap">
                <table class="table">
                  <thead>
                    <tr><th>Município</th><th class="num">Cobertura</th><th class="num">Déficit</th></tr>
                  </thead>
                  <tbody>
                    @for (r of cov.data.top_deficit_municipalities; track r.municipality_code) {
                      <tr>
                        <td>
                          <a [routerLink]="['/municipios', r.municipality_code]">{{
                            label(r)
                          }}</a>
                        </td>
                        <td class="num">{{ pct(r.mean_coverage) }}</td>
                        <td class="num">{{ pts(r.mean_deficit) }}</td>
                      </tr>
                    }
                  </tbody>
                </table>
              </div>
            }
          </article>
        </div>
      }

      <article class="card">
        <h2>Indicadores de previsão</h2>
        @let pred = predictions();
        @if (pred.status === 'loading') {
          <app-state-panel kind="loading" />
        } @else if (pred.status === 'error') {
          <app-state-panel kind="error" [message]="pred.message" />
        } @else if (pred.data.status !== 'ok' || pred.data.total === 0) {
          <app-state-panel kind="unavailable" [message]="pred.data.message" />
        } @else {
          <p class="page__lead">
            Classe de déficit prevista para {{ pred.data.target_year }} (modelo
            <strong>{{ pred.data.model_name }}</strong
            >, {{ int(pred.data.total) }} combinações).
            <a routerLink="/previsoes">Ver previsões</a>
          </p>
          @if (predictionChart(); as chart) {
            <app-chart [config]="chart" ariaLabel="Previsões por classe de déficit" />
          }
        }
      </article>
    </section>
  `,
})
export class DashboardPage {
  private readonly store = inject(FilterStore);
  private readonly coverageApi = inject(CoverageService);
  private readonly municipalitiesApi = inject(MunicipalitiesService);
  private readonly predictionsApi = inject(PredictionsService);
  private readonly geoApi = inject(GeoService);

  protected readonly coverage = loadOnChange(this.store.filters, (f) =>
    this.coverageApi.overview(f, 10),
  );
  private readonly historyFilters = computed(() => ({
    immunizer: this.store.immunizer(),
    deficit_class: this.store.deficitClass(),
  }));
  protected readonly history = loadOnChange(this.historyFilters, (f) => this.coverageApi.history(f));
  protected readonly municipalities = loadOnChange(this.store.filters, (f) =>
    this.municipalitiesApi.list(f, 1000, 0),
  );
  private readonly geo = loadOnce(() => this.geoApi.municipalities());
  protected readonly predictions = loadOnce(() => this.predictionsApi.list({ limit: 1 }));

  protected readonly metric = signal<MapMetric>('risk');
  protected readonly selectedCode = signal<string | null>(null);

  protected readonly pct = formatPercent;
  protected readonly pts = formatPoints;
  protected readonly int = formatInteger;

  protected readonly periodLabel = computed(() => {
    const year = this.store.year();
    return year === null ? 'todos os anos' : `ano ${year}`;
  });

  protected readonly geoData = computed(() => {
    const state = this.geo();
    return state.status === 'success' ? state.data : null;
  });

  protected readonly selected = computed<MunicipalityItem | null>(() => {
    const state = this.municipalities();
    const code = this.selectedCode();
    if (state.status !== 'success' || !code) return null;
    return state.data.items.find((i) => i.municipality_code === code) ?? null;
  });

  protected readonly distribution = computed(() => {
    const state = this.coverage();
    if (state.status !== 'success' || state.data.deficit_distribution.length === 0) return null;
    const items = state.data.deficit_distribution;
    return doughnutChart(
      items.map((i) => RISK_LABELS[i.deficit_class] ?? i.deficit_class),
      items.map((i) => i.count),
      items.map((i) => riskColor(i.deficit_class)),
    );
  });

  protected readonly historyChart = computed(() => {
    const state = this.history();
    if (state.status !== 'success') return null;
    const points = state.data.series[0]?.points ?? [];
    if (points.length === 0) return null;
    return lineChart(
      points.map((p) => p.year),
      [
        { label: 'Cobertura média (%)', data: points.map((p) => p.mean_coverage), color: '#1f4e79' },
        { label: 'Déficit médio (p.p.)', data: points.map((p) => p.mean_deficit), color: '#c62828' },
      ],
      'Percentual / pontos percentuais',
    );
  });

  protected readonly predictionChart = computed(() => {
    const state = this.predictions();
    if (state.status !== 'success') return null;
    const distribution = state.data.class_distribution;
    const keys = RISK_ORDER.filter((k) => k in distribution);
    if (keys.length === 0) return null;
    return barChart(
      keys.map((k) => RISK_LABELS[k]),
      [{ label: 'Combinações', data: keys.map((k) => distribution[k]), colors: keys.map((k) => RISK_COLORS[k]) }],
    );
  });

  protected label(item: { municipality_name: string | null; municipality_code: string }): string {
    return municipalityLabel(item.municipality_name, item.municipality_code);
  }

  protected onMetric(event: Event): void {
    this.metric.set((event.target as HTMLSelectElement).value as MapMetric);
  }
}
