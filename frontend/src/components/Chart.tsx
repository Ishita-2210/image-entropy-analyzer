import { useEffect, useRef } from 'react';
import * as echarts from 'echarts/core';
import { BarChart, HeatmapChart, LineChart, ScatterChart } from 'echarts/charts';
import {
  DataZoomComponent,
  GridComponent,
  LegendComponent,
  TooltipComponent,
  VisualMapComponent,
} from 'echarts/components';
import { SVGRenderer } from 'echarts/renderers';
import type { EChartsOption } from 'echarts';

echarts.use([
  BarChart,
  LineChart,
  HeatmapChart,
  ScatterChart,
  GridComponent,
  TooltipComponent,
  LegendComponent,
  VisualMapComponent,
  DataZoomComponent,
  SVGRenderer,
]);
export function Chart({
  option,
  label,
  height = 270,
  onSelect,
}: {
  option: EChartsOption;
  label: string;
  height?: number;
  onSelect?: (data: number[]) => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const instance = useRef<echarts.ECharts | null>(null);
  const handler = useRef(onSelect);
  handler.current = onSelect;
  useEffect(() => {
    const chart = echarts.init(ref.current!, undefined, { renderer: 'svg' });
    instance.current = chart;
    chart.on('click', (params) => {
      if (Array.isArray(params.value)) handler.current?.(params.value as number[]);
    });
    const observer = new ResizeObserver(() => {
      if (ref.current?.clientWidth) chart.resize();
    });
    observer.observe(ref.current!);
    return () => {
      observer.disconnect();
      chart.dispose();
      instance.current = null;
    };
  }, []);
  useEffect(() => {
    instance.current?.setOption(
      {
        animation: false,
        color: ['#64836a', '#a6b59c', '#b79e71', '#577f8d'],
        textStyle: { fontFamily: 'system-ui', color: '#657166' },
        ...option,
      },
      true,
    );
  }, [option]);
  return <div ref={ref} role="img" aria-label={label} style={{ height, width: '100%' }} />;
}
