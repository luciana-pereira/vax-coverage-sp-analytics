import { TestBed } from '@angular/core/testing';

import { ThemeService } from './theme.service';

describe('ThemeService', () => {
  beforeEach(() => {
    localStorage.removeItem('vax-coverage-theme');
    document.documentElement.removeAttribute('data-theme');
  });

  it('restores a saved theme and applies it to the document', () => {
    localStorage.setItem('vax-coverage-theme', 'dark');

    const service = TestBed.inject(ThemeService);

    expect(service.theme()).toBe('dark');
    expect(document.documentElement.dataset['theme']).toBe('dark');
  });

  it('toggles and persists the theme', () => {
    const service = TestBed.inject(ThemeService);
    service.setTheme('light');

    service.toggle();
    expect(service.theme()).toBe('dark');
    expect(localStorage.getItem('vax-coverage-theme')).toBe('dark');

    service.toggle();
    expect(service.theme()).toBe('light');
  });
});