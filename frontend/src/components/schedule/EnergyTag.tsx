interface EnergyTagProps {
  energy: string;
}

const eClassMap: Record<string, string> = {
  High: 'e-high',
  Medium: 'e-medium',
  Low: 'e-low',
};

export const EnergyTag = ({ energy }: EnergyTagProps) => {
  const base = eClassMap[energy] ?? '';
  return (
    <span className={`badge ${base}`.trim()} style={{ fontSize: '0.65rem' }}>
      {energy}
    </span>
  );
};
