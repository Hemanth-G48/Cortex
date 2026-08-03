import { StudentRadarChart } from '../visualization/RadarChart';

export interface LifeDimension {
  label: string;
  value: number;
}

const DEFAULT_DIMENSIONS: LifeDimension[] = [
  { label: 'Finance', value: 55 },
  { label: 'Physical Health', value: 65 },
  { label: 'Work', value: 70 },
  { label: 'Personal Life', value: 75 },
  { label: 'Overall', value: 60 },
];

/** Life dimensions radar (5 axes) in the Life Planner magenta accent. */
export const RadarChartWidget = ({ dimensions }: { dimensions?: LifeDimension[] }) => {
  const data = (dimensions ?? DEFAULT_DIMENSIONS).map((d) => ({
    subject: d.label,
    score: d.value,
    fullMark: 100,
  }));

  return (
    <div>
      <div className="lp-section-title">Life Dimensions</div>
      <StudentRadarChart data={data} color="#e8496d" />
    </div>
  );
};
