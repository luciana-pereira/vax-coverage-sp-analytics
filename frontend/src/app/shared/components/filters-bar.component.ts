import { Component, computed, inject } from '@angular/core';

import { CoverageService } from '../../core/services/api.services';
import { FilterStore } from '../../core/state/filter-store.service';
import { riskLabel } from '../utils/format';
import { loadOnce } from '../state/load-state';

@Component({
  selector: 'app-filters-bar',
  standalone: true,
  template: `
    <form class="filters" (submit)="$event.preventDefault()" aria-label="Filtros">
      <div class="field">
        <label for="f-year">Ano</label>
        <select id="f-year" (change)="onYear($event)">
          <option value="" [selected]="store.year() === null">Todos</option>
          @for (y of years(); track y) {
            <option [value]="y" [selected]="store.year() === y">{{ y }}</option>
          }
        </select>
      </div>
      <div class="field">
        <label for="f-immunizer">Imunizante</label>
        <select
          id="f-immunizer"
          [disabled]="immunizers().length === 0"
          (change)="onImmunizer($event)"
        >
          <option value="" [selected]="store.immunizer() === null">
            {{ immunizers().length === 0 ? 'Indisponível nos dados' : 'Todos' }}
          </option>
          @for (i of immunizers(); track i) {
            <option [value]="i" [selected]="store.immunizer() === i">{{ i }}</option>
          }
        </select>
      </div>
      <div class="field">
        <label for="f-class">Classe de déficit</label>
        <select id="f-class" (change)="onClass($event)">
          <option value="" [selected]="store.deficitClass() === null">Todas</option>
          @for (c of classes(); track c) {
            <option [value]="c" [selected]="store.deficitClass() === c">{{ label(c) }}</option>
          }
        </select>
      </div>
      <button type="button" class="btn" (click)="store.reset()">Limpar filtros</button>
    </form>
  `,
})
export class FiltersBarComponent {
  protected readonly store = inject(FilterStore);
  private readonly options = loadOnce(() => inject(CoverageService).filters());

  protected readonly years = computed(() => this.read((o) => o.years));
  protected readonly immunizers = computed(() => this.read((o) => o.immunizers));
  protected readonly classes = computed(() => this.read((o) => o.deficit_classes));

  protected label = riskLabel;

  private read<T>(pick: (o: { years: number[]; immunizers: string[]; deficit_classes: string[] }) => T[]): T[] {
    const state = this.options();
    return state.status === 'success' ? pick(state.data) : [];
  }

  protected onYear(event: Event): void {
    const value = (event.target as HTMLSelectElement).value;
    this.store.year.set(value ? Number(value) : null);
  }

  protected onImmunizer(event: Event): void {
    this.store.immunizer.set((event.target as HTMLSelectElement).value || null);
  }

  protected onClass(event: Event): void {
    this.store.deficitClass.set((event.target as HTMLSelectElement).value || null);
  }
}
