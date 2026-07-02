import { ReactNode } from "react";

export default function StreamedField({
  resolved,
  children,
}: {
  resolved: boolean;
  children: ReactNode;
}) {
  return (
    <span className="inline-flex items-center gap-2">
      {children}
      {!resolved && (
        <span className="rounded bg-blue-100 px-2 py-0.5 text-xs font-medium text-blue-700">
          AI refining…
        </span>
      )}
    </span>
  );
}
