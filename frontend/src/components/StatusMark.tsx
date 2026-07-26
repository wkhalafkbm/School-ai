import { STATUS_CLASSES, StatusCode } from "@/lib/status";

export default function StatusMark({ code }: { code: StatusCode }) {
  const meta = STATUS_CLASSES[code] ?? {
    label: code,
    classes: "bg-gray-100 text-gray-600",
    accent: "bg-gray-400",
  };
  return (
    <span className="flex w-40 shrink-0 items-center gap-2">
      <span data-testid="status-rail" className={`h-5 w-0.5 shrink-0 rounded-full ${meta.accent}`} />
      <span data-testid="status-dot" className={`h-1.5 w-1.5 shrink-0 rounded-full ${meta.accent}`} />
      <span className="text-[11px] font-semibold uppercase tracking-wide text-gray-700">
        {meta.label}
      </span>
    </span>
  );
}
