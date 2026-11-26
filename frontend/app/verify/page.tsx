"use client";

import { useEffect, useState, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { CheckCircle2, XCircle, ShieldAlert, Loader2 } from "lucide-react";

function VerifyContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get("token");
  const [loading, setLoading] = useState(true);
  const [success, setSuccess] = useState(false);
  const [message, setMessage] = useState("Verifying your credentials...");

  useEffect(() => {
    if (!token) {
      setLoading(false);
      setSuccess(false);
      setMessage("No verification token found. Please check your verification email link.");
      return;
    }

    const verifyToken = async () => {
      try {
        const response = await fetch(`http://localhost:8000/api/v1/auth/verify?token=${token}`);
        const data = await response.json();
        
        if (response.ok) {
          setSuccess(true);
          setMessage(data.message || "Your email has been verified successfully!");
        } else {
          setSuccess(false);
          setMessage(data.detail || "Verification failed. The token may be invalid or expired.");
        }
      } catch (err) {
        setSuccess(false);
        setMessage("Connection failed. Could not contact verification server.");
      } finally {
        setLoading(false);
      }
    };

    verifyToken();
  }, [token]);

  return (
    <div className="w-full max-w-md glass-panel border border-border p-8 rounded-3xl flex flex-col gap-6 shadow-xl shadow-black/10 text-center relative z-10">
      <div className="flex justify-center">
        {loading ? (
          <div className="bg-primary/10 p-4 rounded-full border border-primary/20 text-primary">
            <Loader2 className="animate-spin" size={48} />
          </div>
        ) : success ? (
          <div className="bg-green-500/10 p-4 rounded-full border border-green-500/20 text-green-400">
            <CheckCircle2 className="animate-pulse" size={48} />
          </div>
        ) : (
          <div className="bg-red-500/10 p-4 rounded-full border border-red-500/20 text-red-400">
            <XCircle className="animate-bounce" size={48} />
          </div>
        )}
      </div>

      <div className="flex flex-col gap-2">
        <h2 className="text-2xl font-extrabold text-foreground tracking-tight">
          {loading ? "Verifying Email" : success ? "Verification Success" : "Verification Failed"}
        </h2>
        <p className="text-xs text-gray-400 leading-relaxed px-4">
          {message}
        </p>
      </div>

      {!loading && (
        <button
          onClick={() => router.push("/login")}
          className="w-full bg-primary hover:bg-primary-hover text-white text-xs font-bold py-3.5 rounded-xl transition-all hover:scale-102 hover:shadow-md hover:shadow-primary/10"
        >
          Return to Sign In Portal
        </button>
      )}
    </div>
  );
}

export default function VerifyPage() {
  return (
    <div className="flex-1 flex flex-col items-center justify-center min-h-screen bg-background relative overflow-hidden p-6">
      {/* Decorative backdrop shapes */}
      <div className="absolute top-[-20%] left-[-10%] w-[500px] h-[500px] rounded-full bg-primary/10 blur-[120px]" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[500px] h-[500px] rounded-full bg-purple-500/10 blur-[120px]" />

      <div className="flex items-center gap-3 mb-8 relative z-10">
        <div className="bg-primary/20 p-2.5 rounded-xl border border-primary/30 text-primary">
          <ShieldAlert size={24} />
        </div>
        <div>
          <h1 className="text-xl font-extrabold tracking-tight bg-gradient-to-r from-primary to-purple-400 bg-clip-text text-transparent">
            LEXORA
          </h1>
          <p className="text-[9px] text-gray-400 font-semibold tracking-widest uppercase">
            AI Risk Analyzer, Rephraser & Humanizer
          </p>
        </div>
      </div>

      <Suspense fallback={
        <div className="w-full max-w-md glass-panel border border-border p-8 rounded-3xl flex flex-col gap-6 items-center justify-center shadow-xl shadow-black/10">
          <Loader2 className="animate-spin text-primary" size={32} />
          <p className="text-xs text-gray-400">Loading verification context...</p>
        </div>
      }>
        <VerifyContent />
      </Suspense>
    </div>
  );
}
