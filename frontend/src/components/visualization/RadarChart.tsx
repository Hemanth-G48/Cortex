import {
  RadarChart as RechartRadar,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  ResponsiveContainer,
  Tooltip,
} from 'recharts';

interface RadarDataPoint {
  subject: string;
  score: number;
  fullMark: number;
}

interface StudentRadarChartProps {
  data?: RadarDataPoint[];
  color?: string;
}

const defaultData: RadarDataPoint[] = [
  { subject: 'Courses', score: 80, fullMark: 100 },
  { subject: 'Tasks', score: 65, fullMark: 100 },
  { subject: 'Habits', score: 45, fullMark: 100 },
  { subject: 'Focus', score: 70, fullMark: 100 },
  { subject: 'Fitness', score: 50, fullMark: 100 },
  { subject: 'Goals', score: 60, fullMark: 100 },
];

/** Radar chart for student life stats */
export const StudentRadarChart = ({ data, color }: StudentRadarChartProps) => {
  const chartData = data ?? defaultData;
  const fill = color ?? 'var(--accent, #e8496d)';

  return (
    <div className="chart-container">
      <ResponsiveContainer width="100%" height={280}>
        <RechartRadar data={chartData} cx="50%" cy="50%" outerRadius="70%">
          <PolarGrid stroke="var(--border)" />
          <PolarAngleAxis dataKey="subject" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} />
          <PolarRadiusAxis angle={30} domain={[0, 100]} tick={false} axisLine={false} />
          <Tooltip
            contentStyle={{
              background: 'var(--bg-card)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--radius)',
              color: 'var(--text-primary)',
              fontSize: '0.8rem',
            }}
          />
          <Radar name="Score" dataKey="score" stroke={fill} fill={fill} fillOpacity={0.2} strokeWidth={2} />
        </RechartRadar>
      </ResponsiveContainer>
    </div>
  );
};
