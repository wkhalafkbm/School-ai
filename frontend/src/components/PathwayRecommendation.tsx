export interface Recommendation {
  action: string;
  confidence: "High" | "Medium" | "Low";
  rationale: string;
}

const CONFIDENCE_CLASSES: Record<Recommendation["confidence"], string> = {
  High: "bg-green-100 text-green-700",
  Medium: "bg-amber-100 text-amber-700",
  Low: "bg-gray-100 text-gray-600",
};

export default function PathwayRecommendation({ recommendation }: { recommendation: Recommendation }) {
  const { action, confidence, rationale } = recommendation;
  return (
    <div className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
      <div className="mb-3 flex items-center gap-3">
        <h2 className="text-base font-semibold text-gray-900">AI Recommendation</h2>
        <span
          data-testid="confidence-label"
          className={`rounded px-2 py-0.5 text-xs font-medium ${CONFIDENCE_CLASSES[confidence]}`}
        >
          {confidence} Confidence
        </span>
      </div>
      <p data-testid="recommendation-action" className="mb-2 font-medium text-gray-900">
        {action}
      </p>
      <p data-testid="rationale" className="text-sm text-gray-600">
        {rationale}
      </p>
    </div>
  );
}
