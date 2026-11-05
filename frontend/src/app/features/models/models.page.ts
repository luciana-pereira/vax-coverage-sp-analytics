import { Component, computed, inject } from '@angular/core';

import { ModelEntry, ModelMetrics } from '../../core/models/api.models';
import { ModelsService } from '../../core/services/api.services';
import { ChartComponent } from '../../shared/components/chart.component';
import { KpiCardComponent } from '../../shared/components/kpi-card.component';
import { StatePanelComponent } from '../../shared/components/state-panel.component';
import { loadOnce } from '../../shared/state/load-state';
import { barChart } from '../../shared/utils/charts';
import { RISK_LABELS, formatInteger, formatNumber } from '../../shared/utils/format';

const MODEL_LABELS: Record<string, string> = {
  logistic_regression: 'Regressão logística',
  random_forest: 'Random Forest',
  gradient_boosting: 'Gradient Boosting',
};

@Component({
  selector: 'app-models-page',
  standalone: true,
  imports: [ChartComponent, KpiCardComponent, StatePanelComponent],
  template: `
    <section class="page" aria-labelledby="mod-title">
      <div>
        <h2 id="mod-title" class="page__title">Modelos</h2>
        <p class="page__lead">
          Comparação dos modelos candidatos com validação temporal. As métricas abaixo vêm do último
          treino, sem ajustes.
        </p>
      </div>

      @let r = report();
      @if (r.status === 'loading') {
        <app-state-panel kind="loading" />
      } @else if (r.status === 'error') {
        <app-state-panel kind="error" [message]="r.message" />
      } @else if (r.data.status !== 'ok' || !r.data.split) {
        <app-state-panel kind="unavailable" [message]="r.data.message" />
      } @else {
        @let d = r.data;
        @let split = d.split!;
        <div class="grid grid--kpi">
          <app-kpi-card label="Melhor modelo" [value]="modelName(d.best_model)" [hint]="'critério: ' + (d.selection?.criterion ?? '—')" />
          <app-kpi-card label="Alvo" [value]="d.target ?? '—'" hint="classe de déficit do ano seguinte" />
          <app-kpi-card label="Treino" [value]="split.train_years.join(', ')" [hint]="int(split.n_train) + ' linhas'" />
          <app-kpi-card label="Validação" [value]="'' + (split.validation_year ?? '—')" [hint]="int(split.n_validation) + ' linhas'" />
          <app-kpi-card label="Teste" [value]="'' + split.test_year" [hint]="int(split.n_test) + ' linhas'" />
        </div>

        @if (d.selection?.note; as note) {
          <app-state-panel kind="unavailable" [message]="note" />
        }

        <article class="card">
          <h2>Métricas no conjunto de teste</h2>
          <div class="table-wrap">
            <table class="table">
              <thead>
                <tr>
                  <th>Modelo</th><th class="num">F1 (macro)</th><th class="num">Precision (macro)</th>
                  <th class="num">Recall (macro)</th><th class="num">F1 (pond.)</th>
                  <th class="num">Acurácia</th><th class="num">F1 validação</th>
                </tr>
              </thead>
              <tbody>
                @for (m of d.models; track m.name) {
                  <tr>
                    <td>{{ modelName(m.name) }} @if (m.is_best) { <strong>(selecionado)</strong> }</td>
                    <td class="num">{{ num(m.test.f1_macro) }}</td>
                    <td class="num">{{ num(m.test.precision_macro) }}</td>
                    <td class="num">{{ num(m.test.recall_macro) }}</td>
                    <td class="num">{{ num(m.test.f1_weighted) }}</td>
                    <td class="num">{{ num(m.test.accuracy) }}</td>
                    <td class="num">{{ m.validation ? num(m.validation.f1_macro) : '—' }}</td>
                  </tr>
                }
                @if (d.baseline; as b) {
                  <tr>
                    <td>Baseline (persistência)</td>
                    <td class="num">{{ num(b.test.f1_macro) }}</td>
                    <td class="num">{{ num(b.test.precision_macro) }}</td>
                    <td class="num">{{ num(b.test.recall_macro) }}</td>
                    <td class="num">{{ num(b.test.f1_weighted) }}</td>
                    <td class="num">{{ num(b.test.accuracy) }}</td>
                    <td class="num">—</td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
          @if (d.baseline; as b) {
            <p class="page__lead">Baseline: {{ b.description }}.</p>
          }
        </article>

        <div class="grid grid--two">
          <article class="card">
            <h2>F1 macro por modelo</h2>
            @if (f1Chart(); as config) {
              <app-chart [config]="config" ariaLabel="F1 macro de cada modelo no teste" />
            }
          </article>
          <article class="card">
            <h2>Matriz de confusão — {{ modelName(d.best_model) }}</h2>
            @if (best(); as model) {
              <div class="table-wrap">
                <table class="table matrix">
                  <caption class="page__lead">Linhas: classe real; colunas: classe prevista.</caption>
                  <thead>
                    <tr><th></th>@for (c of d.classes; track c) { <th>{{ cls(c) }}</th> }</tr>
                  </thead>
                  <tbody>
                    @for (row of model.test.confusion_matrix; track $index) {
                      <tr>
                        <th>{{ cls(d.classes[$index]) }}</th>
                        @for (value of row; track $index) { <td>{{ int(value) }}</td> }
                      </tr>
                    }
                  </tbody>
                </table>
              </div>
            }
          </article>
        </div>

        <article class="card">
          <h2>Importância das features — {{ modelName(d.best_model) }}</h2>
          @if (importanceChart(); as config) {
            <app-chart [config]="config" ariaLabel="Importância das features do melhor modelo" />
          } @else {
            <app-state-panel kind="empty" message="O modelo selecionado não informa importâncias." />
          }
        </article>
      }
    </section>
  `,
})
export class ModelsPage {
  private readonly api = inject(ModelsService);
  protected readonly report = loadOnce(() => this.api.report());

  protected readonly int = formatInteger;
  protected readonly num = (value: number): string => formatNumber(value, 3);

  protected readonly best = computed<ModelEntry | null>(() => {
    const state = this.report();
    if (state.status !== 'success') return null;
    return state.data.models.find((m) => m.is_best) ?? null;
  });

  protected readonly f1Chart = computed(() => {
    const state = this.report();
    if (state.status !== 'success' || state.data.models.length === 0) return null;
    const models = state.data.models;
    const metric = (m: ModelMetrics): number => m.f1_macro;
    return barChart(
      models.map((m) => this.modelName(m.name)),
      [{ label: 'F1 macro (teste)', data: models.map((m) => metric(m.test)), colors: '#1f4e79' }],
      { yTitle: 'F1 macro', max: 1 },
    );
  });

  protected readonly importanceChart = computed(() => {
    const state = this.report();
    if (state.status !== 'success' || state.data.feature_importance.length === 0) return null;
    const items = state.data.feature_importance.slice(0, 10);
    return barChart(
      items.map((i) => i.feature),
      [{ label: 'Importância', data: items.map((i) => i.importance), colors: '#1f4e79' }],
      { horizontal: true },
    );
  });

  protected modelName(name: string | null): string {
    return name ? (MODEL_LABELS[name] ?? name) : '—';
  }

  protected cls(value: string | undefined): string {
    return value ? (RISK_LABELS[value] ?? value) : '—';
  }
}
