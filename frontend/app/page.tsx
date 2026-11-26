"use client";

import { useRouter } from "next/navigation";
import { ArrowRight, CheckCircle2, Award, Zap, HeartPulse, Sparkles, BookOpen, ShieldCheck } from "lucide-react";

export default function LandingPage() {
  const router = useRouter();

  const handleGetStarted = () => {
    const token = localStorage.getItem("token");
    if (token) {
      router.push("/dashboard");
    } else {
      router.push("/login");
    }
  };

  return (
    <div className="min-h-screen bg-[#0A0F1D] text-slate-100 flex flex-col relative overflow-hidden font-sans selection:bg-indigo-500/30 selection:text-indigo-200">
      {/* Premium Animated Glow Backgrounds */}
      <div className="absolute top-[-10%] left-[-10%] w-[600px] h-[600px] rounded-full bg-blue-600/10 blur-[130px] animate-pulse" />
      <div className="absolute bottom-[-10%] right-[-10%] w-[600px] h-[600px] rounded-full bg-indigo-600/10 blur-[130px] animate-pulse" />
      <div className="absolute top-[40%] left-[50%] -translate-x-1/2 w-[800px] h-[300px] rounded-full bg-purple-600/5 blur-[150px]" />

      {/* Header Navigation */}
      <header className="w-full max-w-7xl mx-auto py-6 px-6 flex justify-between items-center relative z-20">
        <div className="flex items-center gap-3 cursor-pointer" onClick={() => router.push("/")}>
          <div className="bg-indigo-500/20 p-2 rounded-xl text-indigo-400 border border-indigo-500/30 shadow-lg shadow-indigo-500/15">
            <ShieldCheck size={24} className="animate-pulse" />
          </div>
          <div>
            <h1 className="text-xl font-black tracking-wider bg-gradient-to-r from-blue-400 via-indigo-400 to-purple-400 bg-clip-text text-transparent">
              LEXORA
            </h1>
            <p className="text-[9px] text-slate-400 tracking-widest font-semibold uppercase">
              Writing Intelligence Platform
            </p>
          </div>
        </div>

        <div className="flex items-center gap-4">
          <button 
            onClick={() => router.push("/login")}
            className="text-xs font-bold text-slate-300 hover:text-white transition-colors"
          >
            Sign In Portal
          </button>
          <button
            onClick={handleGetStarted}
            className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold px-4 py-2.5 rounded-xl border border-indigo-500/30 transition-all hover:scale-105 shadow-md shadow-indigo-500/10 flex items-center gap-1.5"
          >
            Get Started <ArrowRight size={14} />
          </button>
        </div>
      </header>

      {/* Hero Section */}
      <section className="w-full max-w-7xl mx-auto py-16 px-6 text-center flex flex-col items-center gap-6 relative z-10">
        <div className="inline-flex items-center gap-2 bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 px-4 py-1.5 rounded-full text-xs font-semibold">
          <Sparkles size={14} className="animate-spin text-indigo-400" />
          AI-Powered Academic Writing Intelligence
        </div>

        <h1 className="text-4xl sm:text-6xl font-black tracking-tight max-w-4xl leading-[1.1] bg-gradient-to-b from-white to-slate-300 bg-clip-text text-transparent">
          Linguistic Analytics & Style Optimization for Researchers
        </h1>

        <p className="text-xs sm:text-sm text-slate-400 max-w-2xl leading-relaxed">
          Lexora audits document structure, vocabulary density, character perplexity, and stylistic variations. Identify stilted phrasing, enhance burstiness, and preserve citations with complete confidentiality.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 mt-4">
          <button
            onClick={handleGetStarted}
            className="bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold px-6 py-3.5 rounded-xl transition-all hover:scale-105 shadow-lg shadow-indigo-500/20 flex items-center justify-center gap-2"
          >
            Start Linguistic Audit <ArrowRight size={16} />
          </button>
          <a
            href="#metrics"
            className="bg-slate-900 hover:bg-slate-800 text-slate-200 text-xs font-bold px-6 py-3.5 rounded-xl border border-slate-800 transition-all hover:scale-105 flex items-center justify-center"
          >
            Show Technical Specs
          </a>
        </div>
      </section>

      {/* Telemetry Stats Section */}
      <section className="w-full max-w-7xl mx-auto py-12 px-6 relative z-10">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 bg-slate-900/45 backdrop-blur-md border border-slate-800/80 p-8 rounded-3xl text-center shadow-xl shadow-black/10">
          <div>
            <h3 className="text-3xl sm:text-4xl font-black text-blue-400">8</h3>
            <p className="text-xs text-slate-400 mt-1.5 uppercase font-bold tracking-wider">Statistical Features Evaluated</p>
          </div>
          <div className="border-y md:border-y-0 md:border-x border-slate-800 py-6 md:py-0">
            <h3 className="text-3xl sm:text-4xl font-black text-indigo-400">100%</h3>
            <p className="text-xs text-slate-400 mt-1.5 uppercase font-bold tracking-wider">Citation & Formula Retention</p>
          </div>
          <div>
            <h3 className="text-3xl sm:text-4xl font-black text-purple-400">Zero</h3>
            <p className="text-xs text-slate-400 mt-1.5 uppercase font-bold tracking-wider">Document Storage / Server Logs</p>
          </div>
        </div>
      </section>

      {/* Features Showcase Section */}
      <section id="features" className="w-full max-w-7xl mx-auto py-16 px-6 flex flex-col gap-12 relative z-10">
        <div className="text-center max-w-md mx-auto flex flex-col gap-3">
          <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight">Advanced Platform Features</h2>
          <p className="text-xs text-slate-400">
            Engineered to analyze stilted writing patterns, improve flow readability, and preserve research elements.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          {/* Card 1 */}
          <div className="bg-slate-900/30 backdrop-blur-md border border-slate-800/80 p-6 rounded-3xl flex flex-col gap-4 shadow-md hover:scale-[1.02] transition-transform duration-300">
            <div className="bg-blue-500/10 text-blue-400 border border-blue-500/20 p-3 rounded-2xl w-fit">
              <Zap size={22} />
            </div>
            <h3 className="text-base font-bold text-slate-100">Linguistic Risk Engine</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Computes real-time Shannon Entropy, character-level perplexity ratios, lexical diversity (TTR), and cliché frequencies for structural diagnostics.
            </p>
          </div>

          {/* Card 2 */}
          <div className="bg-slate-900/30 backdrop-blur-md border border-slate-800/80 p-6 rounded-3xl flex flex-col gap-4 shadow-md hover:scale-[1.02] transition-transform duration-300">
            <div className="bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 p-3 rounded-2xl w-fit">
              <Sparkles size={22} />
            </div>
            <h3 className="text-base font-bold text-slate-100">LaTeX Matrix Preserver</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Safeguards your bibliography references, brackets, inline LaTeX math equations, and tables while suggesting structural changes.
            </p>
          </div>

          {/* Card 3 */}
          <div className="bg-slate-900/30 backdrop-blur-md border border-slate-800/80 p-6 rounded-3xl flex flex-col gap-4 shadow-md hover:scale-[1.02] transition-transform duration-300">
            <div className="bg-purple-500/10 text-purple-400 border border-purple-500/20 p-3 rounded-2xl w-fit">
              <HeartPulse size={22} />
            </div>
            <h3 className="text-base font-bold text-slate-100">Stylistic Pacing Tuner</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Provides actionable style tips for passive voice overuse, stilted vocabulary, and uniformity of sentence lengths.
            </p>
          </div>
        </div>
      </section>

      {/* Technical Specifications Section */}
      <section id="metrics" className="w-full max-w-7xl mx-auto py-16 px-6 flex flex-col gap-12 relative z-10 border-t border-slate-900">
        <div className="text-center max-w-lg mx-auto flex flex-col gap-3">
          <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight">The Lexora Linguistic Framework</h2>
          <p className="text-xs text-slate-400">
            How we calculate stylometric and mathematical markers to identify stilted text patterns.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-slate-900/30 backdrop-blur-md border border-slate-800/80 p-6 rounded-3xl flex gap-4 items-start shadow-md">
            <div className="bg-indigo-500/10 text-indigo-400 border border-indigo-500/20 p-2.5 rounded-xl shrink-0">
              <BookOpen size={20} />
            </div>
            <div className="flex flex-col gap-2">
              <h4 className="text-sm font-bold text-slate-100">Trigram Perplexity & Entropy</h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                Evaluates transition statistics against natural English distribution models. Lower perplexity and highly predictable word entropy indicates stilted, machine-like constructs.
              </p>
            </div>
          </div>

          <div className="bg-slate-900/30 backdrop-blur-md border border-slate-800/80 p-6 rounded-3xl flex gap-4 items-start shadow-md">
            <div className="bg-blue-500/10 text-blue-400 border border-blue-500/20 p-2.5 rounded-xl shrink-0">
              <Award size={20} />
            </div>
            <div className="flex flex-col gap-2">
              <h4 className="text-sm font-bold text-slate-100">Sentence length Coefficient of Variation</h4>
              <p className="text-xs text-slate-400 leading-relaxed">
                Measures burstiness. Natural writing displays wide variability in sentence length, whereas stilted or automated writing shows uniform sentence structures.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Tiers Section */}
      <section className="w-full max-w-7xl mx-auto py-16 px-6 flex flex-col gap-12 relative z-10">
        <div className="text-center max-w-md mx-auto flex flex-col gap-3">
          <h2 className="text-2xl sm:text-3xl font-extrabold tracking-tight">Access Plans</h2>
          <p className="text-xs text-slate-400">
            Choose the dashboard tier that fits your academic writing requirements.
          </p>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 items-stretch">
          {/* Plan 1 */}
          <div className="bg-slate-900/20 backdrop-blur-md border border-slate-800/80 p-6 rounded-3xl flex flex-col gap-6 justify-between shadow-md">
            <div className="flex flex-col gap-2">
              <span className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">Scholar Free</span>
              <h3 className="text-2xl font-black text-slate-100">$0 <span className="text-xs font-normal text-slate-400">/ forever</span></h3>
              <p className="text-xs text-slate-400">Basic metrics and visual highlighting.</p>
              <ul className="text-xs text-slate-300 flex flex-col gap-2 mt-4">
                <li className="flex items-center gap-2"><CheckCircle2 size={14} className="text-blue-400" /> Max 2 files history</li>
                <li className="flex items-center gap-2"><CheckCircle2 size={14} className="text-blue-400" /> Standard Linguistic Scores</li>
                <li className="flex items-center gap-2"><CheckCircle2 size={14} className="text-blue-400" /> Style and flow highlighting</li>
              </ul>
            </div>
            <button onClick={handleGetStarted} className="w-full bg-slate-800 hover:bg-slate-750 text-slate-200 text-xs font-bold py-3 rounded-xl border border-slate-700/50 mt-4 transition-all">
              Launch Portal
            </button>
          </div>

          {/* Plan 2 */}
          <div className="bg-slate-900/40 backdrop-blur-md border-2 border-indigo-500 p-6 rounded-3xl flex flex-col gap-6 justify-between shadow-lg relative">
            <span className="absolute top-3 right-3 bg-indigo-500 text-white text-[9px] font-bold uppercase tracking-widest px-2.5 py-1 rounded-full">
              Standard
            </span>
            <div className="flex flex-col gap-2">
              <span className="text-[10px] text-indigo-400 font-bold uppercase tracking-widest">Pro Researcher</span>
              <h3 className="text-2xl font-black text-slate-100">$29 <span className="text-xs font-normal text-slate-400">/ month</span></h3>
              <p className="text-xs text-slate-400">Full linguistic metrics & dynamic rephrasing.</p>
              <ul className="text-xs text-slate-300 flex flex-col gap-2 mt-4">
                <li className="flex items-center gap-2"><CheckCircle2 size={14} className="text-indigo-400" /> Unlimited file uploads</li>
                <li className="flex items-center gap-2"><CheckCircle2 size={14} className="text-indigo-400" /> 8 Rephrasing models</li>
                <li className="flex items-center gap-2"><CheckCircle2 size={14} className="text-indigo-400" /> Formula & Citation Preserving</li>
                <li className="flex items-center gap-2"><CheckCircle2 size={14} className="text-indigo-400" /> Advanced Developer Panel stats</li>
              </ul>
            </div>
            <button onClick={handleGetStarted} className="w-full bg-indigo-600 hover:bg-indigo-700 text-white text-xs font-bold py-3 rounded-xl transition-all shadow-md shadow-indigo-500/10">
              Upgrade to Pro
            </button>
          </div>

          {/* Plan 3 */}
          <div className="bg-slate-900/20 backdrop-blur-md border border-slate-800/80 p-6 rounded-3xl flex flex-col gap-6 justify-between shadow-md">
            <div className="flex flex-col gap-2">
              <span className="text-[10px] text-slate-400 font-bold uppercase tracking-widest">Institutional</span>
              <h3 className="text-2xl font-black text-slate-100">Custom <span className="text-xs font-normal text-slate-400">/ tailored</span></h3>
              <p className="text-xs text-slate-400">API integration for research groups.</p>
              <ul className="text-xs text-slate-300 flex flex-col gap-2 mt-4">
                <li className="flex items-center gap-2"><CheckCircle2 size={14} className="text-blue-400" /> Multi-user seat controls</li>
                <li className="flex items-center gap-2"><CheckCircle2 size={14} className="text-blue-400" /> Team workspaces & API keys</li>
                <li className="flex items-center gap-2"><CheckCircle2 size={14} className="text-blue-400" /> Private on-premises deployment</li>
              </ul>
            </div>
            <button onClick={handleGetStarted} className="w-full bg-slate-800 hover:bg-slate-750 text-slate-200 text-xs font-bold py-3 rounded-xl border border-slate-700/50 mt-4 transition-all">
              Contact Support
            </button>
          </div>
        </div>
      </section>

      {/* Professional Footer */}
      <footer className="w-full border-t border-slate-900 py-12 px-6 mt-16 bg-slate-950/20 relative z-20">
        <div className="max-w-7xl mx-auto flex flex-col md:flex-row justify-between items-center gap-6">
          <div className="flex items-center gap-3">
            <div className="bg-slate-900 p-2 rounded-xl text-indigo-400 border border-slate-800">
              <ShieldCheck size={18} />
            </div>
            <div>
              <span className="text-sm font-bold tracking-tight text-slate-100">LEXORA</span>
              <p className="text-[9px] text-slate-500">Writing Intelligence Platform</p>
            </div>
          </div>

          <div className="flex items-center gap-6 text-xs text-slate-400">
            <a href="#" className="hover:text-white transition-colors">Workspace Policy</a>
            <a href="#" className="hover:text-white transition-colors">Privacy Principles</a>
            <a href="#" className="hover:text-white transition-colors">Academic Integrity</a>
          </div>

          <p className="text-[10px] text-slate-500">
            © 2026 Lexora. All rights reserved.
          </p>
        </div>
      </footer>
    </div>
  );
}
