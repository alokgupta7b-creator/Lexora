"use client";

import { useEffect, useState, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { ShieldAlert, Award, FileText, ArrowLeft, RefreshCw, Download, Layers } from "lucide-react";
import Navbar from "@/components/navbar";
import Sidebar from "@/components/sidebar";
import SentenceHighlighter from "@/components/sentence-highlighter";

function AnalyzeContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const docId = searchParams.get("doc_id");

  const [document, setDocument] = useState<any>(null);
  const [analysis, setAnalysis] = useState<any>(null);
  
  const [activeSection, setActiveSection] = useState<string>("introduction");
  const [loading, setLoading] = useState(true);
  const [analyzing, setAnalyzing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDocumentDetails = async () => {
    if (!docId) {
      setError("No document ID specified.");
      setLoading(false);
      return;
    }
    const token = localStorage.getItem("token");
    try {
      // 1. Fetch document raw/sections details
      const docRes = await fetch(`http://localhost:8000/api/v1/document/${docId}`, {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!docRes.ok) throw new Error("Could not find document record");
      const docData = await docRes.json();
      setDocument(docData);
      
      // Auto pick first non-empty section
      if (docData.parsed_sections) {
        const nonEmpties = Object.keys(docData.parsed_sections).filter(k => docData.parsed_sections[k]);
        if (nonEmpties.length > 0) {
          setActiveSection(nonEmpties[0]);
        }
      }

      // 2. Trigger active analysis retrieval or audit
      await fetchOrCreateAnalysis(docData.id, token);
      
    } catch (err: any) {
      setError(err.message || "Failed to download paper statistics");
    } finally {
      setLoading(false);
    }
  };

  const fetchOrCreateAnalysis = async (id: number, token: string | null) => {
    // Audit document risk
    const response = await fetch(`http://localhost:8000/api/v1/analyze/${id}`, {
      method: "POST",
      headers: { Authorization: `Bearer ${token}` }
    });
    if (response.ok) {
      const analysisData = await response.json();
      setAnalysis(analysisData);
    }
  };

  const triggerManualAudit = async () => {
    setAnalyzing(true);
    const token = localStorage.getItem("token");
    try {
      await fetchOrCreateAnalysis(document.id, token);
    } catch (err) {
      console.error(err);
    } finally {
      setAnalyzing(false);
    }
  };

  const handleDownloadReport = async (format: string) => {
    const token = localStorage.getItem("token");
    try {
      const response = await fetch(`http://localhost:8000/api/v1/report/${document.id}?report_type=${format}`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` }
      });
      
      if (!response.ok) throw new Error("Failed to generate report file");
      
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const a = window.document.createElement("a");
      a.href = url;
      a.download = `Report_${document.title.replace(/\s+/g, "_")}.${format}`;
      window.document.body.appendChild(a);
      a.click();
      window.document.body.removeChild(a);
    } catch (err) {
      alert("Error generating download file.");
    }
  };

  const handleSentenceOptimize = (original: string, optimized: string) => {
    // Dynamic replacement in text block view on success rephraser action
    if (!analysis) return;
    const nextAnalysis = { ...analysis };
    const idx = nextAnalysis.risk_details.sentences.findIndex((s: any) => s.sentence === original);
    if (idx !== -1) {
      nextAnalysis.risk_details.sentences[idx].sentence = optimized;
      nextAnalysis.risk_details.sentences[idx].score = 10.0; // Lower score on optimize
      nextAnalysis.risk_details.sentences[idx].category = "Very Low";
      nextAnalysis.risk_details.sentences[idx].reasons = [];
      nextAnalysis.risk_details.sentences[idx].improvement_suggestions = [];
      setAnalysis(nextAnalysis);
    }
  };

  useEffect(() => {
    fetchDocumentDetails();
  }, [docId]);

  if (loading) {
    return (
      <div className="flex-grow flex justify-center items-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin" />
          <span className="text-xs font-bold text-gray-400">Performing Stylistic Risk Audits...</span>
        </div>
      </div>
    );
  }

  if (error || !document) {
    return (
      <div className="flex-grow p-8 flex flex-col justify-center items-center gap-4">
        <h3 className="text-lg font-bold text-red-400">Workspace Error</h3>
        <p className="text-xs text-gray-400">{error || "Document not found."}</p>
        <button onClick={() => router.push("/dashboard")} className="bg-primary px-4 py-2 rounded-xl text-xs text-white">
          Back to Dashboard
        </button>
      </div>
    );
  }

  // Filter sentence analyzer lists based on selected parsed sections to make standard highlighter perfect!
  const getSectionSentences = () => {
    if (!analysis?.risk_details?.sentences) return [];
    
    const sectionText = document.parsed_sections?.[activeSection] || "";
    if (!sectionText.trim()) return [];
    
    const hasSectionTag = analysis.risk_details.sentences.some((s: any) => s.section);
    if (hasSectionTag) {
      return analysis.risk_details.sentences.filter((s: any) => s.section === activeSection);
    }
    
    // We filter standard sentences by matching contents in the parsed section
    return analysis.risk_details.sentences.filter((s: any) => 
      sectionText.toLowerCase().includes(s.sentence.trim().toLowerCase())
    );
  };

  const activeSentences = getSectionSentences();
  const readability = analysis?.readability_scores || {};

  return (
    <main className="flex-1 p-6 md:p-8 flex flex-col gap-8 max-w-7xl mx-auto w-full">
      {/* Breadcrumb Header */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4">
        <div className="flex items-center gap-3">
          <button
            onClick={() => router.push("/dashboard")}
            className="p-2.5 rounded-xl border border-border hover:bg-gray-500/5 transition-colors"
          >
            <ArrowLeft size={16} />
          </button>
          <div>
            <h1 className="text-2xl font-black truncate max-w-sm sm:max-w-md">{document.title}</h1>
            <p className="text-xs text-gray-400 mt-0.5">Style, Readability and AI Risk Assessment Portal</p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={triggerManualAudit}
            disabled={analyzing}
            className="flex items-center gap-2 bg-gray-500/5 hover:bg-gray-500/10 border border-border text-foreground text-xs font-bold px-4 py-2.5 rounded-xl transition-all"
          >
            <RefreshCw size={14} className={analyzing ? "animate-spin" : ""} />
            Re-Audit
          </button>

          <div className="relative group">
            <button className="flex items-center gap-2 bg-primary hover:bg-primary-hover text-white text-xs font-bold px-4 py-2.5 rounded-xl transition-all shadow-md shadow-primary/15">
              <Download size={14} />
              Export Report
            </button>
            <div className="absolute right-0 top-11 hidden group-hover:flex flex-col bg-card border border-border rounded-xl shadow-xl w-32 z-30 py-1.5 overflow-hidden">
              <button onClick={() => handleDownloadReport("pdf")} className="px-4 py-2 text-left text-[11px] font-semibold hover:bg-gray-500/5 text-gray-300">PDF Report</button>
              <button onClick={() => handleDownloadReport("docx")} className="px-4 py-2 text-left text-[11px] font-semibold hover:bg-gray-500/5 text-gray-300">DOCX Word</button>
              <button onClick={() => handleDownloadReport("txt")} className="px-4 py-2 text-left text-[11px] font-semibold hover:bg-gray-500/5 text-gray-300">TXT Log</button>
            </div>
          </div>
        </div>
      </div>

      {/* Main Analytics metrics Row */}
      {analysis && (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
          <div className="glass-panel border border-border p-6 rounded-3xl relative hover:scale-[1.01] transition-transform">
            <p className="text-[10px] text-gray-400 uppercase tracking-widest font-bold">Overall AI Risk Signature</p>
            <div className="flex justify-between items-baseline mt-2">
              <h3 className="text-3xl font-black text-foreground">{analysis.overall_score}%</h3>
              <span className={`text-[9px] uppercase font-bold px-2 py-0.5 rounded ${
                analysis.overall_score <= 25 ? "bg-emerald-500/10 text-emerald-400" :
                analysis.overall_score <= 45 ? "bg-yellow-500/10 text-yellow-400" :
                analysis.overall_score <= 70 ? "bg-orange-500/10 text-orange-400" :
                "bg-red-500/10 text-red-400 animate-pulse"
              }`}>
                {analysis.overall_score <= 25 ? "Very Low" :
                 analysis.overall_score <= 45 ? "Low" :
                 analysis.overall_score <= 70 ? "Moderate" : "High"}
              </span>
            </div>
            <div className="w-full bg-border rounded-full h-1.5 mt-3 overflow-hidden">
              <div className="bg-primary h-full rounded-full" style={{ width: `${analysis.overall_score}%` }} />
            </div>
          </div>

          <div className="glass-panel border border-border p-6 rounded-3xl hover:scale-[1.01] transition-transform">
            <p className="text-[10px] text-gray-400 uppercase tracking-widest font-bold">Academic Quality Rating</p>
            <h3 className="text-3xl font-black text-foreground mt-2">{analysis.academic_quality_score}/100</h3>
            <p className="text-[9px] text-gray-400 mt-2">Based on syntactic transitions and standards.</p>
          </div>

          <div className="glass-panel border border-border p-6 rounded-3xl hover:scale-[1.01] transition-transform">
            <p className="text-[10px] text-gray-400 uppercase tracking-widest font-bold">Publication Readiness</p>
            <h3 className="text-3xl font-black text-foreground mt-2">{analysis.publication_readiness_score}/100</h3>
            <p className="text-[9px] text-gray-400 mt-2">Evaluation of style, formatting, and grammar.</p>
          </div>

          <div className="glass-panel border border-border p-6 rounded-3xl hover:scale-[1.01] transition-transform">
            <p className="text-[10px] text-gray-400 uppercase tracking-widest font-bold">Word Metrics</p>
            <h3 className="text-3xl font-black text-foreground mt-2">{readability.total_words || 0}</h3>
            <p className="text-[9px] text-gray-400 mt-2">{readability.total_sentences || 0} Sentences / {readability.total_paragraphs || 0} Paragraphs</p>
          </div>
        </div>
      )}

      {/* Diagnostics & Extraction Warnings */}
      {document.parsed_sections?._diagnostics?.confidence === "low" && (
        <div className="bg-amber-500/10 border border-amber-500/20 text-amber-400 p-5 rounded-3xl text-xs flex flex-col gap-2 animate-slideIn">
          <div className="flex items-center gap-2 font-bold">
            <span className="w-2.5 h-2.5 rounded-full bg-amber-500 animate-pulse" />
            Linguistic Extraction Warning: Low Heading Detection Confidence
          </div>
          <p className="text-gray-400 leading-normal">
            Our ingestion parser utilized structural cues or proportional fallback ratios to segment this paper. 
            Academic sections might contain merged paragraphs.
          </p>
          {document.parsed_sections._diagnostics.warnings?.length > 0 && (
            <ul className="list-disc pl-4 text-gray-500 flex flex-col gap-1 mt-1">
              {document.parsed_sections._diagnostics.warnings.map((w: string, i: number) => (
                <li key={i}>{w}</li>
              ))}
            </ul>
          )}
        </div>
      )}

      {/* Highlighter Workspace Panel */}
      <div className="grid grid-cols-1 lg:grid-cols-4 gap-8 items-start">
        {/* Left Side: Section Picker tabs */}
        <div className="glass-panel border border-border p-4 rounded-3xl flex flex-row lg:flex-col gap-2 overflow-x-auto lg:overflow-x-visible">
          <div className="hidden lg:flex items-center gap-2 px-3 pb-3 border-b border-border text-gray-400">
            <Layers size={16} />
            <span className="text-[10px] font-bold uppercase tracking-wider">Semantic Sections</span>
          </div>

          {document.parsed_sections && Object.keys(document.parsed_sections).map((key) => {
            if (key.startsWith("_") || typeof document.parsed_sections[key] !== "string") return null;
            const hasContent = document.parsed_sections[key] && document.parsed_sections[key].trim().length > 10;
            if (!hasContent) return null;
            
            return (
              <button
                key={key}
                onClick={() => setActiveSection(key)}
                className={`px-4 py-2.5 rounded-2xl text-xs font-semibold text-left transition-all truncate ${
                  activeSection === key
                    ? "bg-primary text-white"
                    : "text-gray-400 hover:bg-gray-500/5 hover:text-foreground"
                }`}
              >
                {key.replace("_", " ").toUpperCase()}
              </button>
            );
          })}
        </div>

        {/* Right Side: Interactive Sentence Highlighter Panel */}
        <div className="lg:col-span-3 flex flex-col gap-6">
          <div className="glass-panel border border-border p-6 rounded-3xl flex flex-col gap-4">
            <div className="flex justify-between items-center pb-2 border-b border-border">
              <h2 className="text-sm font-bold uppercase tracking-wider flex items-center gap-2">
                <FileText size={18} className="text-primary" />
                Linguistic Auditor - {activeSection.replace("_", " ").toUpperCase()}
              </h2>
              {analysis?.section_scores?.[activeSection] !== undefined && (
                <span className="text-[10px] font-bold uppercase tracking-widest bg-gray-500/10 px-3 py-1.5 rounded-full border border-border">
                  Section Risk: {analysis.section_scores[activeSection]}/100
                </span>
              )}
            </div>

            {activeSentences.length > 0 ? (
              <SentenceHighlighter
                sentences={activeSentences}
                onSentenceOptimize={handleSentenceOptimize}
                documentRiskDetails={analysis.risk_details}
              />
            ) : (
              <div className="text-center py-12 text-xs text-gray-400">
                This academic section does not contain analyzable structures.
              </div>
            )}
          </div>
        </div>
      </div>
    </main>
  );
}

export default function AnalyzePage() {
  return (
    <div className="flex flex-col min-h-screen bg-background text-foreground">
      <Navbar />

      <div className="flex flex-1">
        <Sidebar />

        <Suspense fallback={
          <div className="flex-grow flex justify-center items-center">
            <div className="flex flex-col items-center gap-3">
              <div className="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin" />
              <span className="text-xs font-bold text-gray-400">Loading audit viewport...</span>
            </div>
          </div>
        }>
          <AnalyzeContent />
        </Suspense>
      </div>
    </div>
  );
}
