import type { Institution } from '../../services/api';
import { StatusBadge } from './StatusBadge';

interface InstitutionTableProps {
  institutions: Institution[];
  onToggle: (institution: Institution) => void;
}

/** Admin table of all institutions with approve/deactivate toggles. */
export const InstitutionTable = ({ institutions, onToggle }: InstitutionTableProps) => (
  <div className="card" style={{ overflowX: 'auto' }}>
    <table className="data-table" style={{ minWidth: 560 }}>
      <thead>
        <tr>
          <th>Institution</th>
          <th>Short</th>
          <th>Status</th>
          <th style={{ textAlign: 'right' }}>Action</th>
        </tr>
      </thead>
      <tbody>
        {institutions.map((i) => (
          <tr key={i.id}>
            <td>
              <div style={{ fontWeight: 600 }}>{i.name}</div>
              {i.description && <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{i.description}</div>}
            </td>
            <td><span className="badge" style={{ color: 'var(--info)' }}>{i.short_name}</span></td>
            <td><StatusBadge active={i.is_active} /></td>
            <td style={{ textAlign: 'right' }}>
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => onToggle(i)}>
                {i.is_active ? 'Deactivate' : 'Approve'}
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  </div>
);
