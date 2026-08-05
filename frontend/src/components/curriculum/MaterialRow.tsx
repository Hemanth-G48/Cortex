import { endpoints } from '../../services/api';
import type { Material } from '../../services/api';
import { formatBytes } from '../../utils/format';

const FILE_ICONS: Record<string, string> = {
  pdf: '📄',
  docx: '📝',
  txt: '📃',
  md: '📋',
};

interface MaterialRowProps {
  material: Material;
}

/** One row of the material library: icon, meta, download link. */
export const MaterialRow = ({ material }: MaterialRowProps) => {
  const ext = material.file_type?.toLowerCase() ?? '';
  const icon = FILE_ICONS[ext] ?? '📎';

  return (
    <div
      className="material-row"
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '0.75rem',
        padding: '0.7rem 0.9rem',
        borderRadius: 'var(--radius)',
        background: 'var(--bg-hover)',
      }}
    >
      <span style={{ fontSize: '1.2rem' }} aria-hidden>{icon}</span>
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{ fontWeight: 600, fontSize: '0.85rem', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {material.title}
        </div>
        <div style={{ display: 'flex', gap: '0.75rem', fontSize: '0.72rem', color: 'var(--text-secondary)', flexWrap: 'wrap' }}>
          <span>{ext.toUpperCase()}</span>
          <span>{formatBytes(material.file_size)}</span>
          <span>{`⬇ ${material.download_count} downloads`}</span>
          <span>{`👁 ${material.view_count} views`}</span>
        </div>
      </div>
      <a
        className="btn btn-ghost btn-sm"
        href={endpoints.materials.downloadUrl(material.id)}
        download={material.original_file_name}
        aria-label={`Download ${material.title}`}
      >
        Download
      </a>
    </div>
  );
};
