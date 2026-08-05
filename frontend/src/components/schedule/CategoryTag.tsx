
interface CategoryTagProps {
  category: string;
  className?: string;
}

const catClassMap: Record<string, string> = {
  School: 'cat-school',
  'Study Time': 'cat-study',
  Break: 'cat-break',
};

export const CategoryTag = ({ category, className = '' }: CategoryTagProps) => {
  const base = catClassMap[category] ?? '';
  return (
    <span className={`badge ${base} ${className}`.trim()} style={{ fontSize: '0.65rem' }}>
      {category}
    </span>
  );
};
