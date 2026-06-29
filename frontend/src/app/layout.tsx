import type { Metadata } from "next";
import "./globals.css";
import Shell from "@/components/Shell";
import TopBar from "@/components/TopBar";
import AuthGuard from "@/components/AuthGuard";
import { getBrandingConfig } from "@/lib/brandingConfig";

const { name, subtitle } = getBrandingConfig();

export const metadata: Metadata = {
  title: name,
  description: subtitle,
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthGuard>
          <Shell>
            <TopBar />
            <div className="page-content">{children}</div>
          </Shell>
        </AuthGuard>
      </body>
    </html>
  );
}
