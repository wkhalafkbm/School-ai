import { StatusCode, STATUS_CLASSES } from "@/lib/status";
import { JOURNEY_HEALTH_STAGES, JourneyHealthStage, STAGE_LABELS } from "@/lib/stages";

export type JourneyHealth = Record<JourneyHealthStage, StatusCode>;

export default function JourneyHealthMap({ health }: { health: JourneyHealth }) {
  const stages: readonly JourneyHealthStage[] = JOURNEY_HEALTH_STAGES;
  return (
    <div className="flex gap-3">
      {stages.map((stage) => {
        const code = health[stage];
        const { label, classes } = STATUS_CLASSES[code];
        return (
          <div key={stage} className="flex flex-col items-center gap-1">
            <span className="text-xs text-gray-500">{STAGE_LABELS[stage]}</span>
            <span
              data-testid="health-badge"
              className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-medium ${classes}`}
            >
              {label}
            </span>
          </div>
        );
      })}
    </div>
  );
}
