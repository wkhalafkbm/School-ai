import Link from "next/link";
import { StatusCode } from "@/lib/status";
import { Stage, STAGE_LABELS, STAGE_ROUTES } from "@/lib/stages";
import StatusBadge from "./StatusBadge";

export interface PriorityItem {
  student_id: string;
  student_name: string;
  stage: Stage | string;
  status: StatusCode;
  reason: string;
}

export default function PriorityQueue({ items }: { items: PriorityItem[] }) {
  return (
    <ol className="divide-y rounded-lg border bg-white shadow-sm">
      {items.map((item) => {
        const route = STAGE_ROUTES[item.stage as Stage] ?? "/";
        const href = `${route}?student=${item.student_id}`;
        return (
          <Link
            key={item.student_id}
            href={href}
            data-testid="queue-row"
            className="flex items-center gap-4 px-4 py-3 hover:bg-gray-50"
          >
            <span className="w-36 shrink-0 text-xs text-gray-500">
              {STAGE_LABELS[item.stage as Stage] ?? item.stage}
            </span>
            <span className="flex-1 text-sm font-medium text-gray-900">{item.student_name}</span>
            <StatusBadge code={item.status} />
            <span className="flex-1 truncate text-xs text-gray-500">{item.reason}</span>
          </Link>
        );
      })}
    </ol>
  );
}
