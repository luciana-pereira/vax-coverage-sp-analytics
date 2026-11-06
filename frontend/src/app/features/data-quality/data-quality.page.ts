import { Component, computed, inject } from '@angular/core';

import { DataQualityService } from '../../core/services/api.services';
import { ChartComponent } from '../../shared/components/chart.component';
import { KpiCardComponent } from '../../shared/components/kpi-card.component';
import { StatePanelComponent } from '../../shared/components/state-panel.component';
import { loadOnce } from '../../shared/state/load-state';
import { barChart } from '../../shared/utils/charts';
import { formatInteger, formatPercent } from '../../shared/utils/format';

@Component({
  selector: 'app-data-quality-page',
  standalone: true,
  imports: [ChartComponent, KpiCardComponent, StatePanelComponent],
  template: `
    <section class="page" aria-labelledby="dq-title">
      <div>
        <h2 id="dq-title" class="page__title">Qualidade dos dados</h2>
        <p class="page__lead">Estado dos artefatos do pipeline e dependências ainda pendentes.</p>
      </div>

      @let r = report();
      @if (r.status === 'loading') {
        <app-state-panel kind="loading" />
      } @else if (r.status === 'error') {
        <app-state-panel kind="error" [message]="r.message" [retryable]="true" (retry)="report.retry()" />
      } @else {
        @if (r.data.known_gaps.length > 0) {
          <article class="card">
            <h2>Pendências conhecidas</h2>
            <ul class="gaps">
              @for (gap of r.data.known_gaps; track gap) {
                <li>{{ gap }}</li>
              }
            </ul>
          </article>
        }

        @if (r.data.dataset; as ds) {
          <div class="grid grid--kpi">
            <app-kpi-card label="Linhas" [value]="int(ds.rows)" />
            <app-kpi-card label="Municípios" [value]="int(ds.municipalities)" />
            <app-kpi-card label="Período" [value]="(ds.year_min ?? '—') + ' – ' + (ds.year_max ?? '—')" />
            <app-kpi-card label="Linhas duplicadas" [value]="int(ds.duplicate_rows)" [tone]="ds.duplicate_rows > 0 ? 'alert' : 'default'" />
          </div>
          @if (ds.missing_columns.length > 0) {
            <app-state-panel kind="unavailable" [message]="'Colunas ausentes: ' + ds.missing_columns.join(', ')" />
          }
          <div class="grid grid--two">
            <article class="card">
              <h2>Proporção de valores nulos</h2>
              @if (nullsChart(); as config) {
                <app-chart [config]="config" ariaLabel="Proporção de valores nulos por coluna" />
              } @else {
                <app-state-panel kind="empty" message="Nenhum valor nulo registrado no dataset." />
              }
            </article>
            <article class="card">
              <h2>Registros por ano</h2>
              @if (yearlyChart(); as config) {
                <app-chart [config]="config" ariaLabel="Quantidade de registros por ano" />
              } @else {
                <app-state-panel kind="empty" message="O dataset não informa registros agrupados por ano." />
              }
            </article>
          </div>
          <article class="card">
            <h2>Valores nulos por coluna</h2>
            <div class="table-wrap">
              <table class="table">
                <thead><tr><th>Coluna</th><th class="num">Nulos</th><th class="num">Proporção</th></tr></thead>
                <tbody>
                  @for (c of ds.columns; track c.name) {
                    <tr>
                      <td>{{ c.name }}</td>
                      <td class="num">{{ int(c.null_count) }}</td>
                      <td class="num">{{ pct(c.null_ratio * 100) }}</td>
                    </tr>
                  }
                </tbody>
              </table>
            </div>
          </article>
        } @else {
          <app-state-panel kind="unavailable" message="Dataset de features ainda não gerado." />
        }

        <article class="card">
          <h2>Artefatos</h2>
          <div class="table-wrap">
            <table class="table">
              <thead><tr><th>Artefato</th><th>Caminho</th><th>Status</th></tr></thead>
              <tbody>
                @for (a of r.data.artifacts; track a.name) {
                  <tr>
                    <td>{{ a.description }}</td>
                    <td><code>{{ a.path }}</code></td>
                    <td>
                      <span class="badge" [class.badge--ok]="a.exists" [class.badge--missing]="!a.exists">
                        {{ a.exists ? 'Presente' : 'Ausente' }}
                      </span>
                    </td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        </article>
      }
    </section>
  `,
})
export class DataQualityPage {
  private readonly api = inject(DataQualityService);
  protected readonly report = loadOnce(() => this.api.report());
  protected readonly int = formatInteger;
  protected readonly pct = formatPercent;

  protected readonly nullsChart = computed(() => {
    const state = this.report();
    if (state.status !== 'success' || !state.data.dataset) return null;
    const columns = state.data.dataset.columns.filter((column) => column.null_count > 0);
    if (columns.length === 0) return null;
    return barChart(
      columns.map((column) => column.name),
      [{ label: 'Proporção de nulos', data: columns.map((column) => column.null_ratio), colors: '#e55c54' }],
      { horizontal: true, yTitle: 'Proporção (0–1)', max: 1 },
    );
  });

  protected readonly yearlyChart = computed(() => {
    const state = this.report();
    if (state.status !== 'success' || !state.data.dataset) return null;
    const records = state.data.dataset.records_by_year;
    if (records.length === 0) return null;
    return barChart(
      records.map((item) => String(item.year)),
      [{ label: 'Registros', data: records.map((item) => item.records), colors: '#1769f5' }],
      { yTitle: 'Quantidade de registros' },
    );
  });
}
