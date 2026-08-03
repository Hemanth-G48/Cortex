import { useState, useEffect } from 'react';
import institutionService, { type Institution } from '../services/institutionService';

export function Admin() {
  const [institutions, setInstitutions] = useState<Institution[]>([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [newName, setNewName] = useState('');
  const [newShortName, setNewShortName] = useState('');
  const [newDescription, setNewDescription] = useState('');
  const [creating, setCreating] = useState(false);

  const fetchInstitutions = () => {
    institutionService.getAllInstitutions()
      .then(setInstitutions)
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchInstitutions();
  }, []);

  const handleCreate = async () => {
    if (!newName || !newShortName) return;
    setCreating(true);
    try {
      await institutionService.createInstitution({
        name: newName,
        shortName: newShortName,
        description: newDescription || undefined,
      });
      setNewName('');
      setNewShortName('');
      setNewDescription('');
      setShowCreate(false);
      fetchInstitutions();
    } catch (error) {
      console.error('Create failed:', error);
    } finally {
      setCreating(false);
    }
  };

  const handleToggleStatus = async (id: number, currentStatus: boolean) => {
    try {
      await institutionService.updateInstitutionStatus(id, !currentStatus);
      fetchInstitutions();
    } catch (error) {
      console.error('Status update failed:', error);
    }
  };

  return (
    <div className="min-h-screen bg-surface-dark">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-2xl font-bold text-text">Admin Panel</h1>
            <p className="text-text-secondary mt-1">Manage institutions and verify them</p>
          </div>
          <button
            onClick={() => setShowCreate(!showCreate)}
            className="text-sm font-medium bg-primary text-white px-4 py-2 rounded-lg hover:bg-primary-dark transition-colors"
          >
            {showCreate ? 'Cancel' : 'Add Institution'}
          </button>
        </div>

        {/* Create Form */}
        {showCreate && (
          <div className="bg-white rounded-2xl border border-border p-6 mb-8">
            <h2 className="text-lg font-semibold text-text mb-4">Add New Institution</h2>
            <div className="space-y-4">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-text mb-1.5">Full Name</label>
                  <input
                    type="text"
                    value={newName}
                    onChange={(e) => setNewName(e.target.value)}
                    className="w-full px-4 py-2.5 border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                    placeholder="e.g., GLA University"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-text mb-1.5">Short Name</label>
                  <input
                    type="text"
                    value={newShortName}
                    onChange={(e) => setNewShortName(e.target.value)}
                    className="w-full px-4 py-2.5 border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                    placeholder="e.g., GLA"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-text mb-1.5">Description (optional)</label>
                <input
                  type="text"
                  value={newDescription}
                  onChange={(e) => setNewDescription(e.target.value)}
                  className="w-full px-4 py-2.5 border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  placeholder="Brief description"
                />
              </div>
              <button
                onClick={handleCreate}
                disabled={creating || !newName || !newShortName}
                className="bg-primary text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-primary-dark transition-colors disabled:opacity-60"
              >
                {creating ? 'Creating...' : 'Create Institution'}
              </button>
            </div>
          </div>
        )}

        {/* Institutions List */}
        {loading ? (
          <div className="flex justify-center py-12">
            <div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full"></div>
          </div>
        ) : (
          <div className="space-y-3">
            {institutions.map(inst => (
              <div
                key={inst.id}
                className="bg-white rounded-xl border border-border p-5 flex items-center justify-between"
              >
                <div>
                  <div className="flex items-center gap-3">
                    <h3 className="font-semibold text-text">{inst.name}</h3>
                    <span className="text-xs font-mono text-text-secondary bg-surface-dark px-2 py-0.5 rounded">
                      {inst.shortName}
                    </span>
                    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                      inst.isActive
                        ? 'bg-green-50 text-green-600'
                        : 'bg-amber-50 text-amber-600'
                    }`}>
                      {inst.isActive ? 'Active' : 'Pending'}
                    </span>
                  </div>
                  {inst.description && (
                    <p className="text-sm text-text-secondary mt-1">{inst.description}</p>
                  )}
                </div>
                <button
                  onClick={() => handleToggleStatus(inst.id, inst.isActive)}
                  className={`text-sm font-medium px-4 py-2 rounded-lg transition-colors ${
                    inst.isActive
                      ? 'bg-red-50 text-red-600 hover:bg-red-100'
                      : 'bg-green-50 text-green-600 hover:bg-green-100'
                  }`}
                >
                  {inst.isActive ? 'Deactivate' : 'Approve'}
                </button>
              </div>
            ))}

            {institutions.length === 0 && (
              <div className="bg-white rounded-2xl border border-border p-8 text-center">
                <p className="text-text-secondary">No institutions yet. Create one to get started.</p>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
