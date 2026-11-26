import type { Metadata } from "next";
import "./globals.css";
import AuthProvider from "../components/auth-provider";

export const metadata: Metadata = {
  title: "Research Paper AI Risk Analyzer, Rephraser & Humanizer",
  description: "Evaluate your research paper for AI linguistic characteristics, calculate explainable risk scores, rephrase sections, and optimize paper quality for top journal acceptance.",
  keywords: ["AI detection for research", "academic paraphraser", "LLM writing risk score", "paper humanizer", "journal reviewer feedback", "plagiarism safety"],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark">
      <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0" />
      </head>
      <body className="antialiased min-h-screen">
        <AuthProvider />
        <div id="app-root" className="relative flex flex-col min-h-screen">
          {children}
        </div>
      </body>
    </html>
  );
}
