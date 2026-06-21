export interface ChartData {
  enrollments_by_semester: { semester: string; count: number }[];
  gpa_distribution: { bucket: string; count: number }[];
  intervention_outcomes: { status: string; count: number }[];
  lms_risk_by_semester: { semester: string; at_risk: number; total: number }[];
}

const BAR_HEIGHT = 120;
const BAR_WIDTH = 32;
const GAP = 8;

function BarChart({
  items,
  barTestId,
  labelKey,
  valueKey,
  color = "bg-blue-500",
}: {
  items: Record<string, number | string>[];
  barTestId: string;
  labelKey: string;
  valueKey: string;
  color?: string;
}) {
  const values = items.map((d) => Number(d[valueKey]));
  const max = Math.max(...values, 1);
  return (
    <div className="flex items-end gap-2" style={{ height: BAR_HEIGHT + 24 }}>
      {items.map((d, i) => {
        const h = Math.round((Number(d[valueKey]) / max) * BAR_HEIGHT);
        return (
          <div key={i} className="flex flex-col items-center" style={{ width: BAR_WIDTH }}>
            <div
              data-testid={barTestId}
              className={`w-full rounded-t ${color}`}
              style={{ height: h }}
              title={`${d[labelKey]}: ${d[valueKey]}`}
            />
            <span className="mt-1 truncate text-center text-xs text-gray-500" style={{ maxWidth: BAR_WIDTH + GAP }}>
              {d[labelKey]}
            </span>
          </div>
        );
      })}
    </div>
  );
}

export default function OverviewCharts({ data }: { data: ChartData }) {
  return (
    <div className="grid grid-cols-2 gap-6">
      <div data-testid="chart-section" className="rounded-lg border bg-white p-4 shadow-sm">
        <h3 className="mb-3 text-sm font-semibold text-gray-700">Enrollments by Semester</h3>
        <BarChart
          items={data.enrollments_by_semester as Record<string, string | number>[]}
          barTestId="enrollments-bar"
          labelKey="semester"
          valueKey="count"
          color="bg-blue-500"
        />
      </div>

      <div data-testid="chart-section" className="rounded-lg border bg-white p-4 shadow-sm">
        <h3 className="mb-3 text-sm font-semibold text-gray-700">GPA Distribution</h3>
        <BarChart
          items={data.gpa_distribution as Record<string, string | number>[]}
          barTestId="gpa-bar"
          labelKey="bucket"
          valueKey="count"
          color="bg-indigo-500"
        />
      </div>

      <div data-testid="chart-section" className="rounded-lg border bg-white p-4 shadow-sm">
        <h3 className="mb-3 text-sm font-semibold text-gray-700">Intervention Outcomes</h3>
        <BarChart
          items={data.intervention_outcomes as Record<string, string | number>[]}
          barTestId="intervention-bar"
          labelKey="status"
          valueKey="count"
          color="bg-emerald-500"
        />
      </div>

      <div data-testid="chart-section" className="rounded-lg border bg-white p-4 shadow-sm">
        <h3 className="mb-3 text-sm font-semibold text-gray-700">LMS Risk by Semester</h3>
        <div className="flex items-end gap-2" style={{ height: BAR_HEIGHT + 24 }}>
          {data.lms_risk_by_semester.map((d, i) => {
            const max = Math.max(d.total, 1);
            const atRiskH = Math.round((d.at_risk / max) * BAR_HEIGHT);
            const safeH = Math.round(((d.total - d.at_risk) / max) * BAR_HEIGHT);
            return (
              <div
                key={i}
                data-testid="lms-risk-group"
                className="flex flex-col items-center"
                style={{ width: BAR_WIDTH }}
              >
                <div className="flex w-full flex-col">
                  <div className="w-full rounded-t bg-red-400" style={{ height: atRiskH }} title={`At risk: ${d.at_risk}`} />
                  <div className="w-full bg-blue-200" style={{ height: safeH }} title={`Safe: ${d.total - d.at_risk}`} />
                </div>
                <span className="mt-1 truncate text-center text-xs text-gray-500" style={{ maxWidth: BAR_WIDTH + GAP }}>
                  {d.semester}
                </span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
