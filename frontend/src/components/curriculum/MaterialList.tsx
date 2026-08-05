import type { Material } from '../../services/api';
import { MaterialRow } from './MaterialRow';
import { EmptyState } from '../shared/EmptyState';

interface MaterialListProps {
  items: Material[];
}

/** Vertical list of material rows with an empty state. */
export const MaterialList = ({ items }: MaterialListProps) => {
  if (items.length === 0) {
    return <EmptyState icon="📁" title="No materials yet" message="Upload a PDF, DOCX, TXT or MD file to build this unit's library." />;
  }
  return (
    <div style={{ display: 'grid', gap: '0.5rem' }}>
      {items.map((m) => (
        <MaterialRow key={m.id} material={m} />
      ))}
    </div>
  );
};
