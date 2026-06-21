import { StatusCode, STATUS_CLASSES } from "@/lib/status";

export type JourneyHealth = {
  onboarding: StatusCode;
  registration: StatusCode;
  academic_progress: StatusCode;
  graduation_planning: StatusCode;
  career: StatusCode;
};

const STAGE_LABELS: Record<keyof JourneyHealth, string> = {
  onboarding: "Onboarding",
  registration: "Registration",
  academic_progress: "Academic Progress",
  graduation_planning: "Graduation Planning",
  career: "Career",
};

export default function JourneyHealthMap({ health }: { health: JourneyHealth }) {
  const stages = Object.keys(STAGE_LABELS) as (keyof JourneyHealth)[];
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
