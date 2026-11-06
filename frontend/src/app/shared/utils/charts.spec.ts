import { barChart, chartTable, doughnutChart, lineChart } from './charts';

describe('chart builders', () => {
  it('builds a line chart with labels, series and y-axis title', () => {
    const config = lineChart(
      [2022, 2023],
      [
        {
          label: 'Cobertura',
          data: [80, null],
          color: '#123456',
        },
      ],
      'Cobertura (%)',
    );

    expect(config.type).toBe('line');
    expect(config.data?.labels).toEqual(['2022', '2023']);
    expect(config.data?.datasets?.[0]).toEqual(
      jasmine.objectContaining({
        label: 'Cobertura',
        data: [80, null],
        borderColor: '#123456',
        backgroundColor: '#123456',
        tension: 0.2,
        spanGaps: true,
      }),
    );
    expect(config.options).toEqual(
      jasmine.objectContaining({
        scales: jasmine.objectContaining({
          y: jasmine.objectContaining({
            title: jasmine.objectContaining({
              display: true,
              text: 'Cobertura (%)',
            }),
          }),
        }),
      }),
    );
  });

  it('builds a bar chart with horizontal and axis options', () => {
    const config = barChart(
      ['Baixo', 'Alto'],
      [
        {
          label: 'Municípios',
          data: [10, 5],
          colors: ['#111111', '#222222'],
        },
      ],
      {
        horizontal: true,
        yTitle: 'Quantidade',
        max: 20,
      },
    );

    expect(config.type).toBe('bar');
    expect(config.data?.labels).toEqual(['Baixo', 'Alto']);
    expect(config.data?.datasets?.[0]).toEqual(
      jasmine.objectContaining({
        label: 'Municípios',
        data: [10, 5],
        backgroundColor: ['#111111', '#222222'],
      }),
    );
    expect(config.options).toEqual(
      jasmine.objectContaining({
        indexAxis: 'y',
        scales: jasmine.objectContaining({
          x: jasmine.objectContaining({
            beginAtZero: true,
            max: 20,
            title: jasmine.objectContaining({
              display: true,
              text: 'Quantidade',
            }),
          }),
        }),
      }),
    );
  });

  it('builds a doughnut chart with labels, data and colors', () => {
    const config = doughnutChart(
      ['Baixo', 'Moderado', 'Alto'],
      [10, 20, 5],
      ['#111111', '#222222', '#333333'],
    );

    expect(config.type).toBe('doughnut');
    expect(config.data?.labels).toEqual(['Baixo', 'Moderado', 'Alto']);
    expect(config.data?.datasets?.[0]).toEqual(
      jasmine.objectContaining({
        data: [10, 20, 5],
        backgroundColor: ['#111111', '#222222', '#333333'],
      }),
    );
  });

  it('exposes the chart values as accessible tabular data', () => {
    const config = lineChart(
      [2023, 2024],
      [{ label: 'Cobertura (%)', data: [82.5, null], color: '#123456' }],
      'Cobertura (%)',
    );

    expect(chartTable(config)).toEqual({
      series: ['Cobertura (%)'],
      rows: [
        { label: '2023', values: [82.5] },
        { label: '2024', values: [null] },
      ],
    });
  });
});