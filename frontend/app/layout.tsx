import type { Metadata } from "next";
import { Inter } from "next/font/google";
import { Nav } from "@/components/Nav";
import { API_URL } from "@/lib/api";
import "./globals.css";

const inter = Inter({ variable: "--font-inter", subsets: ["latin"] });

export const metadata: Metadata = {
  title: "NaSCon AI Starter",
  description: "AI workspace: chat, agent tools, documents, ML and vision.",
};

export default function RootLayout({ children }: LayoutProps<"/">) {
  return (
    <html lang="en" className={`${inter.variable} h-full`}>
      <body className="flex min-h-full flex-col">
        <Nav />
        <main className="mx-auto w-full max-w-[1440px] flex-1 px-4 pb-16 sm:px-6">{children}</main>
        <footer className="border-t border-hairline bg-parchment px-6 py-6 text-center text-[12px] text-ink-48">
          Backend API docs at <a className="text-primary" href={`${API_URL}/docs`}>{API_URL}/docs</a>
        </footer>
      </body>
    </html>
  );
}
