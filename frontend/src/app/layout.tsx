import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import Link from "next/link";
import "./globals.css";
import { en } from "@/lib/i18n/en";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: en.app.title,
  description: en.app.tagline,
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full flex flex-col bg-background text-foreground">
        <header className="sticky top-0 z-50 border-b border-border bg-background/95 backdrop-blur">
          <div className="mx-auto flex h-14 max-w-5xl items-center px-6">
            <Link
              href="/"
              className="font-heading text-xl font-semibold tracking-tight focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring rounded"
            >
              {en.app.title}
            </Link>
          </div>
        </header>

        <main className="mx-auto w-full max-w-5xl flex-1 px-6 py-10">
          {children}
        </main>
      </body>
    </html>
  );
}
