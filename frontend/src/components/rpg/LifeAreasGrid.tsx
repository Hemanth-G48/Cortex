import { RpgCard } from './RpgCard';
import { RpgBadge } from './RpgBadge';
import { RpgButton } from './RpgButton';
import type { LifeArea } from '../../services/api';

interface LifeAreasGridProps {
  areas: LifeArea[];
  onEdit: (area: LifeArea) => void;
}

export const LifeAreasGrid = ({ areas, onEdit }: LifeAreasGridProps) => {
  if (areas.length === 0) {
    return (
      <div className="rpg-empty">
        <p>No life areas yet</p>
      </div>
    );
  }

  return (
    <div className="rpg-grid-2col">
      {areas.map((area) => (
        <RpgCard key={area.id} className="rpg-life-area-card">
          <div className="rpg-card-header">
            <h3>{area.name}</h3>
            <RpgBadge variant="orange">{area.progress_percent}%</RpgBadge>
          </div>
          {area.description && <p className="rpg-card-desc">{area.description}</p>}
          <div className="rpg-progress-bar">
            <div
              className="rpg-progress-fill rpg-progress-fill-orange"
              style={{ width: `${area.progress_percent}%` }}
            />
          </div>
          <RpgButton variant="ghost" size="sm" onClick={() => onEdit(area)}>
            Edit
          </RpgButton>
        </RpgCard>
      ))}
    </div>
  );
};
