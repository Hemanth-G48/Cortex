import { useState } from 'react'
import { Layers, Plus, ArrowLeft, ArrowRight, RotateCcw, Trash2, Sparkles, PenLine, Check, X as XIcon, AlertTriangle, Loader2 } from 'lucide-react'
import { useFlashcardsStore, useNotesStore, useXPStore } from '../stores'
import { C, fonts, tint, inputStyle, btnPrimary, btnGhost, iconBox, chip } from '../utils/theme'
import { PageHeader, Empty } from '../components/ui'
import { generateAI, aiAvailable, aiModeLabel } from '../utils/ai'

const DIFFICULTIES = [
  { key: 'easy', label: 'Easy', color: C.green },
  { key: 'basic', label: 'Basic', color: C.blue },
  { key: 'medium', label: 'Medium', color: C.orange },
  { key: 'hard', label: 'Hard', color: C.pink },
  { key: 'olympic', label: 'Olympic', color: C.purple },
]
const DIFFICULTY_PROMPT = {
  easy: 'very easy, recall-level basics a beginner would know',
  basic: 'straightforward, fundamental concepts',
  medium: 'moderately challenging, requires real understanding',
  hard: 'hard, requires connecting multiple concepts',
  olympic: 'olympiad-style — the hardest, most advanced questions on this topic, the kind used in academic competitions',
}
const diffMeta = (key) => DIFFICULTIES.find(d => d.key === key) || DIFFICULTIES[1]

function parseJSONBlock(raw, opener = '[', closer = ']') {
  const start = raw.indexOf(opener)
  const end = raw.lastIndexOf(closer)
  if (start === -1 || end === -1) return null
  try { return JSON.parse(raw.slice(start, end + 1)) } catch { return null }
}

function Modal({ open, onClose, children }) {
  if (!open) return null
  return (
    <div onClick={onClose} style={{
      position: 'fixed', inset: 0, background: 'rgba(4,6,10,0.85)',
      zIndex: 100, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 16,
    }}>
      <div onClick={e => e.stopPropagation()} className="page-enter" style={{
        background: C.card,
        border: `1px solid ${C.border}`, borderRadius: 18, padding: 28, width: 'min(480px,92vw)',
        maxHeight: '90vh', overflowY: 'auto',
        boxShadow: '0 24px 64px rgba(0,0,0,0.6)',
      }}>
        {children}
      </div>
    </div>
  )
}

