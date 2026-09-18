import { StudentRadarChart } from '../visualization/RadarChart';
import { EmptyState } from '../shared/EmptyState';

export interface LifeDimension {
  label: string;
  value: number;
}

/**
 * Life dimensions radar in the Life Planner magenta accent.
 *
 * Defect #39: the axes are whatever the live sources return — the parent maps
 * life-area progress and this week's vault mastery into ``dimensions``. There is
 * no hardcoded default series, so an empty result shows the shared empty state
 * instead of invented numbers.
 */
export const RadarChartWidget = ({ dimensions }: { dimensions?: LifeDimension[] }) => {
  const data = (dimensions ?? []).map((d) => ({
    subject: d.label,
    score: d.value,
    fullMark: 100,
  }));

  return (
    <div>
      <div className="lp-section-title">Life Dimensions</div>
      {data.length === 0 ? (
        <EmptyState
          icon="📊"
          title="No life dimensions yet"
          message="Create life areas or study in the vault to populate this radar."
        />
      ) : (
        <StudentRadarChart data={data} color="#e8496d" />
      )}
    </div>
  );
};
