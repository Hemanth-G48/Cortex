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

/** Grid of academic resource cards */
export const AcademicResourcesGrid = ({ resources }: AcademicResourcesGridProps) => {
  const items = resources ?? defaultResources;

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
