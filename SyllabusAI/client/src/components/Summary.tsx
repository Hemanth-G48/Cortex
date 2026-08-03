import { type SummaryData } from '../services/aiService';

interface SummaryProps {
  summary: SummaryData;
  onClose: () => void;
}

export function Summary({ summary, onClose }: SummaryProps) {
  return (
    <div className="bg-white rounded-2xl border border-border p-6">
      <div className="flex items-center justify-between mb-6">
        <h3 className="text-lg font-semibold text-text">AI Summary</h3>
        <button
          onClick={onClose}
          className="text-text-secondary hover:text-text bg-transparent border-none cursor-pointer text-lg"
        >
          ✕
        </button>
      </div>

      {/* Key Points */}
      {summary.keyPoints.length > 0 && (
        <div className="bg-primary/5 rounded-xl p-4 mb-6">
          <h4 className="text-sm font-semibold text-primary mb-3">Key Takeaways</h4>
          <ul className="space-y-2">
            {summary.keyPoints.map((point, i) => (
              <li key={i} className="flex items-start gap-2 text-sm text-text">
                <span className="text-primary mt-0.5">•</span>
                <span>{point}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Full Summary */}
      <div className="prose prose-sm max-w-none text-text-secondary leading-relaxed whitespace-pre-wrap">
        {summary.content}
      </div>
    </div>
  );
}
