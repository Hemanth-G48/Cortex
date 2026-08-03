import { resourceIcon, bannerGradient } from '../../utils/placeholders';

interface Resource {
  id: string;
  title: string;
  type: string;
  url: string;
  description?: string;
}

interface ResourceCardProps {
  resource: Resource;
}

/** Resource card with themed gradient background */
export const ResourceCard = ({ resource }: ResourceCardProps) => {
  const hue = Math.abs(resource.title.split('').reduce((a, c) => a + c.charCodeAt(0), 0)) % 360;

  return (
    <a
      href={resource.url}
      target="_blank"
      rel="noopener noreferrer"
      className="resource-card"
      style={{ background: bannerGradient(hue) }}
    >
      <div className="resource-card-icon">{resourceIcon(resource.type)}</div>
      <div className="resource-card-body">
        <div className="resource-card-title">{resource.title}</div>
        {resource.description && (
          <div className="resource-card-desc">{resource.description}</div>
        )}
      </div>
    </a>
  );
};

export type { Resource };
