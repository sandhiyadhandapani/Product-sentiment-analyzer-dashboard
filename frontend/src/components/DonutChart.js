import React from 'react';

const DonutChart = ({ size = 110, strokeWidth = 16, segments = [] }) => {
  const r = (size - strokeWidth) / 2;
  const cx = size / 2;
  const cy = size / 2;
  const circumference = 2 * Math.PI * r;

  const chartSegments = segments.length ? segments : [
    { value: 100, color: '#22c55e' },
  ];

  let cumulative = 0;

  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="rotate-[-90deg]">
      {chartSegments.map((seg, i) => {
        const offset = circumference * (1 - cumulative / 100);
        const dash = (seg.value / 100) * circumference;
        cumulative += seg.value;
        return (
          <circle
            key={i}
            cx={cx}
            cy={cy}
            r={r}
            fill="none"
            stroke={seg.color}
            strokeWidth={strokeWidth}
            strokeDasharray={`${dash} ${circumference - dash}`}
            strokeDashoffset={offset}
            strokeLinecap="butt"
          />
        );
      })}
      {/* Inner white circle */}
      <circle cx={cx} cy={cy} r={r - strokeWidth / 2 - 2} fill="white" />
    </svg>
  );
};

export default DonutChart;
