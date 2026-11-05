import { TestBed } from '@angular/core/testing';

import { FilterStore } from './filter-store.service';

describe('FilterStore', () => {
  it('exposes the active filters and resets them', () => {
    const store = TestBed.inject(FilterStore);
    store.year.set(2023);
    store.deficitClass.set('alto');

    expect(store.filters()).toEqual({ year: 2023, immunizer: null, deficit_class: 'alto' });

    store.reset();
    expect(store.filters()).toEqual({ year: null, immunizer: null, deficit_class: null });
  });
});
