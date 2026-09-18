import { RpgCard } from './RpgCard';
import { RpgBadge } from './RpgBadge';
import { RpgButton } from './RpgButton';
import { areaDocCount } from '../../utils/vaultDomains';
import type { LifeArea, KbDomainSummary } from '../../services/api';

interface LifeAreasGridProps {
  areas: LifeArea[];
  onEdit: (area: LifeArea) => void;
  /** Vault domains from `GET /api/kb/domains` (defect #83). */
  domains?: KbDomainSummary[];
}

export const LifeAreasGrid = ({ areas, onEdit, domains = [] }: LifeAreasGridProps) => {
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
          {areaDocCount(area.name, domains) !== null && (
            <div className="rpg-card-desc" style={{ fontSize: '0.7rem' }}>
              📚 {areaDocCount(area.name, domains)} vault documents
            </div>
          )}
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
