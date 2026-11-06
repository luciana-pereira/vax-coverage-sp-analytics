import { Component } from '@angular/core';

@Component({
  selector: 'app-header',
  standalone: true,
  template: `
    <header class="header">
      <div class="header__identity">
        <div>
          <h1 class="header__title">Vax Coverage SP</h1>
          <p class="header__subtitle">Inteligência em saúde pública</p>
        </div>
      </div>
      <p class="header__context">Cobertura vacinal · Estado de São Paulo</p>
    </header>
  `,
})
export class HeaderComponent {}
