import { useCallback, useEffect, useState } from 'react';
import { Header } from '../components/layout/Header';
import { endpoints } from '../services/api';
import type { FlashcardDeck, Note } from '../services/api';

const DIFFICULTIES = [
  { key: 'easy', label: 'Easy', color: 'var(--success)' },
  { key: 'basic', label: 'Basic', color: 'var(--info)' },
  { key: 'medium', label: 'Medium', color: 'var(--warning)' },
  { key: 'hard', label: 'Hard', color: 'var(--danger)' },
  { key: 'olympic', label: 'Olympic', color: '#b07cff' },
] as const;

const diffMeta = (key: string) => DIFFICULTIES.find((d) => d.key === key) ?? DIFFICULTIES[1];

interface GradeResult {
  correct: boolean;
  explanation: string;
}

export const Flashcards = () => {
  const [decks, setDecks] = useState<FlashcardDeck[]>([]);
  const [notes, setNotes] = useState<Note[]>([]);
  const [studyDeck, setStudyDeck] = useState<FlashcardDeck | null>(null);
  const [cardIndex, setCardIndex] = useState(0);
  const [flipped, setFlipped] = useState(false);
  const [writtenMode, setWrittenMode] = useState(false);
  const [writtenAnswer, setWrittenAnswer] = useState('');
  const [grading, setGrading] = useState(false);
  const [gradeResult, setGradeResult] = useState<GradeResult | null>(null);

  const [showNewDeck, setShowNewDeck] = useState(false);
  const [deckName, setDeckName] = useState('');
  const [showAddCard, setShowAddCard] = useState(false);
  const [newFront, setNewFront] = useState('');
  const [newBack, setNewBack] = useState('');
  const [showGenerate, setShowGenerate] = useState(false);
  const [genDifficulty, setGenDifficulty] = useState('basic');
  const [genNoteId, setGenNoteId] = useState('');
  const [genText, setGenText] = useState('');
  const [generating, setGenerating] = useState(false);
  const [genError, setGenError] = useState('');

  const [aiMode, setAiMode] = useState('Offline');
  const [xpEarned, setXpEarned] = useState(0);
  const [dueCounts, setDueCounts] = useState<Record<string, number>>({});
  const [gradingBusy, setGradingBusy] = useState(false);
  const [lastGraded, setLastGraded] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const d = await endpoints.flashcards.list();
      setDecks(d);
      const n = await endpoints.notes.list().catch(() => []);
      setNotes(n);
      const dc = await endpoints.flashcards.dueCounts().catch(() => ({ counts: {} }));
      setDueCounts(dc.counts);
    } catch {
      /* silent */
    }
  }, []);

  useEffect(() => {
    void refresh();
    endpoints.ai
      .health()
      .then((h) => setAiMode(h.available && h.model ? `AI · ${h.model}` : 'Offline'))
      .catch(() => setAiMode('Offline'));
  }, [refresh]);

  const loadDeck = async (id: number) => {
    try {
      const deck = await endpoints.flashcards.get(id);
      setStudyDeck(deck);
      setCardIndex(0);
      setFlipped(false);
      setWrittenMode(false);
      setWrittenAnswer('');
      setGradeResult(null);
    } catch {
      /* silent */
    }
  };

  const handleAddDeck = async () => {
    if (!deckName.trim()) return;
    try {
      await endpoints.flashcards.create({ name: deckName.trim() });
      setDeckName('');
      setShowNewDeck(false);
      void refresh();
    } catch {
      /* silent */
    }
  };

  const handleDeleteDeck = async (id: number) => {
    try {
      await endpoints.flashcards.delete(id);
      void refresh();
    } catch {
      /* silent */
    }
  };

  const handleAddCard = async () => {
    if (!newFront.trim() || !newBack.trim() || !studyDeck) return;
    try {
      await endpoints.flashcards.addCard(studyDeck.id, { front: newFront.trim(), back: newBack.trim(), difficulty: 'basic' });
      setNewFront('');
      setNewBack('');
      setShowAddCard(false);
      void loadDeck(studyDeck.id);
    } catch {
      /* silent */
    }
  };

  const handleGenerate = async () => {
    const source = (genText.trim() || notes.find((n) => String(n.id) === String(genNoteId))?.content || '').trim();
    if (!source) {
      setGenError('Paste some text or pick a note first.');
      return;
    }
    if (!studyDeck) return;
    setGenerating(true);
    setGenError('');
    try {
      const res = await endpoints.ai.flashcards({ content: source, difficulty: genDifficulty });
      const cards = res.cards;
      if (!Array.isArray(cards) || cards.length === 0) throw new Error('AI returned no usable cards');
      for (const c of cards.slice(0, 12)) {
        await endpoints.flashcards.addCard(studyDeck.id, { front: c.front, back: c.back, difficulty: genDifficulty });
      }
      setGenText('');
      setGenNoteId('');
      setShowGenerate(false);
      void loadDeck(studyDeck.id);
    } catch (e) {
      setGenError(e instanceof Error ? e.message : 'Generation failed — try again');
    }
    setGenerating(false);
  };

  const submitWrittenAnswer = async () => {
    if (!writtenAnswer.trim() || !studyDeck) return;
    const card = studyDeck.cards[cardIndex];
    if (!card) return;
    setGrading(true);
    try {
      const res = await endpoints.ai.gradeAnswer({
        question: card.front,
        expected: card.back,
        answer: writtenAnswer,
      });
      setGradeResult({ correct: res.correct, explanation: res.explanation });
      if (res.correct) {
        setXpEarned((x) => x + 5);
        await endpoints.flashcards
          .updateCard(studyDeck.id, card.id, { streak: card.streak + 1 })
          .catch(() => undefined);
      }
    } catch {
      const correct = writtenAnswer.trim().toLowerCase() === (card.back || '').trim().toLowerCase();
      setGradeResult({
        correct,
        explanation: correct ? 'Correct!' : `Couldn't grade automatically — compare with the answer yourself.`,
      });
    }
    setGrading(false);
  };

  const nextCard = () => {
    if (!studyDeck) return;
    setCardIndex((i) => Math.min(studyDeck.cards.length - 1, i + 1));
    setFlipped(false);
    setWrittenAnswer('');
    setGradeResult(null);
  };
  const prevCard = () => {
    setCardIndex((i) => Math.max(0, i - 1));
    setFlipped(false);
    setWrittenAnswer('');
    setGradeResult(null);
  };

  // ── FSRS grading (Idea 52 — vendored py-fsrs) ──
  const gradeButtons = [
    { grade: 0, label: 'Again', color: 'var(--danger)' },
    { grade: 2, label: 'Hard', color: 'var(--warning)' },
    { grade: 3, label: 'Good', color: 'var(--success)' },
    { grade: 5, label: 'Easy', color: 'var(--info)' },
  ] as const;

  const handleGrade = async (grade: number) => {
    if (!studyDeck) return;
    const card = studyDeck.cards[cardIndex];
    if (!card) return;
    setGradingBusy(true);
    setLastGraded(null);
    try {
      const res = await endpoints.flashcards.review(studyDeck.id, card.id, grade);
      const label = gradeButtons.find((g) => g.grade === grade)?.label ?? '';
      setLastGraded(
        `${label} → next review ${res.schedule.interval_days > 0 ? `in ${res.schedule.interval_days}d` : 'today'}`,
      );
      // Wrap to the next card (the graded card is rescheduled away).
      setCardIndex((i) => (i + 1) % studyDeck.cards.length);
      setFlipped(false);
    } catch {
      /* silent */
    } finally {
      setGradingBusy(false);
      void refresh();
    }
  };

  // ── Study mode ──
  if (studyDeck) {
    const cards = studyDeck.cards;
    const card = cards[cardIndex];
    const dMeta = card ? diffMeta(card.difficulty) : null;

    return (
      <div className="fade-in" style={{ maxWidth: 640 }}>
        <Header title="Flashcards" />
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.75rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
          <button type="button" className="btn btn-ghost btn-sm" onClick={() => setStudyDeck(null)}>← Back</button>
          <h2 style={{ fontSize: '1.1rem', fontWeight: 700 }}>{studyDeck.name}</h2>
          <span style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>
            {cards.length ? `${cardIndex + 1} / ${cards.length}` : '0 cards'}
          </span>
          <span style={{ marginLeft: 'auto', display: 'flex', gap: '0.5rem' }}>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => setShowAddCard(true)}>＋ Card</button>
            <button type="button" className="btn btn-ghost btn-sm" onClick={() => setShowGenerate(true)} style={{ color: 'var(--info)' }}>
              ✨ Generate
            </button>
          </span>
        </div>

        {cards.length === 0 ? (
          <div className="card empty-state">
            <div className="empty-icon">🃏</div>
            <div className="empty-title">No cards in this deck yet</div>
            <div className="empty-message">Generate cards from your notes with AI, or add them yourself.</div>
            <div className="empty-action" style={{ display: 'flex', gap: '0.5rem' }}>
              <button type="button" className="btn btn-primary" onClick={() => setShowGenerate(true)}>✨ Generate with AI</button>
              <button type="button" className="btn btn-ghost" onClick={() => setShowAddCard(true)}>＋ Add manually</button>
            </div>
          </div>
        ) : (
          <>
            {/* Progress */}
            <div style={{ height: 5, background: 'var(--bg-hover)', borderRadius: 3, overflow: 'hidden', marginBottom: '1rem' }}>
              <div
                style={{
                  height: '100%',
                  width: `${((cardIndex + 1) / cards.length) * 100}%`,
                  background: 'var(--info)',
                  borderRadius: 3,
                  transition: 'width 0.3s ease',
                }}
              />
            </div>

            {/* Mode toggle */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '0.75rem' }}>
              {dMeta ? (
                <span className="badge" style={{ color: dMeta.color, background: `${dMeta.color}22` }}>{dMeta.label}</span>
              ) : <span />}
              <div style={{ display: 'flex', gap: '0.35rem' }}>
                {[
                  { key: false, label: 'Flip' },
                  { key: true, label: 'Written' },
                ].map((m) => (
                  <button
                    key={String(m.key)}
                    type="button"
                    onClick={() => {
                      setWrittenMode(m.key);
                      setFlipped(false);
                      setWrittenAnswer('');
                      setGradeResult(null);
                    }}
                    className="btn btn-ghost btn-sm"
                    style={writtenMode === m.key ? { color: 'var(--info)', borderColor: 'var(--info)' } : undefined}
                  >
                    {m.label}
                  </button>
                ))}
              </div>
            </div>

            {!writtenMode ? (
              <>
                {/* Card */}
                <div
                  onClick={() => setFlipped((f) => !f)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => e.key === 'Enter' && setFlipped((f) => !f)}
                  style={{
                    background: 'var(--bg-card)',
                    border: `1px solid ${flipped ? 'var(--info)' : 'var(--border)'}`,
                    borderRadius: 20,
                    padding: '3rem 2rem',
                    textAlign: 'center',
                    cursor: 'pointer',
                    minHeight: 220,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexDirection: 'column',
                    gap: '0.75rem',
                    marginBottom: '1.5rem',
                    transition: 'border-color 0.2s ease, box-shadow 0.2s ease',
                    boxShadow: flipped ? '0 0 32px var(--info-muted)' : 'var(--shadow-md)',
                    userSelect: 'none',
                  }}
                >
                  <div style={{ fontSize: '0.65rem', fontWeight: 700, letterSpacing: '0.12em', color: flipped ? 'var(--info)' : 'var(--text-muted)' }}>
                    {flipped ? 'BACK' : 'FRONT'} — click to flip
                  </div>
                  <div style={{ fontSize: '1.1rem', fontWeight: 600, color: flipped ? 'var(--info)' : 'var(--text-primary)', lineHeight: 1.5, whiteSpace: 'pre-wrap' }}>
                    {flipped ? card.back : card.front}
                  </div>
                </div>

                {/* Controls */}
                <div style={{ display: 'flex', gap: '0.6rem', justifyContent: 'center', flexWrap: 'wrap' }}>
                  <button type="button" className="btn btn-ghost" onClick={prevCard} disabled={cardIndex === 0}>← Prev</button>
                  <button type="button" className="btn btn-ghost" onClick={() => setFlipped(false)}>↺ Flip Back</button>
                  <button type="button" className="btn btn-primary" onClick={nextCard} disabled={cardIndex === cards.length - 1}>Next →</button>
                </div>

                {flipped && (
                  <>
                    <div
                      style={{
                        marginTop: '1.1rem',
                        paddingTop: '1.1rem',
                        borderTop: '1px dashed var(--border)',
                        textAlign: 'center',
                      }}
                    >
                      <div style={{ fontSize: '0.65rem', fontWeight: 700, letterSpacing: '0.12em', color: 'var(--text-muted)', marginBottom: '0.5rem' }}>
                        HOW WELL DID YOU KNOW IT?
                      </div>
                      <div style={{ display: 'flex', gap: '0.5rem', justifyContent: 'center', flexWrap: 'wrap' }}>
                        {gradeButtons.map((g) => (
                          <button
                            key={g.label}
                            type="button"
                            className="btn btn-sm"
                            disabled={gradingBusy}
                            onClick={() => void handleGrade(g.grade)}
                            style={{ color: g.color, borderColor: g.color, background: `${g.color}1a` }}
                          >
                            {g.label}
                          </button>
                        ))}
                      </div>
                      {lastGraded && (
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', marginTop: '0.5rem' }}>
                          🧠 {lastGraded}
                        </div>
                      )}
                    </div>
                  </>
                )}
              </>
            ) : (
              <>
                {/* Written question */}
                <div
                  style={{
                    background: 'var(--bg-card)',
                    border: '1px solid var(--border)',
                    borderRadius: 20,
                    padding: '2.25rem 2rem',
                    textAlign: 'center',
                    minHeight: 160,
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    flexDirection: 'column',
                    gap: '1rem',
                    marginBottom: '1.25rem',
                  }}
                >
                  <div style={{ fontSize: '0.65rem', fontWeight: 700, letterSpacing: '0.12em', color: 'var(--text-muted)' }}>QUESTION</div>
                  <div style={{ fontSize: '1.05rem', fontWeight: 600, lineHeight: 1.5 }}>{card.front}</div>
                </div>

                {!gradeResult ? (
                  <>
                    <textarea
                      value={writtenAnswer}
                      onChange={(e) => setWrittenAnswer(e.target.value)}
                      placeholder="Type your answer…"
                      rows={3}
                      disabled={grading}
                      style={{ width: '100%', resize: 'vertical', marginBottom: '0.75rem' }}
                    />
                    <div style={{ display: 'flex', gap: '0.6rem', justifyContent: 'center', marginBottom: '0.5rem' }}>
                      <button type="button" className="btn btn-ghost" onClick={prevCard} disabled={cardIndex === 0}>← Prev</button>
                      <button
                        type="button"
                        className="btn btn-primary"
                        onClick={() => void submitWrittenAnswer()}
                        disabled={!writtenAnswer.trim() || grading}
                      >
                        {grading ? 'Grading…' : 'Submit Answer'}
                      </button>
                    </div>
                  </>
                ) : (
                  <>
                    <div
                      style={{
                        display: 'flex',
                        gap: '0.75rem',
                        alignItems: 'flex-start',
                        background: gradeResult.correct ? 'var(--success-muted)' : 'var(--danger-muted)',
                        border: `1px solid ${gradeResult.correct ? 'var(--success)' : 'var(--danger)'}`,
                        borderRadius: 14,
                        padding: '1rem 1.15rem',
                        marginBottom: '1.15rem',
                      }}
                    >
                      <span style={{ fontSize: '1.1rem' }}>{gradeResult.correct ? '✅' : '❌'}</span>
                      <div>
                        <div style={{ fontWeight: 700, fontSize: '0.85rem', color: gradeResult.correct ? 'var(--success)' : 'var(--danger)', marginBottom: '0.25rem' }}>
                          {gradeResult.correct ? 'Correct! +5 XP' : 'Not quite'}
                        </div>
                        <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>{gradeResult.explanation}</div>
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: '0.6rem', justifyContent: 'center' }}>
                      <button type="button" className="btn btn-ghost" onClick={prevCard} disabled={cardIndex === 0}>← Prev</button>
                      <button type="button" className="btn btn-primary" onClick={nextCard} disabled={cardIndex === cards.length - 1}>Next →</button>
                    </div>
                  </>
                )}
              </>
            )}
          </>
        )}

        {/* Add card modal */}
        {showAddCard && (
          <div className="modal-overlay" onClick={() => setShowAddCard(false)}>
            <div className="modal" onClick={(e) => e.stopPropagation()}>
              <h2 className="modal-title">Add Card</h2>
              <label style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', display: 'block', fontWeight: 600, marginBottom: '0.3rem' }}>Front (question)</label>
              <textarea value={newFront} onChange={(e) => setNewFront(e.target.value)} rows={2} style={{ width: '100%', resize: 'vertical', marginBottom: '0.75rem' }} />
              <label style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', display: 'block', fontWeight: 600, marginBottom: '0.3rem' }}>Back (answer)</label>
              <textarea value={newBack} onChange={(e) => setNewBack(e.target.value)} rows={2} style={{ width: '100%', resize: 'vertical', marginBottom: '1.25rem' }} />
              <div className="modal-actions">
                <button type="button" className="btn btn-ghost" onClick={() => setShowAddCard(false)}>Cancel</button>
                <button type="button" className="btn btn-primary" onClick={() => void handleAddCard()}>Add Card</button>
              </div>
            </div>
          </div>
        )}

        {/* Generate modal */}
        {showGenerate && (
          <div className="modal-overlay" onClick={() => !generating && setShowGenerate(false)}>
            <div className="modal" onClick={(e) => e.stopPropagation()} style={{ width: 'min(480px, 92vw)' }}>
              <h2 className="modal-title">✨ Generate with AI</h2>
              <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginBottom: '1rem' }}>
                {aiMode !== 'Offline' ? `Using ${aiMode} — paste notes or pick one below.` : 'AI is offline — sample cards will be generated.'}
              </p>
              <label style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', display: 'block', fontWeight: 600, marginBottom: '0.4rem' }}>Difficulty</label>
              <div style={{ display: 'flex', gap: '0.35rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
                {DIFFICULTIES.map((d) => (
                  <button
                    key={d.key}
                    type="button"
                    onClick={() => setGenDifficulty(d.key)}
                    className="btn btn-sm"
                    style={
                      genDifficulty === d.key
                        ? { color: d.color, borderColor: d.color, background: `${d.color}22` }
                        : undefined
                    }
                  >
                    {d.label}
                  </button>
                ))}
              </div>
              {notes.length > 0 && (
                <>
                  <label style={{ fontSize: '0.7rem', color: 'var(--text-secondary)', display: 'block', fontWeight: 600, marginBottom: '0.4rem' }}>From a note (optional)</label>
                  <select value={genNoteId} onChange={(e) => setGenNoteId(e.target.value)} style={{ width: '100%', marginBottom: '0.75rem' }}>
                    <option value="">— Paste text instead —</option>
                    {notes.map((n) => (
                      <option key={n.id} value={n.id}>{n.title || 'Untitled'}</option>
                    ))}
                  </select>
                </>
              )}
              {!genNoteId && (
                <textarea
                  value={genText}
                  onChange={(e) => setGenText(e.target.value)}
                  placeholder="Paste study material to generate cards from…"
                  rows={5}
                  style={{ width: '100%', resize: 'vertical', marginBottom: '0.75rem' }}
                />
              )}
              {genError && <p style={{ fontSize: '0.75rem', color: 'var(--danger)', marginBottom: '0.75rem' }}>{genError}</p>}
              <div className="modal-actions">
                <button type="button" className="btn btn-ghost" onClick={() => setShowGenerate(false)} disabled={generating}>Cancel</button>
                <button type="button" className="btn btn-primary" onClick={() => void handleGenerate()} disabled={generating}>
                  {generating ? 'Generating…' : '✨ Generate 8 Cards'}
                </button>
              </div>
            </div>
          </div>
        )}
      </div>
    );
  }

  // ── Deck list ──
  return (
    <div className="fade-in">
      <Header title="Flashcards" />
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '1.5rem' }}>
        <button type="button" className="btn btn-primary" onClick={() => setShowNewDeck(true)}>＋ New Deck</button>
      </div>
      {xpEarned > 0 && (
        <div className="card" style={{ marginBottom: '1rem', borderColor: 'var(--success)' }}>
          🎉 Session XP earned this visit: <strong style={{ color: 'var(--success)' }}>+{xpEarned}</strong>
        </div>
      )}

      {decks.length === 0 ? (
        <div className="card empty-state">
          <div className="empty-icon">🃏</div>
          <div className="empty-title">No flashcard decks yet</div>
          <div className="empty-message">Create a deck, then generate cards from your notes with AI.</div>
          <div className="empty-action">
            <button type="button" className="btn btn-primary" onClick={() => setShowNewDeck(true)}>Create First Deck</button>
          </div>
        </div>
      ) : (
        <div className="card-grid">
          {decks.map((d) => (
            <div key={d.id} className="card" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
              <div style={{ fontSize: '1.5rem' }}>🃏</div>
              <div style={{ fontWeight: 600, fontSize: '0.9rem', display: 'flex', alignItems: 'center', gap: '0.5rem', flexWrap: 'wrap' }}>
                {d.name}
                {(dueCounts[d.id] ?? 0) > 0 && (
                  <span className="badge" style={{ color: 'var(--info)', background: 'var(--info-muted)', fontSize: '0.62rem' }}>
                    ⏳ {dueCounts[d.id]} due
                  </span>
                )}
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>{d.card_count} cards</div>
              <div style={{ display: 'flex', gap: '0.5rem' }}>
                <button type="button" className="btn btn-primary btn-sm" style={{ flex: 1 }} onClick={() => void loadDeck(d.id)}>
                  Study
                </button>
                <button
                  type="button"
                  className="btn btn-ghost btn-sm"
                  aria-label={`Delete ${d.name}`}
                  style={{ color: 'var(--danger)' }}
                  onClick={() => void handleDeleteDeck(d.id)}
                >
                  ✕
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {/* New deck modal */}
      {showNewDeck && (
        <div className="modal-overlay" onClick={() => setShowNewDeck(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h2 className="modal-title">New Deck</h2>
            <input
              value={deckName}
              onChange={(e) => setDeckName(e.target.value)}
              placeholder="e.g. Biology Chapter 3"
              onKeyDown={(e) => e.key === 'Enter' && void handleAddDeck()}
              style={{ width: '100%', marginBottom: '1.25rem' }}
            />
            <div className="modal-actions">
              <button type="button" className="btn btn-ghost" onClick={() => setShowNewDeck(false)}>Cancel</button>
              <button type="button" className="btn btn-primary" onClick={() => void handleAddDeck()}>Create Deck</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
