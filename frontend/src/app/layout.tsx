import type { Metadata } from "next";
import "./globals.css";
import Shell from "@/components/Shell";
import TopBar from "@/components/TopBar";

const universityName =
  process.env.NEXT_PUBLIC_UNIVERSITY_NAME ?? "University AI Operating Center";

export const metadata: Metadata = {
  title: universityName,
  description: "Student Journey Intelligence Layer",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <Shell>
          <TopBar />
          <div className="page-content">{children}</div>
        </Shell>
      </body>
    </html>
  );
}
