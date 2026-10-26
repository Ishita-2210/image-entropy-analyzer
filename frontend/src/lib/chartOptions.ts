import type { EChartsOption } from 'echarts';

export function lineOption(
  x: (number | string)[],
  lines: { name: string; values: (number | null)[] }[],
  xLabel: string,
  yLabel: string,
): EChartsOption {
  return {
    tooltip: { trigger: 'axis' },
    legend: { bottom: 0, icon: 'roundRect', itemWidth: 12, itemHeight: 3 },
    grid: { top: 25, right: 22, left: 64, bottom: 70 },
    xAxis: {
      type: 'category',
      data: x,
      name: xLabel,
      nameLocation: 'middle',
      nameGap: 28,
      axisLine: { lineStyle: { color: '#d9ded5' } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      name: yLabel,
      nameTextStyle: { align: 'left' },
      splitLine: { lineStyle: { color: '#eef0eb' } },
    },
    dataZoom: x.length > 128 ? [{ type: 'inside' }] : [],
    series: lines.map((l) => ({
      name: l.name,
      type: 'line',
      data: l.values,
      showSymbol: x.length < 30,
      lineStyle: { width: 2 },
      areaStyle: lines.length === 1 ? { opacity: 0.12 } : undefined,
    })),
  };
}
export function heatOption(
  map: (number | null)[][],
  x: (number | string)[],
  y: (number | string)[],
  max: number,
  label = 'bits',
  min = 0,
): EChartsOption {
  return {
    tooltip: {
      formatter: (params) => {
        const p = (Array.isArray(params) ? params[0] : params) as { value: number[] };
        const [cx, cy, v] = p.value;
        return `${x[cx]}, ${y[cy]}: ${typeof v === 'number' ? v.toFixed(3) : 'undefined'} ${label}`;
      },
    },
    grid: { top: 12, left: 45, right: 20, bottom: 60 },
    xAxis: { type: 'category', data: x, splitArea: { show: false } },
    yAxis: { type: 'category', data: y, inverse: true },
    visualMap: {
      min,
      max: max || 1,
      orient: 'horizontal',
      left: 'center',
      bottom: 0,
      inRange: { color: ['#eff2dc', '#b9c99a', '#729b79', '#35665b', '#183b3c'] },
      text: [label, String(min)],
      calculable: true,
    },
    series: [
      {
        type: 'heatmap',
        progressive: 0,
        data: map.flatMap((row, j) => row.flatMap((v, i) => (v === null ? [] : [[i, j, v]]))),
      },
    ],
  };
}
