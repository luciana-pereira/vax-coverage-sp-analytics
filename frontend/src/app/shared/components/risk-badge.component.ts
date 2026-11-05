import { Component, input } from '@angular/core';

import { riskColor, riskLabel } from '../utils/format';

@Component({
  selector: 'app-risk-badge',
  standalone: true,
  template: `<span class="badge" [style.--badge-color]="color()">{{ label() }}</span>`,
})
export class RiskBadgeComponent {
  readonly value = input<string | null>(null);

  color(): string {
    return riskColor(this.value());
  }

  label(): string {
    return riskLabel(this.value());
  }
}
