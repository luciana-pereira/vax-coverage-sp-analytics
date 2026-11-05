import {
  NO_DATA_COLOR,
  formatInteger,
  formatPercent,
  formatPoints,
  municipalityLabel,
  riskColor,
  riskLabel,
  sequentialColor,
} from './format';

describe('format utils', () => {
  it('formats percentages and points in pt-BR', () => {
    expect(formatPercent(79.25)).toBe('79,3%');
    expect(formatPoints(16)).toBe('16,0 p.p.');
    expect(formatInteger(1234)).toBe('1.234');
  });

  it('shows a dash for missing values', () => {
    expect(formatPercent(null)).toBe('—');
    expect(formatPoints(undefined)).toBe('—');
    expect(formatInteger(null)).toBe('—');
  });

  it('maps deficit classes to colors and labels', () => {
    expect(riskColor('alto')).toBe('#c62828');
    expect(riskColor('desconhecida')).toBe(NO_DATA_COLOR);
    expect(riskLabel('moderado')).toBe('Moderado');
    expect(riskLabel(null)).toBe('—');
  });

  it('scales sequential colors between the extremes', () => {
    expect(sequentialColor(0, 0, 10)).toBe('rgb(222, 235, 247)');
    expect(sequentialColor(10, 0, 10)).toBe('rgb(8, 48, 107)');
    expect(sequentialColor(null, 0, 10)).toBe(NO_DATA_COLOR);
  });

  it('builds municipality labels', () => {
    expect(municipalityLabel('Alpha', '1100')).toBe('Alpha (1100)');
    expect(municipalityLabel(null, '1100')).toBe('1100');
  });
});
