import "./globals.css";
import type { Metadata } from "next";
import type { ReactNode } from "react";
import { Inter, JetBrains_Mono } from "next/font/google";
import { Header } from "@/components/Header";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-sans",
  display: "swap",
});

const mono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: "Eidolon — Audit Dashboard",
  description:
    "OSINT-calibrated password risk assessment and context-aware authentication hardening.",
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className={`${inter.variable} ${mono.variable}`}>
      <body className="min-h-screen font-sans">
        <Header />
        <main className="mx-auto max-w-7xl px-6 py-10">{children}</main>
        <footer className="mx-auto max-w-7xl border-t border-border px-6 py-6 text-xs text-ink-faint">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <span>
              Stateless API · Synthetic data only · Apache-2.0
            </span>
            <span className="font-mono">v0.1.0 · 2026</span>
          </div>
        </footer>
      </body>
    </html>
  );
}
