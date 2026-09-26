/**
 * The six-step quality workflow from the deck (#98): Measure (AI), Diagnose
 * (AI), Moderate (human/AI), Validate (human), Act (human), Re-measure (AI).
 *
 * The strip is lit up to and including `activeStep`; the page derives that
 * from the flags: nothing flagged means the AI measured and diagnosed and
 * found nothing, an open flag is waiting at Moderate, a routed flag sits with
 * the Programme Quality Lead at Validate.
 */

export type WorkflowStep = "Measure" | "Diagnose" | "Moderate" | "Validate" | "Act" | "Re-measure";

export const WORKFLOW_STEPS: { name: WorkflowStep; actor: string }[] = [
  { name: "Measure", actor: "AI" },
  { name: "Diagnose", actor: "AI" },
  { name: "Moderate", actor: "Human / AI" },
  { name: "Validate", actor: "Human" },
  { name: "Act", actor: "Human" },
  { name: "Re-measure", actor: "AI" },
];

export default function WorkflowStrip({ activeStep }: { activeStep: WorkflowStep }) {
  const activeIndex = WORKFLOW_STEPS.findIndex((step) => step.name === activeStep);

  return (
    <nav aria-label="Moderation workflow" className="rounded-lg border border-gray-200 bg-white p-5 shadow-sm">
      <h2 className="mb-3 text-base font-semibold text-gray-900">Quality workflow</h2>
      <ol aria-label="Moderation workflow steps" className="flex flex-wrap gap-2">
        {WORKFLOW_STEPS.map((step, index) => {
          const lit = index <= activeIndex;
          const current = index === activeIndex;
          return (
            <li
              key={step.name}
              data-step={step.name}
              data-lit={lit ? "true" : "false"}
              aria-current={current ? "step" : undefined}
              className={`flex min-w-[7rem] flex-1 flex-col rounded-md border px-3 py-2 text-sm ${
                lit
                  ? current
                    ? "border-blue-500 bg-blue-50 text-blue-900"
                    : "border-blue-200 bg-blue-50 text-blue-800"
                  : "border-gray-200 bg-gray-50 text-gray-400"
              }`}
            >
              <span className="font-medium">{step.name}</span>
              <span className="text-xs">{step.actor}</span>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
