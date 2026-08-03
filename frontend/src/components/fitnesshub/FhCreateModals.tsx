import { useState } from 'react';
import { endpoints } from '../../services/api';
import { useToast } from '../../hooks/useToast';
import type { FhQuickActionKind } from './FhQuickActions';

interface Props {
  kind: FhQuickActionKind;
  onClose: () => void;
  onCreated: () => void;
}

/** Quick-Action create modals (Phase 71): Exercise / Expense / Muscle Group / Weight Goal / Habit. */
export const FhCreateModal = ({ kind, onClose, onCreated }: Props) => {
  const { toast } = useToast();
  const [saving, setSaving] = useState(false);
  const [name, setName] = useState('');
  const [cost, setCost] = useState('');
  const [category, setCategory] = useState('Supplement');
  const [bodyPart, setBodyPart] = useState('Upper');
  const [sets, setSets] = useState('3');
  const [reps, setReps] = useState('10');
  const [weight, setWeight] = useState('');
  const [initial, setInitial] = useState('');
  const [current, setCurrent] = useState('');
  const [target, setTarget] = useState('');

  const titles: Record<FhQuickActionKind, string> = {
    exercise: 'Add Exercise',
    expense: 'Add New Expense',
    'muscle-group': 'Add Muscle Group',
    habit: 'Add New Habit',
    'weight-goal': 'Add New Weight Goal',
  };

  const submit = async () => {
    if (saving) return;
    setSaving(true);
    try {
      if (kind === 'exercise') {
        await endpoints.fitnessHub.createExercise({
          name: name.trim(),
          muscle_group_id: null,
          sets: Number(sets) || 3,
          reps: Number(reps) || 10,
          weight: Number(weight) || 0,
          user_id: 1,
        });
      } else if (kind === 'expense') {
        if (!name.trim() || !cost) throw new Error('Title and cost are required');
        await endpoints.fitnessHub.createExpense({
          title: name.trim(),
          cost: Number(cost),
          category,
          date: new Date().toISOString().slice(0, 10),
          user_id: 1,
        });
      } else if (kind === 'muscle-group') {
        await endpoints.fitnessHub.createMuscleGroup({
          name: name.trim(),
          body_part: bodyPart,
          sort_order: 99,
          user_id: 1,
        });
      } else if (kind === 'habit') {
        if (!name.trim()) throw new Error('Name is required');
        await endpoints.habits.create({
          name: name.trim(),
          habit_type: 'good',
          xp_reward: 30,
          xp_penalty: 20,
          frequency: 'daily',
          target_count: 1,
          user_id: 1,
        });
      } else if (kind === 'weight-goal') {
        await endpoints.fitnessHub.updateWeightGoal(1, {
          initial: Number(initial),
          current: Number(current),
          target: Number(target),
        });
      }
      toast(`Created ${titles[kind]}! ✅`, 'success');
      onCreated();
      onClose();
    } catch (e) {
      toast(e instanceof Error ? e.message : 'Could not create', 'error');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div
        className="modal"
        role="dialog"
        aria-modal="true"
        aria-label={titles[kind]}
        onClick={(e) => e.stopPropagation()}
        style={{ minWidth: 360 }}
      >
        <div className="modal-title">{titles[kind]}</div>
        <div className="fh-modal-body">
          {(kind === 'exercise' || kind === 'expense' || kind === 'muscle-group' || kind === 'habit') && (
            <div className="fh-field">
              <label htmlFor="fh-name">Name</label>
              <input
                id="fh-name"
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder={
                  kind === 'expense' ? 'e.g. Whey Protein' :
                  kind === 'muscle-group' ? 'e.g. Neck' :
                  kind === 'habit' ? 'e.g. Morning Run' :
                  'e.g. Squat'
                }
                autoFocus
                onKeyDown={(e) => { if (e.key === 'Enter') void submit(); if (e.key === 'Escape') onClose(); }}
              />
            </div>
          )}

          {kind === 'expense' && (
            <>
              <div className="fh-field">
                <label htmlFor="fh-cost">Cost ($)</label>
                <input id="fh-cost" type="number" min={0} step="0.01" value={cost} onChange={(e) => setCost(e.target.value)} />
              </div>
              <div className="fh-field">
                <label htmlFor="fh-category">Category</label>
                <select id="fh-category" value={category} onChange={(e) => setCategory(e.target.value)}>
                  <option value="Supplement">Supplement</option>
                  <option value="Equipment">Equipment</option>
                  <option value="Gym">Gym</option>
                </select>
              </div>
            </>
          )}

          {kind === 'muscle-group' && (
            <div className="fh-field">
              <label htmlFor="fh-body-part">Body Part</label>
              <select id="fh-body-part" value={bodyPart} onChange={(e) => setBodyPart(e.target.value)}>
                <option value="Upper">Upper</option>
                <option value="Lower">Lower</option>
              </select>
            </div>
          )}

          {kind === 'exercise' && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.5rem' }}>
              <div className="fh-field">
                <label htmlFor="fh-sets">Sets</label>
                <input id="fh-sets" type="number" min={1} value={sets} onChange={(e) => setSets(e.target.value)} />
              </div>
              <div className="fh-field">
                <label htmlFor="fh-reps">Reps</label>
                <input id="fh-reps" type="number" min={1} value={reps} onChange={(e) => setReps(e.target.value)} />
              </div>
              <div className="fh-field">
                <label htmlFor="fh-weight">Weight (kg)</label>
                <input id="fh-weight" type="number" min={0} step="0.5" value={weight} onChange={(e) => setWeight(e.target.value)} />
              </div>
            </div>
          )}

          {kind === 'weight-goal' && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '0.5rem' }}>
              <div className="fh-field">
                <label htmlFor="fh-initial">Initial</label>
                <input id="fh-initial" type="number" min={0} step="0.1" value={initial} onChange={(e) => setInitial(e.target.value)} />
              </div>
              <div className="fh-field">
                <label htmlFor="fh-current">Current</label>
                <input id="fh-current" type="number" min={0} step="0.1" value={current} onChange={(e) => setCurrent(e.target.value)} />
              </div>
              <div className="fh-field">
                <label htmlFor="fh-target">Target</label>
                <input id="fh-target" type="number" min={0} step="0.1" value={target} onChange={(e) => setTarget(e.target.value)} />
              </div>
            </div>
          )}
        </div>

        <div className="modal-actions">
          <button type="button" className="btn btn-ghost" onClick={onClose}>Cancel</button>
          <button
            type="button"
            className="btn btn-primary"
            onClick={() => void submit()}
            disabled={saving || (kind === 'expense' && (!name.trim() || !cost)) || (kind === 'weight-goal' && (!initial || !current || !target))}
          >
            {saving ? 'Saving…' : 'Create'}
          </button>
        </div>
      </div>
    </div>
  );
};
