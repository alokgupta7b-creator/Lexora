"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { BookText, FileSpreadsheet, ShieldAlert, Award, FileUp, Sparkles, Clock, Trash2, ArrowRight } from "lucide-react";
import Navbar from "@/components/navbar";
import Sidebar from "@/components/sidebar";
import FileUpload from "@/components/file-upload";

interface DocumentItem {
  id: number;
  title: string;
  file_name: string;
  file_type: string;
  created_at: string;
}

interface HistoryLog {
  id: number;
  action_type: string;
  description: string;
  timestamp: string;
}

export default function Dashboard() {
  const router = useRouter();
  
  const [metrics, setMetrics] = useState<any>(null);
  const [history, setHistory] = useState<HistoryLog[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchDashboardData = async () => {
    setLoading(true);
    const token = localStorage.getItem("token");
    if (!token) {
      router.push("/login");
      return;
    }

    try {
      // 1. Fetch dashboard metrics
      const metricRes = await fetch("http://localhost:8000/api/v1/dashboard", {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!metricRes.ok) throw new Error("Could not load dashboard statistics");
      const metricsData = await metricRes.json();
      setMetrics(metricsData);

      // 2. Fetch action history
      const historyRes = await fetch("http://localhost:8000/api/v1/history", {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (historyRes.ok) {
        const historyData = await historyRes.json();
        setHistory(historyData);
      }
      
    } catch (err: any) {
      setError(err.message || "Failed to establish API server connection.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDashboardData();
  }, []);

  const handleDocumentDelete = async (id: number) => {
    const token = localStorage.getItem("token");
    if (!window.confirm("Are you sure you want to delete this research paper?")) return;
    try {
      const response = await fetch(`http://localhost:8000/api/v1/document/${id}`, {
        method: "DELETE",
        headers: { Authorization: `Bearer ${token}` }
      });
      if (response.ok) {
        fetchDashboardData();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleUploadSuccess = (docId: number, title: string) => {
    // Proactively redirect to deep-dive analytics for this new paper!
    router.push(`/analyze?doc_id=${docId}`);
  };

  if (loading) {
    return (
      <div className="flex-1 flex flex-col min-h-screen bg-background">
        <Navbar />
        <div className="flex-1 flex justify-center items-center">
          <div className="flex flex-col items-center gap-3">
            <div className="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin" />
            <span className="text-xs font-bold text-gray-400 animate-pulse">Assembling Dashboard Workspace...</span>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col min-h-screen bg-background text-foreground">
      <Navbar />

      <div className="flex flex-1">
        <Sidebar />

        <main className="flex-1 p-6 md:p-8 flex flex-col gap-8 max-w-7xl mx-auto w-full">
          {/* Header Title */}
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight">Academic Workspace</h1>
            <p className="text-xs text-gray-400 mt-1">
              Upload papers, monitor styling risks, and optimize submission readiness.
            </p>
          </div>

          {/* Aggregated Totals Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="glass-panel border border-border p-6 rounded-3xl flex items-center gap-4 shadow-md shadow-black/5 hover:scale-[1.01] transition-transform duration-300">
              <div className="bg-primary/10 border border-primary/20 text-primary p-4 rounded-2xl">
                <BookText size={24} />
              </div>
              <div>
                <p className="text-[10px] text-gray-400 uppercase tracking-widest font-bold">Total Papers Uploaded</p>
                <h3 className="text-2xl font-black text-foreground mt-1">{metrics?.total_documents || 0}</h3>
              </div>
            </div>

            <div className="glass-panel border border-border p-6 rounded-3xl flex items-center gap-4 shadow-md shadow-black/5 hover:scale-[1.01] transition-transform duration-300">
              <div className="bg-yellow-500/10 border border-yellow-500/20 text-yellow-400 p-4 rounded-2xl">
                <ShieldAlert size={24} />
              </div>
              <div>
                <p className="text-[10px] text-gray-400 uppercase tracking-widest font-bold">Average AI Risk score</p>
                <h3 className="text-2xl font-black text-foreground mt-1">{metrics?.average_risk_score || 0}%</h3>
              </div>
            </div>

            <div className="glass-panel border border-border p-6 rounded-3xl flex items-center gap-4 shadow-md shadow-black/5 hover:scale-[1.01] transition-transform duration-300">
              <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 p-4 rounded-2xl">
                <Award size={24} />
              </div>
              <div>
                <p className="text-[10px] text-gray-400 uppercase tracking-widest font-bold">Average Readability</p>
                <h3 className="text-2xl font-black text-foreground mt-1">{metrics?.average_readability_score || 0}</h3>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
            {/* Left side: Upload & Saved Papers List */}
            <div className="xl:col-span-2 flex flex-col gap-8">
              {/* File Uploader */}
              <div className="glass-panel border border-border p-6 rounded-3xl">
                <h2 className="text-sm font-bold uppercase tracking-wider mb-4 flex items-center gap-2">
                  <FileUp size={18} className="text-primary" />
                  Analyze New Document
                </h2>
                <FileUpload onUploadSuccess={handleUploadSuccess} />
              </div>

              {/* Saved Papers Table */}
              <div className="glass-panel border border-border p-6 rounded-3xl flex flex-col gap-4">
                <h2 className="text-sm font-bold uppercase tracking-wider flex items-center gap-2">
                  <FileSpreadsheet size={18} className="text-indigo-400" />
                  Recent Research Submissions
                </h2>

                {metrics?.recent_uploads && metrics.recent_uploads.length > 0 ? (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs border-collapse">
                      <thead>
                        <tr className="border-b border-border text-gray-400 font-bold">
                          <th className="pb-3">Title</th>
                          <th className="pb-3 hidden sm:table-cell">Filename</th>
                          <th className="pb-3">Format</th>
                          <th className="pb-3 text-right">Actions</th>
                        </tr>
                      </thead>
                      <tbody>
                        {metrics.recent_uploads.map((doc: DocumentItem) => (
                          <tr key={doc.id} className="border-b border-border hover:bg-gray-500/5 transition-colors">
                            <td className="py-4 font-semibold text-foreground max-w-[200px] truncate">{doc.title}</td>
                            <td className="py-4 text-gray-400 hidden sm:table-cell max-w-[150px] truncate">{doc.file_name}</td>
                            <td className="py-4 uppercase text-[10px] font-bold"><span className="bg-gray-500/10 px-2 py-1 rounded border border-border text-gray-300">{doc.file_type}</span></td>
                            <td className="py-4 text-right flex items-center justify-end gap-2">
                              <button
                                onClick={() => router.push(`/analyze?doc_id=${doc.id}`)}
                                className="bg-primary/10 hover:bg-primary/20 text-primary border border-primary/20 p-2 rounded-xl text-[10px] font-semibold flex items-center gap-1.5 transition-transform hover:scale-105"
                              >
                                Optimize <ArrowRight size={12} />
                              </button>
                              <button
                                onClick={() => handleDocumentDelete(doc.id)}
                                className="bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/20 p-2 rounded-xl transition-all"
                                title="Delete"
                              >
                                <Trash2 size={12} />
                              </button>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                ) : (
                  <div className="text-center py-10 text-xs text-gray-400 border border-dashed border-border rounded-2xl flex flex-col items-center justify-center gap-2">
                    <BookText size={24} />
                    <p>No papers saved in workspace yet.</p>
                  </div>
                )}
              </div>
            </div>

            {/* Right side: Charts & Chronological History */}
            <div className="flex flex-col gap-8">
              {/* Trends chart */}
              <div className="glass-panel border border-border p-6 rounded-3xl flex flex-col gap-4">
                <h2 className="text-sm font-bold uppercase tracking-wider flex items-center gap-2">
                  <Sparkles size={18} className="text-purple-400" />
                  Stylistic Risk Distribution
                </h2>
                <div className="h-48 w-full">
                  <ResponsiveContainer width="100%" height="100%">
                    <AreaChart
                      data={metrics?.risk_trends || []}
                      margin={{ top: 5, right: 5, left: -25, bottom: 5 }}
                    >
                      <defs>
                        <linearGradient id="colorRisk" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="#6366f1" stopOpacity={0.4}/>
                          <stop offset="95%" stopColor="#6366f1" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" stroke="#1f2937" />
                      <XAxis dataKey="name" stroke="#4b5563" fontSize={9} />
                      <YAxis stroke="#4b5563" fontSize={9} domain={[0, 100]} />
                      <Tooltip contentStyle={{ backgroundColor: "#111827", borderColor: "#1f2937", borderRadius: "12px", fontSize: "10px" }} />
                      <Area type="monotone" dataKey="risk" stroke="#6366f1" strokeWidth={2} fillOpacity={1} fill="url(#colorRisk)" />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>

              {/* History list */}
              <div className="glass-panel border border-border p-6 rounded-3xl flex flex-col gap-4 flex-1">
                <h2 className="text-sm font-bold uppercase tracking-wider flex items-center gap-2">
                  <Clock size={18} className="text-gray-400" />
                  Chronological Workspace Logs
                </h2>

                <div className="flex flex-col gap-3 max-h-[300px] overflow-y-auto pr-1">
                  {history.length > 0 ? (
                    history.map((log) => (
                      <div key={log.id} className="bg-gray-500/5 p-3 rounded-2xl border border-border text-[11px] flex flex-col gap-1">
                        <div className="flex justify-between items-center">
                          <span className={`text-[9px] uppercase font-bold px-2 py-0.5 rounded ${
                            log.action_type === 'upload' ? 'bg-primary/20 text-indigo-300' :
                            log.action_type === 'analyze' ? 'bg-yellow-500/20 text-yellow-300' :
                            log.action_type === 'rephrase' ? 'bg-purple-500/20 text-purple-300' :
                            log.action_type === 'humanize' ? 'bg-emerald-500/20 text-emerald-300' :
                            'bg-gray-500/20 text-gray-300'
                          }`}>
                            {log.action_type}
                          </span>
                          <span className="text-[9px] text-gray-400">{new Date(log.timestamp).toLocaleDateString()}</span>
                        </div>
                        <p className="text-gray-300">{log.description}</p>
                      </div>
                    ))
                  ) : (
                    <p className="text-xs text-gray-400 py-4 text-center">No action log history recorded.</p>
                  )}
                </div>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
