"use client";

import { useState } from "react";
import { Sparkles, Layers, ArrowLeftRight, CheckCircle2, ShieldCheck, HeartPulse, ChevronDown } from "lucide-react";
import Navbar from "@/components/navbar";
import Sidebar from "@/components/sidebar";

interface DropdownOption {
  value: string;
  label: string;
}

interface CustomDropdownProps {
  options: DropdownOption[];
  value: string;
  onChange: (value: string) => void;
  label: string;
}

function CustomDropdown({ options, value, onChange, label }: CustomDropdownProps) {
  const [isOpen, setIsOpen] = useState(false);
  const selectedOption = options.find(o => o.value === value) || options[0];

  return (
    <div className="flex flex-col gap-1 relative w-full select-none">
      <label className="text-gray-400 font-semibold">{label}</label>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between w-full bg-slate-900/50 hover:bg-slate-900 border border-border rounded-xl px-3 py-2 text-foreground text-xs focus:outline-none transition-all duration-205"
      >
        <span className="truncate">{selectedOption.label}</span>
        <ChevronDown size={14} className={`text-gray-400 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <>
          <div className="fixed inset-0 z-40 cursor-default" onClick={() => setIsOpen(false)} />
          <div className="absolute top-[58px] left-0 w-full bg-[#0F172A] border border-slate-700/60 rounded-xl shadow-2xl z-50 py-1.5 overflow-hidden animate-slideIn">
            <div className="max-h-60 overflow-y-auto">
              {options.map((opt) => {
                const isSelected = opt.value === value;
                return (
                  <button
                    key={opt.value}
                    type="button"
                    onClick={() => {
                      onChange(opt.value);
                      setIsOpen(false);
                    }}
                    className={`w-full text-left px-3 py-2 text-xs transition-all duration-150 flex items-center justify-between ${
                      isSelected
                        ? "bg-primary text-white font-bold"
                        : "text-gray-200 hover:bg-primary/20 hover:text-white"
                    }`}
                  >
                    <span className="truncate">{opt.label}</span>
                  </button>
                );
              })}
            </div>
          </div>
        </>
      )}
    </div>
  );
}

const REPHRASE_OPTIONS = [
  { value: "Academic", label: "Academic Rephrase" },
  { value: "Journal Submission Style", label: "Journal Submission Style" },
  { value: "Formal Writing", label: "Formal Writing" },
  { value: "Concise Writing", label: "Concise Writing" },
  { value: "Expanded Writing", label: "Expanded Writing" },
  { value: "Simplified Writing", label: "Simplified Writing" },
  { value: "Technical Writing", label: "Technical Writing" }
];

const HUMANIZER_OPTIONS = [
  { value: "Academic Humanizer", label: "Academic Humanizer" },
  { value: "Natural Humanizer", label: "Natural Humanizer" },
  { value: "Reviewer-Friendly Humanizer", label: "Reviewer-Friendly Humanizer" },
  { value: "Journal-Ready Humanizer", label: "Journal-Ready Humanizer" }
];

export default function RephrasePage() {
  // Input/Output states
  const [inputText, setInputText] = useState("");
  const [outputText, setOutputText] = useState("");
  
  // Rephrase settings
  const [rephraseMode, setRephraseMode] = useState("Academic");
  const [rephraseLevel, setRephraseLevel] = useState("Medium");
  const [similarity, setSimilarity] = useState<number | null>(null);
  const [preservations, setPreservations] = useState<any>(null);
  
  // Humanizer settings
  const [humanizerMode, setHumanizerMode] = useState("Academic Humanizer");
  const [humanizerLevel, setHumanizerLevel] = useState("Medium");
  const [riskBefore, setRiskBefore] = useState<number | null>(null);
  const [riskAfter, setRiskAfter] = useState<number | null>(null);

  // Load state
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Word count consistency state
  const [wordCountOriginal, setWordCountOriginal] = useState<number | null>(null);
  const [wordCountRewritten, setWordCountRewritten] = useState<number | null>(null);
  const [wordCountConsistent, setWordCountConsistent] = useState<boolean | null>(null);

  // Intensity debug telemetry
  const [transformationsApplied, setTransformationsApplied] = useState<number | null>(null);
  const [sentencesModified, setSentencesModified] = useState<number | null>(null);
  const [sentencesTotal, setSentencesTotal] = useState<number | null>(null);
  const [modificationPct, setModificationPct] = useState<number | null>(null);
  const [activeLevel, setActiveLevel] = useState<string | null>(null);
  const [activeMode, setActiveMode] = useState<string | null>(null);
  const [activeOperation, setActiveOperation] = useState<"rephrase" | "humanize" | null>(null);

  // Quality metrics state
  const [phraseSubstitutionsApplied, setPhraseSubstitutionsApplied] = useState<number | null>(null);
  const [synonymSubstitutionsApplied, setSynonymSubstitutionsApplied] = useState<number | null>(null);
  const [structuralRewritesApplied, setStructuralRewritesApplied] = useState<number | null>(null);
  const [protectedEntitiesPreservedCount, setProtectedEntitiesPreservedCount] = useState<number | null>(null);
  const [processingTimeMs, setProcessingTimeMs] = useState<number | null>(null);
  const [lexicalDiversityDelta, setLexicalDiversityDelta] = useState<number | null>(null);

  const handleRephrase = async () => {
    if (!inputText.trim()) return;
    setLoading(true);
    setError(null);
    setOutputText("");
    setSimilarity(null);
    setRiskBefore(null);
    setRiskAfter(null);
    setWordCountOriginal(null);
    setWordCountRewritten(null);
    setWordCountConsistent(null);
    setTransformationsApplied(null);
    setSentencesModified(null);
    setSentencesTotal(null);
    setModificationPct(null);
    setActiveLevel(null);
    setActiveMode(null);
    setActiveOperation(null);
    setPhraseSubstitutionsApplied(null);
    setSynonymSubstitutionsApplied(null);
    setStructuralRewritesApplied(null);
    setProtectedEntitiesPreservedCount(null);
    setProcessingTimeMs(null);
    setLexicalDiversityDelta(null);

    const token = localStorage.getItem("token");
    try {
      const response = await fetch("http://localhost:8000/api/v1/rephrase", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          text: inputText,
          mode: rephraseMode,
          level: rephraseLevel
        })
      });

      if (!response.ok) throw new Error("Paraphrase request failed");
      const data = await response.json();
      
      setOutputText(data.rewritten_text);
      setSimilarity(data.similarity_percentage);
      setPreservations(data.preservations);
      setWordCountOriginal(data.word_count_original);
      setWordCountRewritten(data.word_count_rewritten);
      setWordCountConsistent(data.word_count_consistent);
      setTransformationsApplied(data.transformations_applied ?? null);
      setSentencesModified(data.sentences_modified ?? null);
      setSentencesTotal(data.sentences_total ?? null);
      setModificationPct(data.modification_percentage ?? null);
      setPhraseSubstitutionsApplied(data.phrase_substitutions_applied ?? null);
      setSynonymSubstitutionsApplied(data.synonym_substitutions_applied ?? null);
      setStructuralRewritesApplied(data.structural_rewrites_applied ?? null);
      setProtectedEntitiesPreservedCount(data.protected_entities_preserved_count ?? null);
      setProcessingTimeMs(data.processing_time_ms ?? null);
      setLexicalDiversityDelta(data.lexical_diversity_delta ?? null);
      setActiveLevel(rephraseLevel);
      setActiveMode(rephraseMode);
      setActiveOperation("rephrase");
    } catch (err: any) {
      setError(err.message || "Could not rephrase text selection.");
    } finally {
      setLoading(false);
    }
  };

  const handleHumanize = async () => {
    if (!inputText.trim()) return;
    setLoading(true);
    setError(null);
    setOutputText("");
    setSimilarity(null);
    setPreservations(null);
    setWordCountOriginal(null);
    setWordCountRewritten(null);
    setWordCountConsistent(null);
    setTransformationsApplied(null);
    setSentencesModified(null);
    setSentencesTotal(null);
    setModificationPct(null);
    setActiveLevel(null);
    setActiveMode(null);
    setActiveOperation(null);
    setPhraseSubstitutionsApplied(null);
    setSynonymSubstitutionsApplied(null);
    setStructuralRewritesApplied(null);
    setProtectedEntitiesPreservedCount(null);
    setProcessingTimeMs(null);
    setLexicalDiversityDelta(null);

    const token = localStorage.getItem("token");
    try {
      const response = await fetch("http://localhost:8000/api/v1/humanize", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          text: inputText,
          mode: humanizerMode,
          level: humanizerLevel
        })
      });

      if (!response.ok) throw new Error("Humanizer request failed");
      const data = await response.json();
      
      setOutputText(data.rewritten_text);
      setSimilarity(data.similarity_percentage);
      setRiskBefore(data.overall_risk_before);
      setRiskAfter(data.overall_risk_after);
      setWordCountOriginal(data.word_count_original);
      setWordCountRewritten(data.word_count_rewritten);
      setWordCountConsistent(data.word_count_consistent);
      setTransformationsApplied(data.transformations_applied ?? null);
      setSentencesModified(data.sentences_modified ?? null);
      setSentencesTotal(data.sentences_total ?? null);
      setModificationPct(data.modification_percentage ?? null);
      setActiveLevel(humanizerLevel);
      setActiveMode(humanizerMode);
      setActiveOperation("humanize");
    } catch (err: any) {
      setError(err.message || "Could not optimize styling characteristics.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col min-h-screen bg-background text-foreground">
      <Navbar />

      <div className="flex flex-1">
        <Sidebar />

        <main className="flex-1 p-6 md:p-8 flex flex-col gap-8 max-w-7xl mx-auto w-full">
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight">Style Optimization Studio</h1>
            <p className="text-xs text-gray-400 mt-1">
              Select specific academic levels or trigger humanizing syntactic pacing (burstiness).
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-3 gap-8 items-start">
            {/* Control Panel Settings */}
            <div className="flex flex-col gap-6">
              {/* Paraphrasing configurations */}
              <div className="glass-panel border border-border p-6 rounded-3xl flex flex-col gap-4">
                <h2 className="text-sm font-bold uppercase tracking-wider flex items-center gap-2 pb-2 border-b border-border">
                  <ArrowLeftRight size={18} className="text-primary" />
                  Paraphraser Modes
                </h2>

                <div className="flex flex-col gap-3 text-xs">
                  <CustomDropdown
                    label="Paraphrasing Strategy"
                    options={REPHRASE_OPTIONS}
                    value={rephraseMode}
                    onChange={setRephraseMode}
                  />

                  <div className="flex flex-col gap-1">
                    <label className="text-gray-400 font-semibold">Intensity Level</label>
                    <div className="grid grid-cols-4 gap-1.5 mt-1 bg-gray-500/5 p-1 rounded-xl border border-border">
                      {["Low", "Medium", "High", "Aggressive"].map((lvl) => (
                        <button
                          key={lvl}
                          onClick={() => setRephraseLevel(lvl)}
                          className={`py-1.5 rounded-lg font-bold text-[10px] uppercase text-center transition-all ${
                            rephraseLevel === lvl ? "bg-primary text-white" : "text-gray-400 hover:text-foreground"
                          }`}
                        >
                          {lvl}
                        </button>
                      ))}
                    </div>
                  </div>

                  <button
                    onClick={handleRephrase}
                    disabled={loading}
                    className="w-full bg-primary hover:bg-primary-hover text-white py-2.5 rounded-2xl flex items-center justify-center gap-2 font-bold mt-2 transition-all hover:scale-[1.02] shadow-md shadow-primary/15 disabled:opacity-50"
                  >
                    {loading ? (
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    ) : (
                      <Sparkles size={16} />
                    )}
                    {loading ? "Processing..." : "Run Paraphraser"}
                  </button>
                </div>
              </div>

              {/* Humanizer configurations */}
              <div className="glass-panel border border-border p-6 rounded-3xl flex flex-col gap-4">
                <h2 className="text-sm font-bold uppercase tracking-wider flex items-center gap-2 pb-2 border-b border-border">
                  <Layers size={18} className="text-purple-400" />
                  Stylistic Humanizer
                </h2>

                <div className="flex flex-col gap-3 text-xs">
                  <CustomDropdown
                    label="Optimization Profile"
                    options={HUMANIZER_OPTIONS}
                    value={humanizerMode}
                    onChange={setHumanizerMode}
                  />

                  <div className="flex flex-col gap-1">
                    <label className="text-gray-400 font-semibold">Intensity Level</label>
                    <div className="grid grid-cols-3 gap-1.5 mt-1 bg-gray-500/5 p-1 rounded-xl border border-border">
                      {["Low", "Medium", "High"].map((lvl) => (
                        <button
                          key={lvl}
                          onClick={() => setHumanizerLevel(lvl)}
                          className={`py-1.5 rounded-lg font-bold text-[10px] uppercase text-center transition-all ${
                            humanizerLevel === lvl
                              ? lvl === "Low" ? "bg-emerald-600 text-white"
                                : lvl === "Medium" ? "bg-amber-500 text-white"
                                : "bg-rose-600 text-white"
                              : "text-gray-400 hover:text-foreground"
                          }`}
                        >
                          {lvl}
                        </button>
                      ))}
                    </div>
                    <p className="text-[9px] text-gray-500 mt-0.5">
                      {humanizerLevel === "Low" && "5–10% modification · Cliché strip only"}
                      {humanizerLevel === "Medium" && "15–30% modification · Burstiness + synonyms"}
                      {humanizerLevel === "High" && "40–60% modification · Aggressive restructuring"}
                    </p>
                  </div>

                  <button
                    onClick={handleHumanize}
                    disabled={loading}
                    className="w-full bg-purple-600 hover:bg-purple-700 text-white py-2.5 rounded-2xl flex items-center justify-center gap-2 font-bold mt-2 transition-all hover:scale-[1.02] shadow-md shadow-purple-500/15 disabled:opacity-50"
                  >
                    {loading ? (
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                    ) : (
                      <HeartPulse size={16} />
                    )}
                    {loading ? "Optimizing..." : "Execute Humanizer"}
                  </button>
                </div>
              </div>
            </div>

            {/* Editing Pane (Original vs Paraphrased) */}
            <div className="lg:col-span-2 flex flex-col gap-6">
              {/* Telemetry Output HUD */}
              {(similarity !== null || riskBefore !== null || wordCountConsistent !== null) && (
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4 animate-slideIn">
                  {similarity !== null && (
                    <div className="glass-panel border border-border p-4 rounded-2xl flex items-center gap-3">
                      <div className="bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 p-2 rounded-xl">
                        <ShieldCheck size={20} />
                      </div>
                      <div>
                        <p className="text-[9px] text-gray-400 uppercase tracking-widest font-bold">Semantic Overlap</p>
                        <h4 className="text-sm font-black text-emerald-400">{similarity}% Plagiarism-Safe</h4>
                      </div>
                    </div>
                  )}

                  {riskBefore !== null && riskAfter !== null && (
                    <div className="glass-panel border border-border p-4 rounded-2xl flex items-center gap-3">
                      <div className="bg-purple-500/10 text-purple-400 border border-purple-500/20 p-2 rounded-xl">
                        <HeartPulse size={20} />
                      </div>
                      <div>
                        <p className="text-[9px] text-gray-400 uppercase tracking-widest font-bold">AI Risk Signature</p>
                        <h4 className="text-sm font-black text-purple-400">
                          {riskBefore}% → {riskAfter}%
                        </h4>
                      </div>
                    </div>
                  )}

                  {wordCountConsistent !== null && (
                    <div className="glass-panel border border-border p-4 rounded-2xl flex items-center gap-3">
                      <div className={`p-2 rounded-xl ${wordCountConsistent ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/20' : 'bg-amber-500/10 text-amber-400 border border-amber-500/20'}`}>
                        <CheckCircle2 size={20} />
                      </div>
                      <div>
                        <p className="text-[9px] text-gray-400 uppercase tracking-widest font-bold">Word Consistency</p>
                        <h4 className={`text-sm font-black ${wordCountConsistent ? 'text-emerald-400' : 'text-amber-400'}`}>
                          {wordCountConsistent ? 'Consistent ✓' : 'Variance Warning ⚠'}
                        </h4>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Intensity Debug Telemetry Panel */}
              {transformationsApplied !== null && (
                <div className="glass-panel border border-indigo-500/20 bg-indigo-500/5 p-5 rounded-2xl flex flex-col gap-3 animate-slideIn">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-indigo-400 animate-pulse" />
                    <h3 className="text-[10px] font-bold uppercase tracking-widest text-indigo-300">Transformation Debug</h3>
                    <span className={`ml-auto text-[9px] font-bold px-2 py-0.5 rounded-full ${
                      activeLevel === "Low" ? "bg-emerald-500/20 text-emerald-300"
                      : activeLevel === "Medium" ? "bg-amber-500/20 text-amber-300"
                      : "bg-rose-500/20 text-rose-300"
                    }`}>{activeLevel} Intensity · {activeOperation === "humanize" ? "Humanizer" : "Paraphraser"}</span>
                  </div>
                  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
                    <div className="bg-slate-900/60 border border-slate-700/50 rounded-xl p-3 text-center">
                      <p className="text-[9px] text-gray-400 uppercase tracking-wider font-semibold mb-1">Transformations</p>
                      <p className="text-lg font-black text-indigo-300">{transformationsApplied}</p>
                    </div>
                    <div className="bg-slate-900/60 border border-slate-700/50 rounded-xl p-3 text-center">
                      <p className="text-[9px] text-gray-400 uppercase tracking-wider font-semibold mb-1">Sentences Modified</p>
                      <p className="text-lg font-black text-indigo-300">{sentencesModified}<span className="text-xs text-gray-500">/{sentencesTotal}</span></p>
                    </div>
                    <div className="bg-slate-900/60 border border-slate-700/50 rounded-xl p-3 text-center">
                      <p className="text-[9px] text-gray-400 uppercase tracking-wider font-semibold mb-1">Modification %</p>
                      <p className={`text-lg font-black ${
                        (modificationPct ?? 0) >= 40 ? "text-rose-400"
                        : (modificationPct ?? 0) >= 15 ? "text-amber-400"
                        : "text-emerald-400"
                      }`}>{modificationPct}%</p>
                    </div>
                    <div className="bg-slate-900/60 border border-slate-700/50 rounded-xl p-3 text-center">
                      <p className="text-[9px] text-gray-400 uppercase tracking-wider font-semibold mb-1">Words</p>
                      <p className="text-lg font-black text-indigo-300">{wordCountOriginal}<span className="text-gray-500 text-xs">→</span>{wordCountRewritten}</p>
                    </div>
                  </div>
                  {/* Visual intensity progress bar */}
                  <div className="flex flex-col gap-1">
                    <div className="flex justify-between text-[9px] text-gray-500">
                      <span>0%</span>
                      <span className="text-gray-400 font-semibold">{activeLevel} target range: {activeLevel === "Low" ? "5–10%" : activeLevel === "Medium" ? "15–30%" : "40–60%"}</span>
                      <span>60%+</span>
                    </div>
                    <div className="h-1.5 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-700 ${
                          (modificationPct ?? 0) >= 40 ? "bg-rose-500"
                          : (modificationPct ?? 0) >= 15 ? "bg-amber-500"
                          : "bg-emerald-500"
                        }`}
                        style={{ width: `${Math.min(100, ((modificationPct ?? 0) / 60) * 100)}%` }}
                      />
                    </div>
                  </div>

                  {activeOperation === "rephrase" && phraseSubstitutionsApplied !== null && (
                    <div className="grid grid-cols-2 md:grid-cols-3 gap-2.5 pt-3 mt-1 border-t border-indigo-500/15 text-[10px] text-gray-300">
                      <div className="flex justify-between items-center px-3 py-1.5 bg-slate-900/60 border border-slate-800/80 rounded-xl">
                        <span className="text-gray-400 font-semibold">Phrase Rewrites:</span>
                        <span className="font-extrabold text-indigo-300">{phraseSubstitutionsApplied}</span>
                      </div>
                      <div className="flex justify-between items-center px-3 py-1.5 bg-slate-900/60 border border-slate-800/80 rounded-xl">
                        <span className="text-gray-400 font-semibold">Synonym Swaps:</span>
                        <span className="font-extrabold text-indigo-300">{synonymSubstitutionsApplied}</span>
                      </div>
                      <div className="flex justify-between items-center px-3 py-1.5 bg-slate-900/60 border border-slate-800/80 rounded-xl">
                        <span className="text-gray-400 font-semibold">Structural Edits:</span>
                        <span className="font-extrabold text-indigo-300">{structuralRewritesApplied}</span>
                      </div>
                      <div className="flex justify-between items-center px-3 py-1.5 bg-slate-900/60 border border-slate-800/80 rounded-xl">
                        <span className="text-gray-400 font-semibold">Protected Constants:</span>
                        <span className="font-extrabold text-emerald-400">{protectedEntitiesPreservedCount}</span>
                      </div>
                      <div className="flex justify-between items-center px-3 py-1.5 bg-slate-900/60 border border-slate-800/80 rounded-xl">
                        <span className="text-gray-400 font-semibold">Lexical Diversity Delta:</span>
                        <span className={`font-extrabold ${lexicalDiversityDelta !== null && lexicalDiversityDelta > 0 ? "text-emerald-400" : lexicalDiversityDelta !== null && lexicalDiversityDelta < 0 ? "text-rose-400" : "text-gray-400"}`}>
                          {lexicalDiversityDelta !== null && lexicalDiversityDelta > 0 ? `+${lexicalDiversityDelta}` : lexicalDiversityDelta}
                        </span>
                      </div>
                      <div className="flex justify-between items-center px-3 py-1.5 bg-slate-900/60 border border-slate-800/80 rounded-xl">
                        <span className="text-gray-400 font-semibold">Processing Speed:</span>
                        <span className="font-extrabold text-indigo-300">{processingTimeMs}ms</span>
                      </div>
                    </div>
                  )}

                </div>
              )}

              {/* Text Blocks */}
              <div className="flex flex-col md:flex-row gap-6 w-full items-stretch">
                {/* Input Text Box */}
                <div className="flex-1 glass-panel border border-border p-5 rounded-3xl flex flex-col gap-3 min-h-[300px]">
                  <p className="text-[10px] text-gray-400 uppercase font-bold tracking-widest">
                    Original Draft text
                  </p>
                  <textarea
                    value={inputText}
                    onChange={(e) => setInputText(e.target.value)}
                    placeholder="Paste your paragraph or research section here..."
                    className="flex-1 bg-transparent border-0 p-0 text-xs leading-relaxed text-foreground resize-none focus:outline-none focus:ring-0 min-h-[250px]"
                  />
                  <div className="flex justify-between items-center text-[10px] text-gray-400 select-none">
                    <span>{inputText.split(/\s+/).filter(Boolean).length} Words</span>
                    <span>Supports math/citations preservation</span>
                  </div>
                </div>

                {/* Output Text Box */}
                <div className="flex-1 glass-panel border border-border p-5 rounded-3xl flex flex-col gap-3 min-h-[300px] relative">
                  <p className="text-[10px] text-gray-400 uppercase font-bold tracking-widest">
                    Optimized academic output
                  </p>
                  
                  {loading ? (
                    <div className="flex-1 flex flex-col items-center justify-center gap-2 select-none">
                      <div className="w-8 h-8 border-4 border-primary border-t-transparent rounded-full animate-spin" />
                      <span className="text-[10px] font-bold text-gray-400">Restructuring syntax...</span>
                    </div>
                  ) : (
                    <textarea
                      readOnly
                      value={outputText}
                      placeholder="Your optimized, human-pitted phrasing matches will appear here..."
                      className="flex-1 bg-transparent border-0 p-0 text-xs leading-relaxed text-foreground resize-none focus:outline-none focus:ring-0 min-h-[250px]"
                    />
                  )}

                  <div className="flex justify-between items-center text-[10px] text-gray-400 select-none">
                    <span>{outputText.split(/\s+/).filter(Boolean).length} Words</span>
                    {outputText && (
                      <button
                        onClick={() => {
                          navigator.clipboard.writeText(outputText);
                          alert("Text copied to clipboard!");
                        }}
                        className="text-primary hover:underline font-semibold"
                      >
                        Copy Output
                      </button>
                    )}
                  </div>
                </div>
              </div>

              {/* Saved Citations Preserved Display */}
              {preservations && (preservations.math.length > 0 || preservations.citations.length > 0) && (
                <div className="glass-panel border border-border p-5 rounded-3xl flex flex-col gap-3 animate-slideIn">
                  <h3 className="text-xs font-bold uppercase tracking-wider text-gray-300">
                    Preserved Academic Constants
                  </h3>
                  <div className="flex flex-wrap gap-2 text-[10px]">
                    {preservations.citations.map((c: string, idx: number) => (
                      <span key={idx} className="bg-indigo-500/10 border border-indigo-500/20 text-indigo-300 px-2 py-1 rounded-lg">
                        Citation: {c}
                      </span>
                    ))}
                    {preservations.math.map((m: string, idx: number) => (
                      <span key={idx} className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-300 px-2 py-1 rounded-lg">
                        Formula: {m}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
