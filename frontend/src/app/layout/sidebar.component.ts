import { Component } from '@angular/core';
import { RouterLink, RouterLinkActive } from '@angular/router';

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
      <ul>
        @for (item of items; track item.path) {
          <li>
            <a [routerLink]="item.path" routerLinkActive="active" ariaCurrentWhenActive="page">{{
              item.label
            }}</a>
          </li>
        }
      </ul>
    </nav>
  `,
})
export class SidebarComponent {
  protected readonly items: NavItem[] = [
    { path: '/dashboard', label: 'Visão geral' },
    { path: '/cobertura', label: 'Histórico' },
    { path: '/municipios', label: 'Municípios' },
    { path: '/previsoes', label: 'Previsões' },
    { path: '/modelos', label: 'Modelos' },
    { path: '/qualidade-dados', label: 'Qualidade dos dados' },
  ];
}
