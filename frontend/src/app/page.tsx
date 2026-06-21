import KpiCards, { OverviewMetrics } from "@/components/KpiCards";
import JourneyHealthMap, { JourneyHealth } from "@/components/JourneyHealthMap";
import OverviewCharts, { ChartData } from "@/components/OverviewCharts";
import PriorityQueue, { PriorityItem } from "@/components/PriorityQueue";

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${API}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${path} → ${res.status}`);
  return res.json();
}

export default async function OverviewPage() {
  const [metrics, health, queue, chartData] = await Promise.all([
    fetchJson<OverviewMetrics>("/api/overview/metrics"),
    fetchJson<JourneyHealth>("/api/overview/journey-health"),
    fetchJson<PriorityItem[]>("/api/overview/priority-queue"),
    fetchJson<ChartData>("/api/overview/chart-data"),
  ]);

  return (
    <main className="space-y-8 p-6">
      <section aria-label="Key Performance Indicators">
        <KpiCards metrics={metrics} />
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
