import { STATUS_CLASSES, StatusCode } from "@/lib/status";

export default function StatusBadge({ code }: { code: StatusCode }) {
  const meta = STATUS_CLASSES[code] ?? { label: code, classes: "bg-gray-100 text-gray-600" };
  return (
    <span className={`inline-flex items-center rounded px-2 py-0.5 text-xs font-medium ${meta.classes}`}>
      {meta.label}
    </span>
  );
}
