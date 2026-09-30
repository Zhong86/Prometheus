import type { Metadata } from "next";
import { Cardo, JetBrains_Mono, Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";

const display = Cardo({ weight: ["400", "700"], subsets: ["latin", "greek"], variable: "--font-display" });
const sans = Plus_Jakarta_Sans({ subsets: ["latin"], variable: "--font-sans" });
const mono = JetBrains_Mono({ weight: "500", subsets: ["latin"], variable: "--font-mono" });

export const metadata: Metadata = {
  title: "Prometheus",
  description: "Turn a topic into three buildable software ideas.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className={`${display.variable} ${sans.variable} ${mono.variable}`}>{children}</body>
    </html>
  );
}
