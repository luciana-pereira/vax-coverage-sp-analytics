import { Component, input } from '@angular/core';

@Component({
  selector: 'app-kpi-card',
  standalone: true,
  template: `
    <article class="card kpi" [class.kpi--alert]="tone() === 'alert'">
      <h3 class="kpi__label">{{ label() }}</h3>
      <p class="kpi__value">{{ value() }}</p>
      @if (hint()) {
        <p class="kpi__hint">{{ hint() }}</p>
      }
    </article>
  `,
})
export class KpiCardComponent {
  readonly label = input.required<string>();
  readonly value = input.required<string>();
  readonly hint = input<string>('');
  readonly tone = input<'default' | 'alert'>('default');
}
