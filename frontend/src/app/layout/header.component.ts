import { Component } from '@angular/core';

@Component({
  selector: 'app-header',
  standalone: true,
  template: `
    <header class="header">
      <div>
        <h1 class="header__title">Vax Coverage SP</h1>
        <p class="header__subtitle">Cobertura vacinal no Estado de São Paulo — PI IV UNIVESP</p>
      </div>
    </header>
  `,
})
export class HeaderComponent {}
