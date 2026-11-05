export const RISK_COLORS: Record<string, string> = {
  baixo: '#2e7d32',
  moderado: '#b7791f',
  alto: '#c62828',
};

export const RISK_LABELS: Record<string, string> = {
  baixo: 'Baixo',
  moderado: 'Moderado',
  alto: 'Alto',
};

export const NO_DATA_COLOR = '#d0d5dd';

export const RISK_ORDER = ['baixo', 'moderado', 'alto'];

export function riskColor(deficitClass: string | null | undefined): string {
  return (deficitClass && RISK_COLORS[deficitClass]) || NO_DATA_COLOR;
}

export function riskLabel(deficitClass: string | null | undefined): string {
  return (deficitClass && RISK_LABELS[deficitClass]) || '—';
}

/** Cor sequencial (claro -> escuro) para um valor entre `min` e `max`. */
export function sequentialColor(value: number | null | undefined, min: number, max: number): string {
  if (value === null || value === undefined || Number.isNaN(value)) return NO_DATA_COLOR;
  const span = max - min;
  const t = span > 0 ? Math.min(1, Math.max(0, (value - min) / span)) : 0.5;
  const light = [222, 235, 247];
  const dark = [8, 48, 107];
  const [r, g, b] = light.map((c, i) => Math.round(c + (dark[i] - c) * t));
  return `rgb(${r}, ${g}, ${b})`;
}

export function formatPercent(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined) return '—';
  return `${value.toLocaleString('pt-BR', { maximumFractionDigits: digits, minimumFractionDigits: digits })}%`;
}

export function formatPoints(value: number | null | undefined, digits = 1): string {
  if (value === null || value === undefined) return '—';
  return `${value.toLocaleString('pt-BR', { maximumFractionDigits: digits, minimumFractionDigits: digits })} p.p.`;
}

export function formatInteger(value: number | null | undefined): string {
  if (value === null || value === undefined) return '—';
  return value.toLocaleString('pt-BR');
}

export function formatNumber(value: number | null | undefined, digits = 3): string {
  if (value === null || value === undefined) return '—';
  return value.toLocaleString('pt-BR', { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

export function municipalityLabel(name: string | null | undefined, code: string): string {
  return name ? `${name} (${code})` : code;
}
