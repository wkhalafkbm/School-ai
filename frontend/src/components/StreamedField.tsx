import { ReactNode } from "react";

export default function StreamedField({
  resolved,
  children,
}: {
  resolved: boolean;
  children: ReactNode;
}) {
  if (resolved) {
    return <>{children}</>;
  }

  return (
    <div aria-busy="true" className="relative min-h-14 overflow-hidden rounded-lg">
      <div className="opacity-60">{children}</div>
      <div
        className="pointer-events-none absolute inset-y-0 w-1/2 bg-gradient-to-r from-transparent via-white/70 to-transparent"
        style={{ animation: "ai-shimmer 1.8s ease-in-out infinite" }}
      />
      <div className="pointer-events-none absolute inset-0 flex items-center justify-center">
        <span className="flex items-center gap-2 rounded-full border border-gray-200 bg-white/95 px-3 py-1.5 text-xs font-medium text-gray-700 shadow-sm">
          <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-blue-500 border-t-transparent" />
          AI refining…
        </span>
      </div>
    </div>
  );
}
