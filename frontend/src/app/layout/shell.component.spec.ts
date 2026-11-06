import { TestBed } from '@angular/core/testing';
import { provideRouter } from '@angular/router';

import { ShellComponent } from './shell.component';

describe('ShellComponent', () => {
  it('keeps navigation outside the scrollable main and the header inside it', async () => {
    TestBed.configureTestingModule({ providers: [provideRouter([])] });
    const fixture = TestBed.createComponent(ShellComponent);
    fixture.detectChanges();
    await fixture.whenStable();

    const root = fixture.nativeElement as HTMLElement;
    const main = root.querySelector('main');
    expect(root.querySelector('.shell > app-sidebar')).not.toBeNull();
    expect(root.querySelector('.sidebar__title')?.textContent).toContain('Vax Coverage SP');
    expect(root.querySelector('.sidebar__mark')?.textContent).toContain('💉');
    expect(root.querySelector('.header__mark')).toBeNull();
    expect(main?.querySelector('app-header')).not.toBeNull();
    expect(main?.querySelector('.main__content > router-outlet')).not.toBeNull();
    expect(root.querySelector('.skip-link')?.getAttribute('href')).toBe('#main');
    expect(main?.getAttribute('tabindex')).toBe('-1');
  });
});
