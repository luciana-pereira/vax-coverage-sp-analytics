import { Component, computed, effect, inject, signal, untracked } from '@angular/core';
import { RouterLink } from '@angular/router';

import { MunicipalitiesService } from '../../core/services/api.services';
import { FilterStore } from '../../core/state/filter-store.service';
import { FiltersBarComponent } from '../../shared/components/filters-bar.component';
import { RiskBadgeComponent } from '../../shared/components/risk-badge.component';
import { StatePanelComponent } from '../../shared/components/state-panel.component';
import { loadOnChange } from '../../shared/state/load-state';
import { formatInteger, formatPercent, formatPoints } from '../../shared/utils/format';

const PAGE_SIZE = 25;

@Component({
  selector: 'app-municipalities-page',
  standalone: true,
  imports: [FiltersBarComponent, RiskBadgeComponent, RouterLink, StatePanelComponent],
  template: `
    <section class="page" aria-labelledby="mun-title">
      <div>
        <h2 id="mun-title" class="page__title">Municípios</h2>
        <p class="page__lead">Cobertura e déficit médios por município para os filtros selecionados.</p>
      </div>
      <app-filters-bar />

      @let list = municipalities();
      @if (list.status === 'loading') {
        <app-state-panel kind="loading" />
      } @else if (list.status === 'error') {
        <app-state-panel kind="error" [message]="list.message" />
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
                  <th>Município</th><th>Código</th><th class="num">Cobertura</th>
                  <th class="num">Déficit</th><th>Risco</th>
                </tr>
              </thead>
              <tbody>
                @for (m of list.data.items; track m.municipality_code) {
                  <tr>
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
      }
    </section>
  `,
})
export class MunicipalitiesPage {
  private readonly store = inject(FilterStore);
  private readonly api = inject(MunicipalitiesService);

  protected readonly page = signal(0);
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
      untracked(() => this.page.set(0));
    });
  }

  protected pages(total: number): number {
    return Math.max(1, Math.ceil(total / PAGE_SIZE));
  }

  protected go(step: number): void {
    this.page.update((p) => Math.max(0, p + step));
  }
}
