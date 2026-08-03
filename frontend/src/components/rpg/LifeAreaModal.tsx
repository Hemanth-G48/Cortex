import { useState } from 'react';
import { RpgCard } from './RpgCard';
import { RpgButton } from './RpgButton';
import { endpoints } from '../../services/api';
import type { LifeArea } from '../../services/api';

interface LifeAreaModalProps {
  area: LifeArea | null;
  onClose: () => void;
  onSaved: (updated: LifeArea) => void;
}

export function LifeAreaModal({ area, onClose, onSaved }: LifeAreaModalProps) {
  const [name, setName] = useState(area?.name ?? '');
  const [description, setDescription] = useState(area?.description ?? '');
  const [progress, setProgress] = useState(area?.progress_percent ?? 0);
  const [saving, setSaving] = useState(false);

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    try {
      const updated = await endpoints.lifeAreas.update(area!.id, {
        name,
        description,
        progress_percent: progress,
      });
      onSaved(updated);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0,0,0,0.7)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
      }}
      onClick={onClose}
    >
      <RpgCard
        style={{ maxWidth: 480, width: '100%', padding: 0 }}
        onClick={(e) => e.stopPropagation()}
      >
        <div style={{ padding: '24px 24px 0' }}>
          <h2
            style={{
              margin: '0 0 20px',
              fontSize: '18px',
              color: '#fff',
              fontFamily: 'monospace',
              letterSpacing: '2px',
              textTransform: 'uppercase',
            }}
          >
            Edit Life Area
          </h2>

          <form onSubmit={handleSave}>
            <div style={{ marginBottom: 12 }}>
              <label
                style={{
                  display: 'block',
                  marginBottom: 4,
                  color: '#b0b0b0',
                  fontSize: 13,
                  fontFamily: 'monospace',
                }}
              >
                Name
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Life Area Name"
                style={{
                  width: '100%',
                  backgroundColor: '#2a2a2a',
                  border: '1px solid #3a3a3a',
                  padding: '8px',
                  borderRadius: 6,
                  color: '#fff',
                  fontSize: 14,
                  boxSizing: 'border-box',
                  outline: 'none',
                }}
              />
            </div>

            <div style={{ marginBottom: 12 }}>
              <label
                style={{
                  display: 'block',
                  marginBottom: 4,
                  color: '#b0b0b0',
                  fontSize: 13,
                  fontFamily: 'monospace',
                }}
              >
                Description / Goal
              </label>
              <textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder="Describe this area..."
                rows={3}
                style={{
                  width: '100%',
                  backgroundColor: '#2a2a2a',
                  border: '1px solid #3a3a3a',
                  padding: '8px',
                  borderRadius: 6,
                  color: '#fff',
                  fontSize: 14,
                  boxSizing: 'border-box',
                  outline: 'none',
                  resize: 'vertical',
                  fontFamily: 'inherit',
                }}
              />
            </div>

            <div style={{ marginBottom: 20 }}>
              <label
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  marginBottom: 4,
                  color: '#b0b0b0',
                  fontSize: 13,
                  fontFamily: 'monospace',
                }}
              >
                <span>Progress</span>
                <span>{progress}%</span>
              </label>
              <input
                type="range"
                min={0}
                max={100}
                value={progress}
                onChange={(e) => setProgress(Number(e.target.value))}
                style={{
                  width: '100%',
                  accentColor: '#e8740c',
                  cursor: 'pointer',
                }}
              />
            </div>

            <div
              style={{
                display: 'flex',
                gap: 8,
                justifyContent: 'flex-end',
                padding: '0 24px 24px',
              }}
            >
              <RpgButton variant="ghost" onClick={onClose} type="button">
                Cancel
              </RpgButton>
              <RpgButton variant="orange" type="submit" disabled={saving}>
                {saving ? 'Saving...' : 'Save'}
              </RpgButton>
            </div>
          </form>
        </div>
      </RpgCard>
    </div>
  );
}
