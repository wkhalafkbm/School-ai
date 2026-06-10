"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV_ITEMS = [
  { label: "Overview", href: "/" },
  { label: "Admissions", href: "/admissions" },
  { label: "Enrollment", href: "/enrollment" },
  { label: "Teaching Readiness", href: "/teaching-readiness" },
  { label: "Academic Risk", href: "/academic-risk" },
  { label: "Progression", href: "/progression" },
  { label: "Career & Alumni", href: "/career-alumni" },
  { label: "Workflow Activity", href: "/workflow-activity" },
];

export default function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="shell-layout">
      <nav className="sidebar" aria-label="Journey stages">
        <ul>
          {NAV_ITEMS.map(({ label, href }) => (
            <li key={href}>
              <Link
                href={href}
                className={pathname === href ? "nav-link nav-link--active" : "nav-link"}
                aria-current={pathname === href ? "page" : undefined}
              >
                {label}
              </Link>
            </li>
          ))}
        </ul>
      </nav>
      <div className="shell-content">{children}</div>
    </div>
  );
}
