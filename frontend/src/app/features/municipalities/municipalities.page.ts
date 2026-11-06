import { Component, computed, effect, inject, signal, untracked } from '@angular/core';
import { RouterLink } from '@angular/router';

import { MunicipalitiesService } from '../../core/services/api.services';
import { MunicipalityItem } from '../../core/models/api.models';
import { FilterStore } from '../../core/state/filter-store.service';
import { ChartComponent } from '../../shared/components/chart.component';
import { FiltersBarComponent } from '../../shared/components/filters-bar.component';
import { RiskBadgeComponent } from '../../shared/components/risk-badge.component';
import { StatePanelComponent } from '../../shared/components/state-panel.component';
import { VaccinationAnalyticsPanelComponent } from '../../shared/components/vaccination-analytics-panel.component';
import { loadOnChange } from '../../shared/state/load-state';
import { barChart } from '../../shared/utils/charts';
import { formatInteger, formatPercent, formatPoints } from '../../shared/utils/format';

const PAGE_SIZE = 25;
const MAX_COMPARE = 5;

@Component({
  selector: 'app-municipalities-page',
  standalone: true,
  imports: [ChartComponent, FiltersBarComponent, RiskBadgeComponent, RouterLink, StatePanelComponent, VaccinationAnalyticsPanelComponent],
  template: `
    <section class="page" aria-labelledby="mun-title">
      <div>
        <h2 id="mun-title" class="page__title">Municípios</h2>
        <p class="page__lead">Cobertura e déficit médios por município para os filtros selecionados.</p>
      </div>
      <app-filters-bar />
      <app-vaccination-analytics-panel view="municipalities" />

      @let list = municipalities();
      @if (list.status === 'loading') {
        <app-state-panel kind="loading" />
      } @else if (list.status === 'error') {
        <app-state-panel kind="error" [message]="list.message" [retryable]="true" (retry)="municipalities.retry()" />
      } @else if (list.data.status !== 'ok') {
        <app-state-panel kind="unavailable" [message]="list.data.message" />
      } @else if (list.data.items.length === 0) {
        <app-state-panel kind="empty" message="Nenhum município para os filtros." />
      } @else {
        <article class="card">
          <div class="table-wrap">
            <table class="table">
              <thead>
                <tr>
                  <th scope="col">Comparar</th>
                  <th>Município</th><th>Código</th><th class="num">Cobertura</th>
                  <th class="num">Déficit</th><th>Risco</th>
                </tr>
              </thead>
              <tbody>
                @for (m of list.data.items; track m.municipality_code) {
                  <tr>
                    <td>
                      <input
                        type="checkbox"
                        [checked]="isSelected(m.municipality_code)"
                        [disabled]="!isSelected(m.municipality_code) && selectedItems().length >= maxCompare"
                        [attr.aria-label]="'Comparar ' + (m.municipality_name ?? m.municipality_code)"
                        (change)="toggleSelection(m, $event)"
                      />
                    </td>
                    <td>
                      <a [routerLink]="['/municipios', m.municipality_code]">{{
                        m.municipality_name ?? '—'
                      }}</a>
                    </td>
                    <td>{{ m.municipality_code }}</td>
                    <td class="num">{{ pct(m.mean_coverage) }}</td>
                    <td class="num">{{ pts(m.mean_deficit) }}</td>
                    <td><app-risk-badge [value]="m.deficit_class" /></td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
          <div class="pager">
            <span>{{ int(list.data.total) }} municípios — página {{ page() + 1 }} de {{ pages(list.data.total) }}</span>
            <button type="button" class="btn" [disabled]="page() === 0" (click)="go(-1)">Anterior</button>
            <button
              type="button"
              class="btn"
              [disabled]="page() + 1 >= pages(list.data.total)"
              (click)="go(1)"
            >
              Próxima
            </button>
          </div>
        </article>
        @if (selectedItems().length >= 2) {
          <div class="grid grid--two">
            <article class="card">
              <h2>Cobertura dos municípios selecionados</h2>
              @if (coverageChart(); as config) {
                <app-chart [config]="config" ariaLabel="Comparação de cobertura dos municípios selecionados" />
              } @else {
                <app-state-panel kind="empty" message="Sem cobertura válida para comparar." />
              }
            </article>
            <article class="card">
              <h2>Déficit dos municípios selecionados</h2>
              @if (deficitChart(); as config) {
                <app-chart [config]="config" ariaLabel="Comparação de déficit dos municípios selecionados" />
              } @else {
                <app-state-panel kind="empty" message="Sem déficit válido para comparar." />
              }
            </article>
          </div>
        }
      }
    </section>
  `,
})
export class MunicipalitiesPage {
  private readonly store = inject(FilterStore);
  private readonly api = inject(MunicipalitiesService);

  protected readonly page = signal(0);
  protected readonly maxCompare = MAX_COMPARE;
  protected readonly selectedItems = signal<MunicipalityItem[]>([]);
  protected readonly pct = formatPercent;
  protected readonly pts = formatPoints;
  protected readonly int = formatInteger;

  private readonly query = computed(() => ({ filters: this.store.filters(), page: this.page() }));
  protected readonly municipalities = loadOnChange(this.query, (q) =>
    this.api.list(q.filters, PAGE_SIZE, q.page * PAGE_SIZE),
  );

  constructor() {
    effect(() => {
      this.store.filters();
      untracked(() => {
        this.page.set(0);
        this.selectedItems.set([]);
      });
    });
  }

  protected isSelected(code: string): boolean {
    return this.selectedItems().some((item) => item.municipality_code === code);
  }

  protected toggleSelection(item: MunicipalityItem, event: Event): void {
    const checked = (event.target as HTMLInputElement).checked;
    const current = this.selectedItems();
    this.selectedItems.set(
      checked
        ? [...current, item].slice(-MAX_COMPARE)
        : current.filter((selected) => selected.municipality_code !== item.municipality_code),
    );
  }

  protected readonly coverageChart = computed(() => {
    const items = this.selectedItems().filter((item) => item.mean_coverage !== null);
    if (items.length < 2) return null;
    return barChart(
      items.map((item) => item.municipality_name ?? item.municipality_code),
      [{ label: 'Cobertura (%)', data: items.map((item) => item.mean_coverage!), colors: '#1769f5' }],
      { horizontal: true, yTitle: 'Cobertura (%)' },
    );
  });

  protected readonly deficitChart = computed(() => {
    const items = this.selectedItems().filter((item) => item.mean_deficit !== null);
    if (items.length < 2) return null;
    return barChart(
      items.map((item) => item.municipality_name ?? item.municipality_code),
      [{ label: 'Déficit (p.p.)', data: items.map((item) => item.mean_deficit!), colors: '#e55c54' }],
      { horizontal: true, yTitle: 'Déficit (p.p.)' },
    );
  });

  protected pages(total: number): number {
    return Math.max(1, Math.ceil(total / PAGE_SIZE));
  }

  protected go(step: number): void {
    this.page.update((p) => Math.max(0, p + step));
  }
}
