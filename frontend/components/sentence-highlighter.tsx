"use client";

import { useState } from "react";
import { Sparkles, HelpCircle, ArrowRight, ShieldAlert, BadgeCheck } from "lucide-react";

interface SentenceData {
  sentence: string;
  score: number;
  category: string;
  reasons: string[];
  improvement_suggestions: string[];
  stats: {
    words: number;
    passive_count: number;
    transition_count: number;
    cliche_count: number;
  };
}

interface SentenceHighlighterProps {
  sentences: SentenceData[];
  onSentenceOptimize?: (original: string, optimized: string) => void;
  documentRiskDetails?: any;
}

export default function SentenceHighlighter({ sentences, onSentenceOptimize, documentRiskDetails }: SentenceHighlighterProps) {
  const [selectedSentence, setSelectedSentence] = useState<SentenceData | null>(null);
  const [optimizing, setOptimizing] = useState(false);
  const [optimizedResult, setOptimizedResult] = useState<string | null>(null);

  const getRiskColor = (score: number) => {
    if (score <= 25) return "bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-800 dark:text-emerald-300 border-b-2 border-emerald-500/30";
    if (score <= 45) return "bg-yellow-500/10 hover:bg-yellow-500/20 text-yellow-800 dark:text-yellow-300 border-b-2 border-yellow-500/30";
    if (score <= 70) return "bg-orange-500/10 hover:bg-orange-500/20 text-orange-800 dark:text-orange-300 border-b-2 border-orange-500/30";
    return "bg-red-500/10 hover:bg-red-500/20 text-red-800 dark:text-red-400 border-b-2 border-red-500/50 font-medium";
  };

  const handleQuickOptimize = async (sentText: string) => {
    setOptimizing(true);
    setOptimizedResult(null);
    try {
      const token = localStorage.getItem("token");
      const response = await fetch("http://localhost:8000/api/v1/humanize", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          text: sentText,
          mode: "Academic Humanizer"
        })
      });

      if (!response.ok) throw new Error("Optimization failed");
      const data = await response.json();
      setOptimizedResult(data.rewritten_text);
      if (onSentenceOptimize) {
        onSentenceOptimize(sentText, data.rewritten_text);
      }
    } catch (err) {
      console.error(err);
    } finally {
      setOptimizing(false);
    }
  };

  return (
    <div className="flex flex-col xl:flex-row gap-6 w-full items-start">
      {/* Scrollable Highlight Panel */}
      <div className="glass-panel border border-border p-6 rounded-3xl w-full xl:flex-1 max-h-[500px] overflow-y-auto leading-relaxed text-sm select-text">
        <p className="text-xs text-gray-400 mb-4 italic select-none">
          Click any highlighted sentence to review custom suggestions, active syntactic features, or trigger humanizing rewrites.
        </p>
        <div className="space-x-1">
          {sentences.map((item, idx) => (
            <span
              key={idx}
              onClick={() => {
                setSelectedSentence(item);
                setOptimizedResult(null);
              }}
              className={`inline-block py-0.5 px-1 rounded cursor-pointer transition-all duration-200 hover:scale-[1.01] ${getRiskColor(item.score)}`}
            >
              {item.sentence}{" "}
            </span>
          ))}
        </div>
      </div>

      {/* Interactive Explanation Sidebar */}
      <div className="w-full xl:w-96 shrink-0">
        {selectedSentence ? (
          <div className="glass-panel border border-border rounded-3xl p-6 flex flex-col gap-4 animate-slideIn">
            <div className="flex justify-between items-center border-b border-border pb-3">
              <h3 className="text-sm font-bold text-foreground flex items-center gap-2">
                <ShieldAlert size={18} className="text-primary" />
                Linguistic Inspection
              </h3>
              <span className={`text-[10px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full ${
                selectedSentence.score <= 25 ? "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20" :
                selectedSentence.score <= 45 ? "bg-yellow-500/10 text-yellow-400 border border-yellow-500/20" :
                selectedSentence.score <= 70 ? "bg-orange-500/10 text-orange-400 border border-orange-500/20" :
                "bg-red-500/10 text-red-400 border border-red-500/20 animate-pulse"
              }`}>
                {selectedSentence.category} Risk ({selectedSentence.score}%)
              </span>
            </div>

            <div>
              <p className="text-xs text-gray-400 uppercase tracking-widest font-semibold mb-1">
                Target Sentence
              </p>
              <p className="text-xs italic bg-gray-500/5 p-3 rounded-2xl border border-border dark:text-gray-300">
                "{selectedSentence.sentence}"
              </p>
            </div>

            {/* Statistics */}
            <div>
              <p className="text-xs text-gray-400 uppercase tracking-widest font-semibold mb-2">
                Linguistic Metrics
              </p>
              <div className="grid grid-cols-2 gap-2 text-[10px]">
                <div className="bg-gray-500/5 p-2 rounded-xl border border-border">
                  <span className="text-gray-400">Word Count:</span>
                  <span className="float-right font-bold text-foreground">{selectedSentence.stats.words}</span>
                </div>
                <div className="bg-gray-500/5 p-2 rounded-xl border border-border">
                  <span className="text-gray-400">Passive Verbs:</span>
                  <span className="float-right font-bold text-foreground">{selectedSentence.stats.passive_count}</span>
                </div>
                <div className="bg-gray-500/5 p-2 rounded-xl border border-border">
                  <span className="text-gray-400">AI cliché density:</span>
                  <span className="float-right font-bold text-foreground">{selectedSentence.stats.cliche_count}</span>
                </div>
                <div className="bg-gray-500/5 p-2 rounded-xl border border-border">
                  <span className="text-gray-400">Transition density:</span>
                  <span className="float-right font-bold text-foreground">{selectedSentence.stats.transition_count}</span>
                </div>
              </div>
            </div>

            {/* Flag reasons */}
            {selectedSentence.reasons.length > 0 && (
              <div>
                <p className="text-xs text-gray-400 uppercase tracking-widest font-semibold mb-1">
                  Stylistic Flags
                </p>
                <ul className="text-xs text-foreground flex flex-col gap-1 list-disc pl-4">
                  {selectedSentence.reasons.map((reason, idx) => (
                    <li key={idx} className="text-red-400">{reason}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* Actionable suggestions */}
            {selectedSentence.improvement_suggestions.length > 0 && (
              <div>
                <p className="text-xs text-gray-400 uppercase tracking-widest font-semibold mb-1">
                  Improvement Actions
                </p>
                <ul className="text-xs text-foreground flex flex-col gap-1 list-disc pl-4">
                  {selectedSentence.improvement_suggestions.map((sug, idx) => (
                    <li key={idx} className="text-emerald-400">{sug}</li>
                  ))}
                </ul>
              </div>
            )}

            {/* AI Humanize rewrites */}
            <div className="border-t border-border pt-4">
              {!optimizedResult ? (
                <button
                  onClick={() => handleQuickOptimize(selectedSentence.sentence)}
                  disabled={optimizing}
                  className="w-full bg-primary hover:bg-primary-hover text-white text-xs font-bold py-2.5 rounded-2xl flex items-center justify-center gap-2 transition-all hover:scale-[1.02] disabled:opacity-50"
                >
                  <Sparkles size={16} />
                  {optimizing ? "Generating Rephraser output..." : "Direct Humanizer Paraphrase"}
                </button>
              ) : (
                <div className="flex flex-col gap-2">
                  <p className="text-[10px] text-emerald-400 uppercase tracking-widest font-semibold flex items-center gap-1">
                    <BadgeCheck size={14} /> Optimized Humanized text
                  </p>
                  <p className="text-xs bg-emerald-500/5 p-3 rounded-2xl border border-emerald-500/20 text-emerald-300 italic">
                    "{optimizedResult}"
                  </p>
                </div>
              )}
            </div>
            {/* Developer accordion fallback */}
            {documentRiskDetails && (
              <details className="border-t border-border pt-3 mt-1">
                <summary className="text-[10px] text-gray-400 uppercase tracking-widest font-bold cursor-pointer hover:text-foreground select-none">
                  Inspect Global Metrics
                </summary>
                <div className="grid grid-cols-2 gap-2 text-[10px] mt-2">
                  <div className="bg-gray-500/5 p-2 rounded-xl border border-border">
                    <span className="text-gray-400">Perplexity:</span>
                    <span className="float-right font-bold text-foreground">{documentRiskDetails.perplexity_score ?? "N/A"}</span>
                  </div>
                  <div className="bg-gray-500/5 p-2 rounded-xl border border-border">
                    <span className="text-gray-400">Entropy:</span>
                    <span className="float-right font-bold text-foreground">{documentRiskDetails.entropy_score ?? "N/A"}</span>
                  </div>
                  <div className="bg-gray-500/5 p-2 rounded-xl border border-border">
                    <span className="text-gray-400">Repetition Score:</span>
                    <span className="float-right font-bold text-foreground">{documentRiskDetails.repetition_score ?? "N/A"}%</span>
                  </div>
                  <div className="bg-gray-500/5 p-2 rounded-xl border border-border">
                    <span className="text-gray-400">N-gram Predict:</span>
                    <span className="float-right font-bold text-foreground">{documentRiskDetails.ngram_predictability ?? "N/A"}%</span>
                  </div>
                </div>
              </details>
            )}
          </div>
        ) : (
          <div className="flex flex-col gap-6">
            <div className="glass-panel border border-border border-dashed rounded-3xl p-8 text-center flex flex-col items-center justify-center gap-3">
              <div className="bg-gray-500/10 p-3 rounded-full text-gray-400">
                <HelpCircle size={28} />
              </div>
              <h4 className="text-sm font-bold text-foreground">No sentence chosen</h4>
              <p className="text-xs text-gray-400 max-w-[200px]">
                Tap any colored academic block in the inspector panel to see metrics.
              </p>
            </div>

            {documentRiskDetails && (
              <div className="glass-panel border border-border rounded-3xl p-6 flex flex-col gap-4 animate-slideIn">
                <h3 className="text-sm font-bold text-foreground border-b border-border pb-3 flex items-center gap-2">
                  <span className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                  Linguistic Developer Panel
                </h3>
                
                <div className="flex flex-col gap-3">
                  {documentRiskDetails.document_reasoning && documentRiskDetails.document_reasoning.length > 0 && (
                    <div className="bg-primary/5 p-3 rounded-2xl border border-primary/20 text-[10px] text-primary leading-normal">
                      <strong>AI Risk Logic:</strong> {documentRiskDetails.document_reasoning[0]}
                    </div>
                  )}

                  <div className="flex flex-col gap-2">
                    <p className="text-[10px] text-gray-400 uppercase tracking-widest font-bold">Raw Features Dump</p>
                    <div className="grid grid-cols-2 gap-2 text-[10px]">
                      <div className="bg-gray-500/5 p-2 rounded-xl border border-border">
                        <span className="text-gray-400">Perplexity:</span>
                        <span className="float-right font-bold text-foreground">{documentRiskDetails.perplexity_score ?? "N/A"}</span>
                      </div>
                      <div className="bg-gray-500/5 p-2 rounded-xl border border-border">
                        <span className="text-gray-400">Entropy:</span>
                        <span className="float-right font-bold text-foreground">{documentRiskDetails.entropy_score ?? "N/A"}</span>
                      </div>
                      <div className="bg-gray-500/5 p-2 rounded-xl border border-border">
                        <span className="text-gray-400">Repetition Score:</span>
                        <span className="float-right font-bold text-foreground">{documentRiskDetails.repetition_score ?? "N/A"}%</span>
                      </div>
                      <div className="bg-gray-500/5 p-2 rounded-xl border border-border">
                        <span className="text-gray-400">N-gram Predict:</span>
                        <span className="float-right font-bold text-foreground">{documentRiskDetails.ngram_predictability ?? "N/A"}%</span>
                      </div>
                      <div className="bg-gray-500/5 p-2 rounded-xl border border-border">
                        <span className="text-gray-400">Uniformity:</span>
                        <span className="float-right font-bold text-foreground">{documentRiskDetails.uniformity_score ?? "N/A"}%</span>
                      </div>
                      <div className="bg-gray-500/5 p-2 rounded-xl border border-border">
                        <span className="text-gray-400">Redundancy:</span>
                        <span className="float-right font-bold text-foreground">{documentRiskDetails.semantic_redundancy ?? "N/A"}%</span>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
