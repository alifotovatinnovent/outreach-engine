import type { Metadata } from "next";
import Link from "next/link";
import "./globals.css";

export const metadata: Metadata = {
  title: "Outreach Engine",
  description: "Multi-channel B2B outreach orchestrator",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <header className="border-b border-slate-200 bg-white">
          <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
            <Link href="/" className="flex items-center gap-2 text-lg font-semibold">
              <span className="rounded bg-slate-900 px-2 py-1 text-sm text-white">OE</span>
              Outreach Engine
            </Link>
            <nav className="flex gap-6 text-sm text-slate-600">
              <Link href="/" className="hover:text-slate-900">Accounts</Link>
              <Link href="/settings" className="hover:text-slate-900">Settings</Link>
            </nav>
          </div>
        </header>
        <main className="mx-auto max-w-6xl px-6 py-8">{children}</main>
      </body>
    </html>
  );
}
