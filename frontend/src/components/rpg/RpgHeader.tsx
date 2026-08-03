export const RpgHeader = () => {
  return (
    <header
      style={{
        background: 'linear-gradient(180deg, #1a1a1a 0%, #121212 100%)',
        borderBottom: '2px solid var(--rpg-border, #2a2a2a)',
        padding: '1.25rem 2rem',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        gap: '1rem',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
        {/* Pixel-art trophy + forest banner (emoji-based) */}
        <div
          style={{
            fontSize: '2rem',
            lineHeight: 1,
            filter: 'none',
            imageRendering: 'pixelated',
          }}
          aria-hidden="true"
        >
          🏆🌲
        </div>
        <div>
          <h1
            className="pixel-text"
            style={{
              fontSize: '1.1rem',
              color: '#ff9800',
              margin: 0,
              letterSpacing: '0.04em',
            }}
          >
            RPG WEEKLY PLANNER
          </h1>
          <p
            style={{
              fontSize: '0.7rem',
              color: '#707070',
              margin: '0.25rem 0 0 0',
            }}
          >
            Complete quests. Earn XP. Level up your life.
          </p>
        </div>
      </div>

      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '0.5rem',
          fontSize: '0.65rem',
          color: '#707070',
        }}
      >
        <span>⚡</span>
        <span>Press</span>
        <kbd
          style={{
            background: '#2a2a2a',
            padding: '0.15rem 0.4rem',
            borderRadius: '3px',
            fontSize: '0.6rem',
            color: '#b0b0b0',
            border: '1px solid #3a3a3a',
          }}
        >
          N
        </kbd>
        <span>for quick quest</span>
      </div>
    </header>
  );
};
