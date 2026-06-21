export interface OverviewMetrics {
  students_needing_attention: number;
  at_risk_detected_early: number;
  registration_issues_resolved: number;
  graduation_delays_prevented: number;
  faculty_overload_alerts: number;
}

const LABELS: Record<keyof OverviewMetrics, string> = {
  students_needing_attention: "Students Needing Attention",
  at_risk_detected_early: "At-Risk Detected Early",
  registration_issues_resolved: "Registration Issues Resolved",
  graduation_delays_prevented: "Graduation Delays Prevented",
  faculty_overload_alerts: "Faculty Overload Alerts",
};

export default function KpiCards({ metrics }: { metrics: OverviewMetrics }) {
  const keys = Object.keys(LABELS) as (keyof OverviewMetrics)[];
  return (
    <div className="grid grid-cols-5 gap-4">
      {keys.map((key) => (
        <div key={key} data-testid="kpi-card" className="rounded-lg border bg-white p-4 shadow-sm">
          <p className="text-sm text-gray-500">{LABELS[key]}</p>
          <p data-testid={`kpi-${key}`} className="mt-1 text-3xl font-bold text-gray-900">
            {metrics[key]}
          </p>
        </div>
      ))}
    </div>
  );
}
