import { Injectable, computed, signal } from '@angular/core';

import { CoverageFilters } from '../models/api.models';

/** Filtros globais compartilhados entre as páginas de análise. */
@Injectable({ providedIn: 'root' })
export class FilterStore {
  readonly year = signal<number | null>(null);
  readonly immunizer = signal<string | null>(null);
  readonly deficitClass = signal<string | null>(null);

  readonly filters = computed<CoverageFilters>(() => ({
    year: this.year(),
    immunizer: this.immunizer(),
    deficit_class: this.deficitClass(),
  }));

  reset(): void {
    this.year.set(null);
    this.immunizer.set(null);
    this.deficitClass.set(null);
  }
}
