import React, { useId } from 'react';

/**
 * Compact telemetry sparkline. Renders an accessible SVG line + area.
 */
export function Sparkline({
  data = [],
  color = 'var(--primary)',
  width = 120,
  height = 32,
  label = '24-hour trend',
  className = '',
  showEndPoint = true,
}) {
  const gradientId = `spark-${useId().replace(/[^a-zA-Z0-9_-]/g, '')}`;
  const values = data
    .map((point) => (typeof point === 'number' ? point : Number(point?.value)))
    .filter((value) => Number.isFinite(value));

  if (values.length === 0) {
    return <span className={`sparkline-empty ${className}`.trim()}>No trend data</span>;
  }

  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  const padding = 4;
  const usableWidth = width - padding * 2;
  const usableHeight = height - padding * 2;

  const coordinates = values.map((value, index) => {
    const x = padding + (values.length === 1 ? usableWidth / 2 : (index / (values.length - 1)) * usableWidth);
    const y = padding + (1 - (value - min) / span) * usableHeight;
    return { x: Number(x.toFixed(2)), y: Number(y.toFixed(2)), value };
  });

  const linePath = coordinates.map((point, index) => `${index === 0 ? 'M' : 'L'}${point.x},${point.y}`).join(' ');
  const areaPath = `${linePath} L${coordinates[coordinates.length - 1].x},${height - padding} L${coordinates[0].x},${height - padding} Z`;
  const last = coordinates[coordinates.length - 1];

  return (
    <svg
      className={`sparkline ${className}`.trim()}
      viewBox={`0 0 ${width} ${height}`}
      role="img"
      aria-label={`${label}: ${values.join(', ')}`}
      preserveAspectRatio="none"
    >
      <title>{`${label}. Latest ${last.value}.`}</title>
      <defs>
        <linearGradient id={gradientId} x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stopColor={color} stopOpacity="0.28" />
          <stop offset="100%" stopColor={color} stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={areaPath} fill={`url(#${gradientId})`} />
      <path
        d={linePath}
        fill="none"
        stroke={color}
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        vectorEffect="non-scaling-stroke"
      />
      {showEndPoint && <circle cx={last.x} cy={last.y} r="2.6" fill={color} />}
    </svg>
  );
}

export default Sparkline;
