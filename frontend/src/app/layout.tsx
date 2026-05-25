import type { Metadata } from "next";
import "./globals.css";
import { QueryProvider } from "@/components/shared/QueryProvider";

export const metadata: Metadata = {
  title: "Aarav AI Music — Dashboard",
  description: "AI Music Production Control Panel",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen bg-[#0f0f1a] text-gray-100">
        <QueryProvider>{children}</QueryProvider>
      </body>
    </html>
  );
}
