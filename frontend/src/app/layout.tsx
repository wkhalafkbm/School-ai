import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "University AI Operating Center",
  description: "Student Journey Intelligence Layer",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
