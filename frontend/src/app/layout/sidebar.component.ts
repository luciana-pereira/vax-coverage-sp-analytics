import { Component, inject, signal } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';

import { ThemeService } from '../core/state/theme.service';

interface NavItem {
  path: string;
  label: string;
}

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [RouterLink, RouterLinkActive],
  template: `
    <nav class="sidebar" aria-label="Navegação principal">
      <div class="sidebar__top">
        <div class="sidebar__identity">
          <span class="sidebar__mark" aria-hidden="true">💉</span>
          <div>
            <span class="sidebar__title">Vax Coverage SP</span>
            <span class="sidebar__section-label">Painel analítico</span>
          </div>
        </div>
        <button
          class="sidebar__menu-toggle"
          type="button"
          [attr.aria-expanded]="menuOpen()"
          aria-controls="primary-navigation"
          (click)="toggleMenu()"
        >
          {{ menuOpen() ? 'Fechar menu' : 'Menu' }}
        </button>
      </div>
      <ul
        id="primary-navigation"
        class="sidebar__list"
        [class.sidebar__list--open]="menuOpen()"
      >
        @for (item of items; track item.path) {
          <li>
            <a
              [routerLink]="item.path"
              routerLinkActive="active"
              ariaCurrentWhenActive="page"
              (click)="closeMenu()"
              >{{ item.label }}</a
            >
          </li>
        }
      </ul>
      <div class="sidebar__footer">
        <button class="theme-toggle" type="button" (click)="theme.toggle()">
          <span aria-hidden="true">{{ theme.theme() === 'dark' ? '◐' : '◑' }}</span>
          {{ theme.theme() === 'dark' ? 'Usar tema claro' : 'Usar tema escuro' }}
        </button>
      </div>
    </nav>
  `,
})
export class SidebarComponent {
  protected readonly theme = inject(ThemeService);
  protected readonly menuOpen = signal(false);

  protected readonly items: NavItem[] = [
    { path: '/dashboard', label: 'Visão geral' },
    { path: '/cobertura', label: 'Histórico' },
    { path: '/municipios', label: 'Municípios' },
    { path: '/previsoes', label: 'Previsões' },
    { path: '/modelos', label: 'Modelos' },
    { path: '/qualidade-dados', label: 'Qualidade dos dados' },
  ];

  protected toggleMenu(): void {
    this.menuOpen.update((open) => !open);
  }

  protected closeMenu(): void {
    this.menuOpen.set(false);
  }
}
