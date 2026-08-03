import type { ReactNode } from 'react';
import { RpgHeader } from './RpgHeader';

interface RpgLayoutProps {
  sidebar: ReactNode;
  children: ReactNode;
}

export const RpgLayout = ({ sidebar, children }: RpgLayoutProps) => {
  return (
    <div className="theme-rpg rpg-layout">
      <RpgHeader />
      <div style={{ display: 'flex', flex: 1, marginTop: '73px' }}>
        <aside className="rpg-sidebar">
          {sidebar}
        </aside>
        <main className="rpg-main">
          {children}
        </main>
      </div>
    </div>
  );
};
