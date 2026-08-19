import { useEffect, useState } from 'react';
import { endpoints } from '../../services/api';
import { ResourceCard } from './ResourceCard';
import type { Resource } from './ResourceCard';

const defaultResources: Resource[] = [
  { id: 'lib', title: 'Library Portal', type: 'link', url: '#', description: 'Access journals and books' },
  { id: 'scholar', title: 'Google Scholar', type: 'link', url: '#', description: 'Research papers & citations' },
  { id: 'drive', title: 'Course Drive', type: 'link', url: '#', description: 'Shared lecture materials' },
  { id: 'github', title: 'Code Repos', type: 'code', url: '#', description: 'Project templates & examples' },
];

interface AcademicResourcesGridProps {
  resources?: Resource[];
}

/** Grid of academic resource cards — derived from KB sources + Classroom when available. */
export const AcademicResourcesGrid = ({ resources }: AcademicResourcesGridProps) => {
  const [items, setItems] = useState<Resource[]>(resources ?? defaultResources);

  useEffect(() => {
    if (resources) {
      setItems(resources);
      return;
    }
    endpoints.courses
      .resources()
      .then((fetched) => {
        if (fetched.length > 0) {
          // Backend already falls back to defaults; coerce null url/description.
          setItems(
            fetched.map((r) => ({
              id: r.id,
              title: r.title,
              type: r.type,
              url: r.url ?? '#',
              description: r.description ?? undefined,
            })),
          );
        }
      })
      .catch(() => {
        // Keep defaults on any failure so the grid never renders empty.
      });
  }, [resources]);

  return (
    <div className="page-section">
      <h2>Academic Resources</h2>
      <div className="resource-grid">
        {items.map((r) => (
          <ResourceCard key={r.id} resource={r} />
        ))}
      </div>
    </div>
  );
};
