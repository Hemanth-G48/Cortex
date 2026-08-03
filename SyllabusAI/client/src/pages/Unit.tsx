import { useState, useEffect, useRef } from 'react';
import { useParams, Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import unitService, { type Unit } from '../services/unitService';
import materialService, { type Material } from '../services/materialService';
import aiService, { type Quiz as QuizType, type SummaryData } from '../services/aiService';
import { Quiz } from '../components/Quiz';
import { Summary } from '../components/Summary';

const fileTypeIcons: Record<string, string> = {
  pdf: '📄',
  ppt: '📊',
  pptx: '📊',
  doc: '📝',
  docx: '📝',
};

function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function UnitPage() {
  const { id } = useParams<{ id: string }>();
  const { user } = useAuth();
  const [unit, setUnit] = useState<(Unit & { materials: Material[] }) | null>(null);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [uploadTitle, setUploadTitle] = useState('');
  const [showUpload, setShowUpload] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  // AI state
  const [quiz, setQuiz] = useState<QuizType | null>(null);
  const [summary, setSummary] = useState<SummaryData | null>(null);
  const [generatingQuiz, setGeneratingQuiz] = useState(false);
  const [generatingSummary, setGeneratingSummary] = useState(false);
  const [aiError, setAiError] = useState('');

  const fetchUnit = () => {
    if (!id) return;
    unitService.getUnitById(Number(id))
      .then(setUnit)
      .catch(console.error)
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    fetchUnit();
  }, [id]);

  const handleUpload = async () => {
    const file = fileInputRef.current?.files?.[0];
    if (!file || !uploadTitle || !id) return;

    setUploading(true);
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('title', uploadTitle);
      await materialService.uploadMaterial(Number(id), formData);
      setUploadTitle('');
      setShowUpload(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
      fetchUnit();
    } catch (error) {
      console.error('Upload failed:', error);
    } finally {
      setUploading(false);
    }
  };

  const handleGenerateQuiz = async () => {
    if (!id) return;
    setGeneratingQuiz(true);
    setAiError('');
    try {
      const quizData = await aiService.generateQuiz(Number(id));
      setQuiz(quizData);
    } catch (error: any) {
      setAiError(error.response?.data?.message || 'Failed to generate quiz');
    } finally {
      setGeneratingQuiz(false);
    }
  };

  const handleGenerateSummary = async () => {
    if (!id) return;
    setGeneratingSummary(true);
    setAiError('');
    try {
      const { summary: summaryData } = await aiService.generateSummary([Number(id)]);
      setSummary(summaryData);
    } catch (error: any) {
      setAiError(error.response?.data?.message || 'Failed to generate summary');
    } finally {
      setGeneratingSummary(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="animate-spin w-8 h-8 border-4 border-primary border-t-transparent rounded-full"></div>
      </div>
    );
  }

  if (!unit) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-text-secondary">Unit not found.</p>
      </div>
    );
  }

  const materials = unit.materials || [];

  return (
    <div className="min-h-screen bg-surface-dark">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Breadcrumb */}
        <nav className="mb-6 text-sm text-text-secondary">
          <Link to="/dashboard" className="hover:text-primary no-underline">Dashboard</Link>
          <span className="mx-2">/</span>
          <span className="text-text">Unit {unit.unitNumber}: {unit.name}</span>
        </nav>

        {/* Header */}
        <div className="bg-white rounded-2xl border border-border p-6 mb-8">
          <div className="flex items-center gap-4">
            <div className="w-14 h-14 bg-primary/10 text-primary rounded-xl flex items-center justify-center font-bold text-xl">
              {unit.unitNumber}
            </div>
            <div>
              <h1 className="text-2xl font-bold text-text">{unit.name}</h1>
              {unit.description && (
                <p className="text-text-secondary mt-1">{unit.description}</p>
              )}
            </div>
          </div>
        </div>

        {/* AI Error */}
        {aiError && (
          <div className="bg-red-50 text-red-600 px-4 py-3 rounded-lg text-sm mb-6">
            {aiError}
          </div>
        )}

        {/* Quiz Modal */}
        {quiz && (
          <div className="mb-8">
            <Quiz quiz={quiz} onClose={() => setQuiz(null)} />
          </div>
        )}

        {/* Summary Display */}
        {summary && (
          <div className="mb-8">
            <Summary summary={summary} onClose={() => setSummary(null)} />
          </div>
        )}

        {/* Action Buttons */}
        {!quiz && !summary && (
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-8">
            <button
              onClick={handleGenerateQuiz}
              disabled={generatingQuiz || materials.length === 0 || !user}
              className="bg-white rounded-xl border border-border p-5 text-left hover:border-purple-300 hover:shadow-md transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-purple-50 text-purple-600 rounded-lg flex items-center justify-center text-xl">
                  {generatingQuiz ? (
                    <div className="animate-spin w-5 h-5 border-2 border-purple-600 border-t-transparent rounded-full"></div>
                  ) : (
                    '🧠'
                  )}
                </div>
                <div>
                  <h3 className="font-semibold text-text">
                    {generatingQuiz ? 'Generating Quiz...' : 'Generate Quiz'}
                  </h3>
                  <p className="text-xs text-text-secondary">
                    {materials.length === 0 ? 'Upload materials first' : 'AI-powered quiz from your materials'}
                  </p>
                </div>
              </div>
            </button>
            <button
              onClick={handleGenerateSummary}
              disabled={generatingSummary || materials.length === 0 || !user}
              className="bg-white rounded-xl border border-border p-5 text-left hover:border-green-300 hover:shadow-md transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
            >
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-green-50 text-green-600 rounded-lg flex items-center justify-center text-xl">
                  {generatingSummary ? (
                    <div className="animate-spin w-5 h-5 border-2 border-green-600 border-t-transparent rounded-full"></div>
                  ) : (
                    '📋'
                  )}
                </div>
                <div>
                  <h3 className="font-semibold text-text">
                    {generatingSummary ? 'Generating Summary...' : 'Generate Summary'}
                  </h3>
                  <p className="text-xs text-text-secondary">
                    {materials.length === 0 ? 'Upload materials first' : 'AI summary with key points'}
                  </p>
                </div>
              </div>
            </button>
          </div>
        )}

        {/* Materials Section */}
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-text">
            Materials ({materials.length})
          </h2>
          {user && (
            <button
              onClick={() => setShowUpload(!showUpload)}
              className="text-sm font-medium bg-primary text-white px-4 py-2 rounded-lg hover:bg-primary-dark transition-colors"
            >
              {showUpload ? 'Cancel' : 'Upload Material'}
            </button>
          )}
        </div>

        {/* Upload Form */}
        {showUpload && (
          <div className="bg-white rounded-xl border border-border p-5 mb-6">
            <div className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-text mb-1.5">Title</label>
                <input
                  type="text"
                  value={uploadTitle}
                  onChange={(e) => setUploadTitle(e.target.value)}
                  className="w-full px-4 py-2.5 border border-border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-primary/20 focus:border-primary"
                  placeholder="e.g., Introduction to Arrays - Lecture Notes"
                />
              </div>
              <div>
                <label className="block text-sm font-medium text-text mb-1.5">File (PDF, PPT, DOC)</label>
                <input
                  type="file"
                  ref={fileInputRef}
                  accept=".pdf,.ppt,.pptx,.doc,.docx"
                  className="w-full text-sm text-text-secondary file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-primary/10 file:text-primary hover:file:bg-primary/20"
                />
              </div>
              <button
                onClick={handleUpload}
                disabled={uploading || !uploadTitle}
                className="bg-primary text-white px-6 py-2 rounded-lg text-sm font-medium hover:bg-primary-dark transition-colors disabled:opacity-60 disabled:cursor-not-allowed"
              >
                {uploading ? 'Uploading...' : 'Upload'}
              </button>
            </div>
          </div>
        )}

        {/* Materials List */}
        {materials.length > 0 ? (
          <div className="space-y-3">
            {materials.map(material => (
              <div
                key={material.id}
                className="bg-white rounded-xl border border-border p-5 flex items-center justify-between"
              >
                <div className="flex items-center gap-4">
                  <div className="text-2xl">
                    {fileTypeIcons[material.fileType] || '📄'}
                  </div>
                  <div>
                    <h3 className="font-medium text-text">{material.title}</h3>
                    <div className="flex items-center gap-3 text-xs text-text-secondary mt-1">
                      <span className="uppercase font-medium">{material.fileType}</span>
                      <span>{formatFileSize(material.fileSize)}</span>
                      <span>{material.downloadCount} downloads</span>
                    </div>
                  </div>
                </div>
                <a
                  href={materialService.getDownloadUrl(material.id)}
                  className="flex items-center gap-2 text-sm font-medium text-primary bg-primary/10 px-4 py-2 rounded-lg hover:bg-primary/20 transition-colors no-underline"
                >
                  Download
                </a>
              </div>
            ))}
          </div>
        ) : (
          <div className="bg-white rounded-2xl border border-border p-8 text-center">
            <div className="text-4xl mb-4">📁</div>
            <h3 className="text-lg font-semibold text-text mb-2">No materials yet</h3>
            <p className="text-text-secondary">
              {user ? 'Be the first to upload study materials for this unit!' : 'Sign in to upload materials.'}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
