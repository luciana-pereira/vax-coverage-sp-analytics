import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';

import { HeaderComponent } from './header.component';
import { SidebarComponent } from './sidebar.component';

@Component({
  selector: 'app-shell',
  standalone: true,
  imports: [HeaderComponent, SidebarComponent, RouterOutlet],
  template: `
    <a class="skip-link" href="#main">Ir para o conteúdo</a>
    <app-header />
    <div class="shell">
      <app-sidebar />
      <main id="main" class="main" tabindex="-1">
        <router-outlet />
      </main>
    </div>
  `,
})
export class ShellComponent {}
