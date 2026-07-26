import KpiCards, { MetricDetail, MetricKey, OverviewMetrics } from "@/components/KpiCards";
import JourneyHealthMap, { JourneyHealth } from "@/components/JourneyHealthMap";
import OverviewCharts, { ChartData } from "@/components/OverviewCharts";
import PriorityQueue, { PriorityItem } from "@/components/PriorityQueue";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return res.json();
}

const fetchDetail = (key: MetricKey) =>
  fetchJson<MetricDetail>(`/api/overview/metrics/${key}/detail`);

export default async function OverviewPage() {
  // The five drill-downs ride along with the other reads so every panel opens
  // instantly — no client-side fetch, no spinner inside the panel.
  const [
    metrics,
    health,
    queue,
    chartData,
    attentionDetail,
    earlyDetail,
    registrationDetail,
    graduationDetail,
    facultyDetail,
  ] = await Promise.all([
    fetchJson<OverviewMetrics>("/api/overview/metrics"),
    fetchJson<JourneyHealth>("/api/overview/journey-health"),
    fetchJson<PriorityItem[]>("/api/overview/priority-queue"),
    fetchJson<ChartData>("/api/overview/chart-data"),
    fetchDetail("students_needing_attention"),
    fetchDetail("at_risk_detected_early"),
    fetchDetail("registration_issues_resolved"),
    fetchDetail("graduation_delays_prevented"),
    fetchDetail("faculty_overload_alerts"),
  ]);

  const details: Record<MetricKey, MetricDetail> = {
    students_needing_attention: attentionDetail,
    at_risk_detected_early: earlyDetail,
    registration_issues_resolved: registrationDetail,
    graduation_delays_prevented: graduationDetail,
    faculty_overload_alerts: facultyDetail,
  };

  return (
    <main className="space-y-8 p-6">
      <section aria-label="Key Performance Indicators">
        <KpiCards metrics={metrics} details={details} />
      </section>

      <section aria-label="Journey Health">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
          Journey Health
        </h2>
        <JourneyHealthMap health={health} />
      </section>

      <section aria-label="Aggregate Metrics">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
          Aggregate Metrics
        </h2>
        <OverviewCharts data={chartData} />
      </section>

      <section aria-label="Priority Queue">
        <h2 className="mb-3 text-sm font-semibold uppercase tracking-wide text-gray-500">
          Priority Queue
        </h2>
        <PriorityQueue items={queue} />
      </section>
    </main>
  );
}
