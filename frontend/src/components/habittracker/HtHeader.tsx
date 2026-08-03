/** Cinematic 3D pixel-art living-room banner + app title overlay (Phases 41/49). */
export const HtHeader = () => (
  <header className="ht-header">
    <div className="ht-header-scene" aria-hidden="true">
      <div className="ht-pixel-crate" />
      <div className="ht-pixel-crate" />
      <div className="ht-pixel-crate" />
    </div>
    <div className="ht-header-inner">
      <span className="ht-header-eyebrow">⚔️ Student OS · Gamified Module</span>
      <h1>Gamified Habit Tracker</h1>
      <p className="ht-header-sub">
        Level up your life — complete good habits to earn gold, admit your bad habits
        to own the penalty. Keep going, player!
      </p>
    </div>
  </header>
);