export default function Flashcards() {
  const { decks, addDeck, deleteDeck, addCard } = useFlashcardsStore()
  const { notes } = useNotesStore()
  const { addXP } = useXPStore()
  const [studyDeck, setStudyDeck] = useState(null)
  const [cardIndex, setCardIndex] = useState(0)
  const [flipped, setFlipped] = useState(false)
  const [showModal, setShowModal] = useState(false)
  const [deckName, setDeckName] = useState('')
  const [showAddCard, setShowAddCard] = useState(false)
  const [newFront, setNewFront] = useState('')
  const [newBack, setNewBack] = useState('')
  const [showGenerate, setShowGenerate] = useState(false)
  const [genDifficulty, setGenDifficulty] = useState('basic')
  const [genNoteId, setGenNoteId] = useState('')
  const [genText, setGenText] = useState('')
  const [generating, setGenerating] = useState(false)
  const [genError, setGenError] = useState('')
  const [writtenMode, setWrittenMode] = useState(false)
  const [writtenAnswer, setWrittenAnswer] = useState('')
  const [grading, setGrading] = useState(false)
  const [gradeResult, setGradeResult] = useState(null) // { correct, explanation }

  const deck = studyDeck ? (decks || []).find(d => d.id === studyDeck) : null
  const cards = deck?.cards || []
  const card = cards[cardIndex]

  const handleAddDeck = () => {
    if (!deckName.trim()) return
    addDeck({ id: Date.now().toString(), name: deckName, cards: [], createdAt: new Date().toISOString() })
    setDeckName('')
    setShowModal(false)
  }

  const handleAddCard = () => {
    if (!newFront.trim() || !newBack.trim() || !deck) return
    addCard(deck.id, { front: newFront.trim(), back: newBack.trim(), difficulty: 'basic' })
    setNewFront(''); setNewBack(''); setShowAddCard(false)
  }

  const handleGenerate = async () => {
    const note = (notes || []).find(n => n.id === genNoteId)
    const source = (genText.trim() || note?.content || '').trim()
    if (!source) { setGenError('Paste some text or pick a note first.'); return }
    if (!aiAvailable()) { setGenError("This browser can't run AI (needs WebGPU) — add a Gemini key in Settings, or use Chrome/Edge."); return }
    setGenerating(true); setGenError('')
    try {
      const prompt = `From the following study material, write 8 high-quality flashcard question/answer pairs at a ${DIFFICULTY_PROMPT[genDifficulty]} difficulty level. Return ONLY a JSON array, no markdown, no explanation: [{"front":"question here","back":"answer here"}, ...]\n\nMaterial:\n${source.slice(0, 4000)}`
      const raw = await generateAI(prompt, { maxOutputTokens: 1600 })
      const cardsOut = raw ? parseJSONBlock(raw) : null
      if (!Array.isArray(cardsOut) || cardsOut.length === 0) throw new Error('AI returned no usable cards')
      cardsOut.forEach(c => {
        if (c?.front && c?.back) addCard(deck.id, { front: c.front, back: c.back, difficulty: genDifficulty })
      })
      setGenText(''); setGenNoteId(''); setShowGenerate(false)
    } catch (e) {
      setGenError(e?.message || 'Generation failed — try again')
    }
    setGenerating(false)
  }

  const submitWrittenAnswer = async () => {
    if (!writtenAnswer.trim() || !card) return
    setGrading(true)
    let result
    try {
      const exactFallback = () => {
        const correct = writtenAnswer.trim().toLowerCase() === (card.back || '').trim().toLowerCase()
        return { correct, explanation: correct ? 'Correct!' : `The correct answer was: ${card.back}` }
      }
      if (!aiAvailable()) {
        result = exactFallback()
      } else {
        const prompt = `You are grading a student's flashcard answer. Question: "${card.front}"\nExpected answer: "${card.back}"\nStudent's answer: "${writtenAnswer}"\n\nJudge if the student's answer is correct — accept answers that are substantively correct even if worded differently. Return ONLY JSON, no markdown: {"correct": true or false, "explanation": "one short sentence explaining why, and the correct answer if they got it wrong"}`
        const raw = await generateAI(prompt, { maxOutputTokens: 300 })
        const parsed = raw ? parseJSONBlock(raw, '{', '}') : null
        result = (parsed && typeof parsed.correct === 'boolean') ? parsed : exactFallback()
      }
    } catch {
      result = { correct: false, explanation: "Couldn't grade automatically — compare with the answer yourself." }
    }
    setGradeResult(result)
    if (result.correct) addXP(5)
    setGrading(false)
  }

  const nextCard = () => {
    setCardIndex(i => Math.min(cards.length - 1, i + 1))
    setFlipped(false); setWrittenAnswer(''); setGradeResult(null)
  }
  const prevCard = () => {
    setCardIndex(i => Math.max(0, i - 1))
    setFlipped(false); setWrittenAnswer(''); setGradeResult(null)
  }

  if (deck) {
    const dMeta = card?.difficulty ? diffMeta(card.difficulty) : null
    return (
      <div style={{ fontFamily: fonts.body, color: C.text, maxWidth: 620, margin: '0 auto' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 20, flexWrap: 'wrap' }}>
          <button onClick={() => { setStudyDeck(null); setCardIndex(0); setFlipped(false); setWrittenMode(false) }} style={{ ...btnGhost, padding: '7px 14px', color: C.textMuted }}>
            <ArrowLeft size={14} /> Back
          </button>
          <h2 style={{ fontFamily: fonts.heading, fontSize: 20, fontWeight: 700, color: C.text }}>{deck.name}</h2>
          <span style={{ fontSize: 12, color: C.textMuted, fontFamily: fonts.heading, fontWeight: 600 }}>
            {cards.length ? `${cardIndex + 1} / ${cards.length}` : '0 cards'}
          </span>
          <div style={{ marginLeft: 'auto', display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            <button onClick={() => setShowAddCard(true)} style={{ ...btnGhost, padding: '7px 12px', fontSize: 12, color: C.textMuted }}>
              <Plus size={13} /> Add Card
            </button>
            <button onClick={() => setShowGenerate(true)} style={{ ...btnGhost, padding: '7px 12px', fontSize: 12, color: C.purple, borderColor: tint(C.purple, 0.35) }}>
              <Sparkles size={13} /> Generate with AI
            </button>
          </div>
        </div>

        {cards.length === 0 ? (
          <div style={{
            background: C.card,
            border: `1px solid ${C.border}`, borderRadius: 16,
          }}>
            <Empty
              icon={Layers}
              accent={C.purple}
              title="No cards in this deck yet"
              description="Generate cards from your notes with AI, or add them yourself."
              action={() => setShowGenerate(true)}
              actionLabel="Generate with AI"
            />
            <div style={{ textAlign: 'center', paddingBottom: 32 }}>
              <button onClick={() => setShowAddCard(true)} style={{ ...btnGhost, color: C.textMuted }}>
                <Plus size={13} /> Add a card manually
              </button>
            </div>
          </div>
        ) : (
          <>
            {/* Progress bar */}
            <div style={{ height: 5, background: tint(C.blue, 0.1), borderRadius: 3, overflow: 'hidden', marginBottom: 16 }}>
              <div style={{
                height: '100%', width: `${((cardIndex + 1) / cards.length) * 100}%`,
                background: C.blueDark,
                borderRadius: 3, transition: 'width 0.3s ease',
              }} />
            </div>

            {/* Mode toggle */}
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
              {dMeta ? (
                <span style={{ ...chip(dMeta.color), textTransform: 'capitalize' }}>{dMeta.label}</span>
              ) : <span />}
              <div style={{ display: 'flex', gap: 6 }}>
                {[{ key: false, label: 'Flip', icon: RotateCcw }, { key: true, label: 'Written', icon: PenLine }].map(m => (
                  <button key={String(m.key)} onClick={() => { setWrittenMode(m.key); setFlipped(false); setWrittenAnswer(''); setGradeResult(null) }} style={{
                    display: 'flex', alignItems: 'center', gap: 5, padding: '6px 12px', borderRadius: 999,
                    border: `1px solid ${writtenMode === m.key ? tint(C.blue, 0.4) : C.border}`,
                    background: writtenMode === m.key ? tint(C.blue, 0.12) : 'transparent',
                    color: writtenMode === m.key ? C.blue : C.textMuted,
                    cursor: 'pointer', fontFamily: fonts.heading, fontSize: 11, fontWeight: 700,
                  }}><m.icon size={11} /> {m.label}</button>
                ))}
              </div>
            </div>

            {!writtenMode ? (
              <>
                {/* Card */}
                <div onClick={() => setFlipped(f => !f)} style={{
                  background: C.card,
                  border: `1px solid ${flipped ? tint(C.purple, 0.5) : C.border}`,
                  borderRadius: 20, padding: '48px 32px', textAlign: 'center', cursor: 'pointer',
                  minHeight: 220, display: 'flex', alignItems: 'center', justifyContent: 'center',
                  flexDirection: 'column', gap: 12, marginBottom: 24,
                  transition: 'border-color 0.2s ease, box-shadow 0.2s ease',
                  boxShadow: flipped ? `0 0 40px ${tint(C.purple, 0.15)}` : '0 8px 24px rgba(0,0,0,0.3)',
                  userSelect: 'none',
                }}>
                  <div style={{
                    fontSize: 11, color: flipped ? C.purple : C.textFaint, fontFamily: fonts.heading,
                    fontWeight: 700, letterSpacing: '0.12em', marginBottom: 8,
                  }}>
                    {flipped ? 'BACK' : 'FRONT'} — click to flip
                  </div>
                  <div style={{ fontSize: 19, fontWeight: 600, color: flipped ? C.purple : C.text, lineHeight: 1.5 }}>
                    {flipped ? card.back : card.front}
                  </div>
                </div>

                {/* Controls */}
                <div style={{ display: 'flex', gap: 10, justifyContent: 'center', flexWrap: 'wrap' }}>
                  <button onClick={prevCard} disabled={cardIndex === 0}
                    style={{ ...btnGhost, color: cardIndex === 0 ? C.textFaint : C.text, cursor: cardIndex === 0 ? 'not-allowed' : 'pointer' }}
                  ><ArrowLeft size={14} /> Prev</button>
                  <button onClick={() => setFlipped(false)} style={{ ...btnGhost, color: C.textMuted }}>
                    <RotateCcw size={13} /> Flip Back
                  </button>
                  <button onClick={nextCard} disabled={cardIndex === cards.length - 1}
                    style={{ ...btnGhost, color: cardIndex === cards.length - 1 ? C.textFaint : C.text, cursor: cardIndex === cards.length - 1 ? 'not-allowed' : 'pointer' }}
                  >Next <ArrowRight size={14} /></button>
                </div>
              </>
            ) : (
              <>
                {/* Written question */}
                <div style={{
                  background: C.card, border: `1px solid ${C.border}`, borderRadius: 20,
                  padding: '36px 32px', textAlign: 'center', minHeight: 220,
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  flexDirection: 'column', gap: 16, marginBottom: 20,
                }}>
                  <div style={{ fontSize: 11, color: C.textFaint, fontFamily: fonts.heading, fontWeight: 700, letterSpacing: '0.12em' }}>QUESTION</div>
                  <div style={{ fontSize: 18, fontWeight: 600, color: C.text, lineHeight: 1.5 }}>{card.front}</div>
                </div>

                {!gradeResult ? (
                  <>
                    <textarea
                      value={writtenAnswer}
                      onChange={e => setWrittenAnswer(e.target.value)}
                      placeholder="Type your answer…"
                      rows={3}
                      disabled={grading}
                      style={{ ...inputStyle, resize: 'vertical', marginBottom: 14 }}
                      onFocus={e => { e.target.style.borderColor = C.blueDark }}
                      onBlur={e => { e.target.style.borderColor = C.border }}
                    />
                    {!aiAvailable() && (
                      <div style={{ display: 'flex', gap: 8, alignItems: 'flex-start', fontSize: 12, color: C.orange, marginBottom: 14 }}>
                        <AlertTriangle size={13} style={{ flexShrink: 0, marginTop: 1 }} />
                        No AI available in this browser — answers will only be checked for an exact match.
                      </div>
                    )}
                    <div style={{ display: 'flex', gap: 10, justifyContent: 'center' }}>
                      <button onClick={prevCard} disabled={cardIndex === 0} style={{ ...btnGhost, color: cardIndex === 0 ? C.textFaint : C.text }}>
                        <ArrowLeft size={14} /> Prev
                      </button>
                      <button onClick={submitWrittenAnswer} disabled={!writtenAnswer.trim() || grading} style={{ ...btnPrimary, opacity: !writtenAnswer.trim() || grading ? 0.6 : 1 }}>
                        {grading ? <Loader2 size={14} className="spin" /> : <Check size={14} />} {grading ? (aiAvailable() ? `Grading with ${aiModeLabel()}…` : 'Checking…') : 'Submit Answer'}
                      </button>
                    </div>
                  </>
                ) : (
                  <>
                    <div style={{
                      display: 'flex', gap: 12, alignItems: 'flex-start',
                      background: tint(gradeResult.correct ? C.greenDark : C.pink, 0.08),
                      border: `1px solid ${tint(gradeResult.correct ? C.greenDark : C.pink, 0.35)}`,
                      borderRadius: 14, padding: '16px 18px', marginBottom: 18,
                    }}>
                      {gradeResult.correct ? <Check size={18} color={C.green} style={{ flexShrink: 0 }} /> : <XIcon size={18} color={C.pink} style={{ flexShrink: 0 }} />}
                      <div>
                        <div style={{ fontFamily: fonts.heading, fontWeight: 700, fontSize: 14, color: gradeResult.correct ? C.green : C.pink, marginBottom: 4 }}>
                          {gradeResult.correct ? 'Correct! +5 XP' : 'Not quite'}
                        </div>
                        <div style={{ fontSize: 13, color: C.textMuted, lineHeight: 1.5 }}>{gradeResult.explanation}</div>
                      </div>
                    </div>
                    <div style={{ display: 'flex', gap: 10, justifyContent: 'center' }}>
                      <button onClick={prevCard} disabled={cardIndex === 0} style={{ ...btnGhost, color: cardIndex === 0 ? C.textFaint : C.text }}>
                        <ArrowLeft size={14} /> Prev
                      </button>
                      <button onClick={nextCard} disabled={cardIndex === cards.length - 1} style={btnPrimary}>
                        Next <ArrowRight size={14} />
                      </button>
                    </div>
                  </>
                )}
              </>
            )}
          </>
        )}

        {/* Add card modal */}
        <Modal open={showAddCard} onClose={() => setShowAddCard(false)}>
          <h2 style={{ fontFamily: fonts.heading, fontSize: 18, fontWeight: 700, color: C.text, marginBottom: 18 }}>Add Card</h2>
          <label style={{ display: 'block', fontSize: 12, color: C.textMuted, marginBottom: 6, fontWeight: 700 }}>Front (question)</label>
          <textarea value={newFront} onChange={e => setNewFront(e.target.value)} rows={2} style={{ ...inputStyle, resize: 'vertical', marginBottom: 14 }} />
          <label style={{ display: 'block', fontSize: 12, color: C.textMuted, marginBottom: 6, fontWeight: 700 }}>Back (answer)</label>
          <textarea value={newBack} onChange={e => setNewBack(e.target.value)} rows={2} style={{ ...inputStyle, resize: 'vertical', marginBottom: 20 }} />
          <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
            <button onClick={() => setShowAddCard(false)} style={{ ...btnGhost, color: C.textMuted }}>Cancel</button>
            <button onClick={handleAddCard} style={btnPrimary}>Add Card</button>
          </div>
        </Modal>

        {/* Generate with AI modal */}
        <Modal open={showGenerate} onClose={() => !generating && setShowGenerate(false)}>
          <h2 style={{ fontFamily: fonts.heading, fontSize: 18, fontWeight: 700, color: C.text, marginBottom: 6 }}>Generate with AI</h2>
          <p style={{ fontSize: 12, color: C.textMuted, marginBottom: 16 }}>
            {aiAvailable() ? `Using ${aiModeLabel()} — paste notes or pick one below.` : "This browser can't run AI — add a Gemini key in Settings, or use Chrome/Edge for free on-device AI."}
          </p>
          <label style={{ display: 'block', fontSize: 12, color: C.textMuted, marginBottom: 6, fontWeight: 700 }}>Difficulty</label>
          <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginBottom: 16 }}>
            {DIFFICULTIES.map(d => (
              <button key={d.key} onClick={() => setGenDifficulty(d.key)} style={{
                padding: '6px 14px', borderRadius: 999,
                border: `1px solid ${genDifficulty === d.key ? tint(d.color, 0.5) : C.border}`,
                background: genDifficulty === d.key ? tint(d.color, 0.14) : 'transparent',
                color: genDifficulty === d.key ? d.color : C.textMuted,
                cursor: 'pointer', fontFamily: fonts.heading, fontSize: 12, fontWeight: 700,
              }}>{d.label}</button>
            ))}
          </div>
          {(notes || []).length > 0 && (
            <>
              <label style={{ display: 'block', fontSize: 12, color: C.textMuted, marginBottom: 6, fontWeight: 700 }}>From a note (optional)</label>
              <select value={genNoteId} onChange={e => setGenNoteId(e.target.value)} style={{ ...inputStyle, marginBottom: 14 }}>
                <option value=''>— Paste text instead —</option>
                {(notes || []).map(n => (<option key={n.id} value={n.id}>{n.title || 'Untitled'}</option>))}
              </select>
            </>
          )}
          {!genNoteId && (
            <textarea
              value={genText} onChange={e => setGenText(e.target.value)}
              placeholder="Paste study material to generate cards from…"
              rows={5}
              style={{ ...inputStyle, resize: 'vertical', marginBottom: 14 }}
            />
          )}
          {genError && <p style={{ fontSize: 12, color: C.pink, marginBottom: 12 }}>{genError}</p>}
          <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
            <button onClick={() => setShowGenerate(false)} disabled={generating} style={{ ...btnGhost, color: C.textMuted }}>Cancel</button>
            <button onClick={handleGenerate} disabled={generating} style={{ ...btnPrimary, opacity: generating ? 0.7 : 1 }}>
              {generating ? <Loader2 size={14} className="spin" /> : <Sparkles size={14} />} {generating ? 'Generating…' : 'Generate 8 Cards'}
            </button>
          </div>
        </Modal>
      </div>
    )
  }

  return (
    <div style={{ fontFamily: fonts.body, color: C.text, maxWidth: 920, margin: '0 auto' }}>
      <PageHeader
        icon={Layers}
        accent={C.purple}
        title="Flashcards"
        subtitle="Study decks for every subject"
        actions={
          <button onClick={() => setShowModal(true)} style={btnPrimary}>
            <Plus size={15} /> New Deck
          </button>
        }
      />

      {(!decks || decks.length === 0) ? (
        <div style={{
          background: C.card,
          border: `1px solid ${C.border}`, borderRadius: 16,
        }}>
          <Empty
            icon={Layers}
            accent={C.purple}
            title="No flashcard decks yet"
            description="Create a deck, then generate cards from your notes with AI — or add them yourself."
            action={() => setShowModal(true)}
            actionLabel="Create First Deck"
          />
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill,minmax(230px,1fr))', gap: 14 }}>
          {decks.map(d => (
            <div key={d.id} className="hover-lift" style={{
              background: C.card,
              border: `1px solid ${C.border}`, borderRadius: 14, padding: 20,
            }}>
              <div style={{ ...iconBox(C.purple, 42), marginBottom: 14 }}>
                <Layers size={20} strokeWidth={2.2} />
              </div>
              <div style={{ fontFamily: fonts.heading, fontSize: 15, fontWeight: 700, color: C.text, marginBottom: 4 }}>{d.name}</div>
              <div style={{ fontSize: 12, color: C.textMuted, marginBottom: 16 }}>{(d.cards || []).length} cards</div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button onClick={() => { setStudyDeck(d.id); setCardIndex(0); setFlipped(false) }} style={{ ...btnPrimary, flex: 1, padding: '8px 0', fontSize: 12 }}>
                  Study
                </button>
                <button onClick={e => { e.stopPropagation(); deleteDeck(d.id) }} aria-label="Delete deck" style={{
                  padding: '8px 11px', borderRadius: 10, border: `1px solid ${C.border}`,
                  background: 'transparent', color: C.textFaint, cursor: 'pointer', display: 'flex', alignItems: 'center',
                  transition: 'color 0.15s ease',
                }}
                  onMouseEnter={e => e.currentTarget.style.color = C.pink}
                  onMouseLeave={e => e.currentTarget.style.color = C.textFaint}
                ><Trash2 size={13} /></button>
              </div>
            </div>
          ))}
        </div>
      )}

      <Modal open={showModal} onClose={() => setShowModal(false)}>
        <h2 style={{ fontFamily: fonts.heading, fontSize: 18, fontWeight: 700, color: C.text, marginBottom: 18 }}>New Deck</h2>
        <label style={{ display: 'block', fontSize: 12, color: C.textMuted, marginBottom: 6, fontWeight: 700 }}>Deck Name</label>
        <input
          value={deckName} onChange={e => setDeckName(e.target.value)}
          placeholder="e.g. Biology Chapter 3"
          onKeyDown={e => e.key === 'Enter' && handleAddDeck()}
          style={{ ...inputStyle, marginBottom: 20 }}
          onFocus={e => { e.target.style.borderColor = C.blueDark }}
          onBlur={e => { e.target.style.borderColor = C.border }}
        />
        <div style={{ display: 'flex', gap: 10, justifyContent: 'flex-end' }}>
          <button onClick={() => setShowModal(false)} style={{ ...btnGhost, color: C.textMuted }}>Cancel</button>
          <button onClick={handleAddDeck} style={btnPrimary}>Create Deck</button>
        </div>
      </Modal>
    </div>
  )
}
