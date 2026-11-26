"use client";

import { useState, useEffect, Suspense } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { ShieldAlert, AlertCircle, CheckCircle2, Check, X, Eye, EyeOff } from "lucide-react";

function ResetPasswordContent() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const token = searchParams.get("token");

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  // Password Policy requirements
  const requirements = [
    { label: "At least 8 characters", val: password.length >= 8 },
    { label: "At least one uppercase letter (A-Z)", val: /[A-Z]/.test(password) },
    { label: "At least one lowercase letter (a-z)", val: /[a-z]/.test(password) },
    { label: "At least one number (0-9)", val: /\d/.test(password) },
    { label: "At least one special character (!@#$%^&*)", val: /[!@#$%^&*(),.?":{}|<>]/.test(password) },
  ];

  const allRequirementsMet = requirements.every(req => req.val);
  const passwordsMatch = password && password === confirmPassword;

  useEffect(() => {
    if (!token) {
      setError("Reset token is missing in URL. Please copy the link exactly from your email.");
    }
  }, [token]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!token) return;

    if (!allRequirementsMet) {
      setError("Please satisfy all password complexity requirements first.");
      return;
    }

    if (!passwordsMatch) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const response = await fetch("http://localhost:8000/api/v1/auth/reset-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ token, password }),
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || "Failed to reset password.");
      }

      setSuccess(true);
    } catch (err: any) {
      setError(err.message || "An error occurred while resetting your password.");
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <div className="w-full max-w-sm glass-panel border border-border p-8 rounded-3xl flex flex-col gap-6 shadow-xl shadow-black/10 text-center relative z-10">
        <div className="flex justify-center">
          <div className="bg-green-500/10 p-4 rounded-full border border-green-500/20 text-green-400">
            <CheckCircle2 className="animate-pulse" size={48} />
          </div>
        </div>
        <div className="flex flex-col gap-2">
          <h2 className="text-xl font-extrabold text-foreground tracking-tight">Password Reset</h2>
          <p className="text-xs text-gray-400 leading-relaxed">
            Your password has been reset successfully. You can now use your new password to sign in.
          </p>
        </div>
        <button
          onClick={() => router.push("/login")}
          className="w-full bg-primary hover:bg-primary-hover text-white text-xs font-bold py-3.5 rounded-xl transition-all hover:scale-102"
        >
          Proceed to Sign In
        </button>
      </div>
    );
  }

  return (
    <div className="w-full max-w-sm glass-panel border border-border p-8 rounded-3xl flex flex-col gap-6 shadow-xl shadow-black/10 relative z-10">
      <div className="text-center">
        <h2 className="text-xl font-extrabold text-foreground">
          Reset Password
        </h2>
        <p className="text-xs text-gray-400 mt-1">
          Create a secure, publication-compliant password
        </p>
      </div>

      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5 relative">
          <label className="text-[10px] uppercase font-bold tracking-wider text-gray-400">New Password</label>
          <div className="relative">
            <input
              type={showPassword ? "text" : "password"}
              required
              disabled={!token}
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full bg-gray-500/5 border border-border rounded-xl pl-4 pr-10 py-2.5 text-xs text-foreground focus:outline-none focus:border-primary transition-colors"
            />
            <button
              type="button"
              onClick={() => setShowPassword(!showPassword)}
              className="absolute right-3.5 top-3 text-gray-400 hover:text-foreground"
            >
              {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
            </button>
          </div>
        </div>

        <div className="flex flex-col gap-1.5">
          <label className="text-[10px] uppercase font-bold tracking-wider text-gray-400">Confirm Password</label>
          <input
            type="password"
            required
            disabled={!token}
            placeholder="••••••••"
            value={confirmPassword}
            onChange={(e) => setConfirmPassword(e.target.value)}
            className="bg-gray-500/5 border border-border rounded-xl px-4 py-2.5 text-xs text-foreground focus:outline-none focus:border-primary transition-colors"
          />
        </div>

        {/* Requirements Tracker */}
        {password && (
          <div className="flex flex-col gap-1.5 bg-gray-500/5 p-3.5 rounded-2xl border border-border">
            <p className="text-[9px] uppercase font-extrabold tracking-wider text-gray-400 mb-1">Complexity Strength</p>
            <div className="flex flex-col gap-1">
              {requirements.map((req, idx) => (
                <div key={idx} className="flex items-center gap-2 text-[10px]">
                  {req.val ? (
                    <Check size={10} className="text-green-400 shrink-0" />
                  ) : (
                    <X size={10} className="text-red-400 shrink-0" />
                  )}
                  <span className={req.val ? "text-gray-300 line-through" : "text-gray-400"}>
                    {req.label}
                  </span>
                </div>
              ))}
              <div className="flex items-center gap-2 text-[10px] border-t border-border/40 mt-1 pt-1">
                {passwordsMatch ? (
                  <Check size={10} className="text-green-400 shrink-0" />
                ) : (
                  <X size={10} className="text-red-400 shrink-0" />
                )}
                <span className={passwordsMatch ? "text-gray-300" : "text-gray-400"}>
                  Passwords match
                </span>
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-3 rounded-2xl flex items-center gap-2 text-[11px]">
            <AlertCircle size={16} className="shrink-0" />
            <p className="text-left">{error}</p>
          </div>
        )}

        <button
          type="submit"
          disabled={loading || !token || !allRequirementsMet || !passwordsMatch}
          className="w-full bg-primary hover:bg-primary-hover text-white text-xs font-bold py-3 rounded-xl transition-all hover:scale-102 hover:shadow-md hover:shadow-primary/10 disabled:opacity-50"
        >
          {loading ? "Resetting..." : "Save New Password"}
        </button>
      </form>
    </div>
  );
}

export default function ResetPasswordPage() {
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
        <div className="w-full max-w-sm glass-panel border border-border p-8 rounded-3xl flex flex-col gap-6 items-center justify-center shadow-xl shadow-black/10">
          <div className="animate-spin text-primary rounded-full h-8 w-8 border-b-2 border-primary" />
          <p className="text-xs text-gray-400">Loading reset context...</p>
        </div>
      }>
        <ResetPasswordContent />
      </Suspense>
    </div>
  );
}
