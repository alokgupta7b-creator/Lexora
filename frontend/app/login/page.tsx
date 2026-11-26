"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { ShieldAlert, LogIn, UserPlus, Star, AlertCircle, Eye, EyeOff, Check, X, Mail } from "lucide-react";
import { normalizeEmail } from "@/utils/email";

export default function LoginPage() {
  const router = useRouter();
  const [isRegister, setIsRegister] = useState(false);
  const [forgotPassword, setForgotPassword] = useState(false);

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [showPassword, setShowPassword] = useState(false);

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [showResendVerification, setShowResendVerification] = useState(false);
  const [isGoogleConfigured, setIsGoogleConfigured] = useState<boolean | null>(null);

  // Email format validation using shared utility normalization helper
  const normalizedEmail = normalizeEmail(email);
  const isEmailValid = typeof email === "string" &&
    email.trim() !== "" &&
    /^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$/.test(normalizedEmail) &&
    !normalizedEmail.includes("..");

  // Password Policy requirements
  const passwordRequirements = [
    { label: "At least 8 characters", val: password.length >= 8 },
    { label: "At least one uppercase letter (A-Z)", val: /[A-Z]/.test(password) },
    { label: "At least one lowercase letter (a-z)", val: /[a-z]/.test(password) },
    { label: "At least one number (0-9)", val: /\d/.test(password) },
    { label: "At least one special character (!@#$%^&*)", val: /[!@#$%^&*(),.?":{}|<>]/.test(password) },
  ];
  const allRequirementsMet = passwordRequirements.every(req => req.val);

  // Google OAuth code query listener & Config checker
  useEffect(() => {
    // 1. Fetch Google credentials configuration from server
    const checkGoogleConfig = async () => {
      try {
        const response = await fetch("http://localhost:8000/api/v1/auth/google/client-id");
        if (response.ok) {
          const data = await response.json();
          setIsGoogleConfigured(data.client_id !== null && data.redirect_uri !== null);
        } else {
          setIsGoogleConfigured(false);
        }
      } catch (err) {
        setIsGoogleConfigured(false);
      }
    };
    checkGoogleConfig();

    // 2. Handle Google code callback
    const handleCodeCallback = async () => {
      const query = new URLSearchParams(window.location.search);
      const code = query.get("code");
      const state = query.get("state");
      const storedState = localStorage.getItem("oauth_state");
      if (code) {
        setLoading(true);
        setError(null);
        try {
          if (!state || state !== storedState) {
            throw new Error("Security state mismatch. Possible CSRF attack detected.");
          }
          localStorage.removeItem("oauth_state");

          // Exchange Google auth code for Lexora session token
          const response = await fetch("http://localhost:8000/api/v1/auth/google", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ code }),
          });

          if (!response.ok) {
            let errMsg = "Google SSO authentication failed.";
            try {
              if (response.headers.get("content-type")?.includes("application/json")) {
                const errData = await response.json();
                if (errData.detail) {
                  if (Array.isArray(errData.detail)) {
                    errMsg = errData.detail.map((d: any) => d.msg).join(", ");
                  } else {
                    errMsg = errData.detail;
                  }
                }
              } else {
                errMsg = `Server error: ${response.status} ${response.statusText}`;
              }
            } catch (parseErr) {
              errMsg = "Could not parse server error response.";
            }
            throw new Error(errMsg);
          }

          const data = await response.json();
          localStorage.setItem("token", data.access_token);

          // Get user details
          const meResponse = await fetch("http://localhost:8000/api/v1/auth/me", {
            headers: {
              Authorization: `Bearer ${data.access_token}`,
            },
          });
          if (meResponse.ok) {
            const meData = await meResponse.json();
            localStorage.setItem("userEmail", meData.email);
            localStorage.setItem("userRole", meData.role);
          }

          // Clear query params without reloading the page
          window.history.replaceState({}, document.title, window.location.pathname);
          router.push("/dashboard");
        } catch (err: any) {
          console.error("Google Callback failure:", err);
          let userMsg = err.message || "Google Single Sign-On failed.";
          if (userMsg.includes("Failed to fetch")) {
            userMsg = "Cannot connect to server.";
          } else if (err instanceof TypeError || err.name === "TypeError" || userMsg.includes("NetworkError") || userMsg.includes("network")) {
            userMsg = "Network error. Please try again.";
          }
          setError(userMsg);
          setLoading(false);
        }
      }
    };

    handleCodeCallback();
  }, [router]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMessage(null);
    setShowResendVerification(false);

    // Strict input type validation guards
    if (typeof email !== "string") {
      setError("Please enter a valid email.");
      return;
    }

    setLoading(true);

    if (!isEmailValid) {
      setError("Please enter a valid email address.");
      setLoading(false);
      return;
    }

    if (isRegister && !allRequirementsMet) {
      setError("Password does not meet all security guidelines.");
      setLoading(false);
      return;
    }

    const url = isRegister
      ? "http://localhost:8000/api/v1/auth/register"
      : "http://localhost:8000/api/v1/auth/login";

    const payload = isRegister
      ? { email: normalizedEmail, password, full_name: fullName }
      : new URLSearchParams({ username: normalizedEmail, password });

    const headers: Record<string, string> = isRegister
      ? { "Content-Type": "application/json" }
      : { "Content-Type": "application/x-www-form-urlencoded" };

    try {
      const response = await fetch(url, {
        method: "POST",
        headers,
        body: isRegister ? JSON.stringify(payload) : payload.toString(),
      });

      if (!response.ok) {
        if (!isRegister && response.status === 403) {
          setShowResendVerification(true);
        }
        let errMsg = "Authentication request failed";
        try {
          if (response.headers.get("content-type")?.includes("application/json")) {
            const errData = await response.json();
            if (errData.detail) {
              if (Array.isArray(errData.detail)) {
                errMsg = errData.detail.map((d: any) => d.msg).join(", ");
              } else {
                errMsg = errData.detail;
              }
            }
          } else {
            errMsg = `Server error: ${response.status} ${response.statusText}`;
          }
        } catch (parseErr) {
          errMsg = "Could not parse server error response.";
        }
        throw new Error(errMsg);
      }

      if (isRegister) {
        const data = await response.json();
        const isAutoVerified = data.message?.includes("log in now") || data.message?.includes("ready");
        setIsRegister(false);
        if (isAutoVerified) {
          setSuccessMessage(
            "✅ Account created! You can log in right now with your credentials — no email verification needed in development mode."
          );
        } else {
          setSuccessMessage(
            "📧 Registration successful! A verification link has been sent. Please check your email (or the backend server console), click the link, then sign in here."
          );
        }
        setPassword("");
        return;
      }

      const data = await response.json();
      localStorage.setItem("token", data.access_token);
      localStorage.setItem("userEmail", normalizedEmail);
      
      // Fetch user role
      const meResponse = await fetch("http://localhost:8000/api/v1/auth/me", {
        headers: {
          Authorization: `Bearer ${data.access_token}`,
        },
      });
      if (meResponse.ok) {
        const meData = await meResponse.json();
        localStorage.setItem("userRole", meData.role);
      }

      router.push("/dashboard");
    } catch (err: any) {
      console.error("Submission failure:", err);
      let userMsg = err.message || "An authentication error occurred.";
      if (userMsg.includes("Failed to fetch")) {
        userMsg = "Cannot connect to server.";
      } else if (err instanceof TypeError || err.name === "TypeError" || userMsg.includes("NetworkError") || userMsg.includes("network")) {
        userMsg = "Network error. Please try again.";
      }
      setError(userMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleResendVerification = async () => {
    setError(null);
    setSuccessMessage(null);
    setLoading(true);

    try {
      const response = await fetch("http://localhost:8000/api/v1/auth/resend-verification", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: normalizedEmail }),
      });

      if (!response.ok) {
        const errData = await response.json();
        const detail = errData.detail;
        throw new Error(
          Array.isArray(detail)
            ? detail.map((item: { msg: string }) => item.msg).join(", ")
            : detail || `Request failed with status ${response.status}.`
        );
      }

      const data = await response.json();
      setSuccessMessage(data.message || "If this email is registered and unverified, a verification link has been sent.");
      setShowResendVerification(false);
    } catch (err: any) {
      console.error("Resend verification failure:", err);
      setError(err.message || "Failed to resend verification link.");
    } finally {
      setLoading(false);
    }
  };

  const handleForgotPasswordSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setSuccessMessage(null);

    // Strict input type validation guards
    if (typeof email !== "string") {
      setError("Please enter a valid email.");
      return;
    }

    setLoading(true);

    if (!isEmailValid) {
      setError("Please enter a valid email address.");
      setLoading(false);
      return;
    }

    try {
      const response = await fetch("http://localhost:8000/api/v1/auth/forgot-password", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: normalizedEmail }),
      });

      if (!response.ok) {
        let errMsg = "Request failed.";
        try {
          if (response.headers.get("content-type")?.includes("application/json")) {
            const errData = await response.json();
            if (errData.detail) {
              if (Array.isArray(errData.detail)) {
                errMsg = errData.detail.map((d: any) => d.msg).join(", ");
              } else {
                errMsg = errData.detail;
              }
            }
          } else {
            errMsg = `Server error: ${response.status} ${response.statusText}`;
          }
        } catch (parseErr) {
          errMsg = "Could not parse server error response.";
        }
        throw new Error(errMsg);
      }

      const data = await response.json();
      setSuccessMessage(data.message || "Password recovery instructions sent! Check the server CLI logs for the verification token link.");
      setForgotPassword(false);
    } catch (err: any) {
      console.error("Forgot Password failure:", err);
      let userMsg = err.message || "Failed to submit recovery request.";
      if (userMsg.includes("Failed to fetch")) {
        userMsg = "Cannot connect to server.";
      } else if (err instanceof TypeError || err.name === "TypeError" || userMsg.includes("NetworkError") || userMsg.includes("network")) {
        userMsg = "Network error. Please try again.";
      }
      setError(userMsg);
    } finally {
      setLoading(false);
    }
  };

  const handleGoogleLogin = async () => {
    if (isGoogleConfigured === false) {
      setError("Google Sign-In is not configured on this server.");
      return;
    }

    setLoading(true);
    setError(null);
    try {
      // Fetch client ID and redirect URI from server
      const clientResp = await fetch("http://localhost:8000/api/v1/auth/google/client-id");
      if (!clientResp.ok) {
        let errMsg = "Could not fetch Google OAuth configuration from the server.";
        try {
          if (clientResp.headers.get("content-type")?.includes("application/json")) {
            const errData = await clientResp.json();
            if (errData.detail) {
              errMsg = errData.detail;
            }
          }
        } catch (e) {}
        throw new Error(errMsg);
      }
      
      const clientData = await clientResp.json();
      const clientId = clientData.client_id;
      const redirectUri = clientData.redirect_uri;

      if (!clientId || !redirectUri) {
        throw new Error(
          "Google Sign-In is not configured on the server. Please define GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and GOOGLE_REDIRECT_URI environment variables to enable Google SSO."
        );
      }

      const encodedRedirectUri = encodeURIComponent(redirectUri);
      const state = Math.random().toString(36).substring(2);
      localStorage.setItem("oauth_state", state);

      const googleAuthUrl = `https://accounts.google.com/o/oauth2/v2/auth?client_id=${clientId}&redirect_uri=${encodedRedirectUri}&response_type=code&scope=openid%20email%20profile&state=${state}&prompt=select_account`;

      // Redirect the user to Google OIDC screen
      window.location.href = googleAuthUrl;
    } catch (err: any) {
      console.error("Google SSO Initialization failure:", err);
      let userMsg = err.message || "Google Single Sign-On initialization failed.";
      if (userMsg.includes("Failed to fetch")) {
        userMsg = "Cannot connect to server.";
      } else if (err instanceof TypeError || err.name === "TypeError" || userMsg.includes("NetworkError") || userMsg.includes("network")) {
        userMsg = "Network error. Please try again.";
      }
      setError(userMsg);
      setLoading(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col md:flex-row min-h-screen bg-background relative overflow-hidden">
      {/* Decorative backdrop shapes */}
      <div className="absolute top-[-20%] left-[-10%] w-[500px] h-[500px] rounded-full bg-primary/10 blur-[120px]" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[500px] h-[500px] rounded-full bg-purple-500/10 blur-[120px]" />

      {/* Brand Column (High Impact Premium Banner) */}
      <div className="flex-1 flex flex-col justify-center p-8 lg:p-16 bg-gray-500/5 dark:bg-gray-100/5 border-b md:border-b-0 md:border-r border-border relative z-10">
        <div className="max-w-md mx-auto flex flex-col gap-6">
          <div className="flex items-center gap-3">
            <div className="bg-primary/20 p-3 rounded-2xl border border-primary/30 text-primary">
              <ShieldAlert size={36} className="animate-pulse" />
            </div>
            <div>
              <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-primary to-purple-400 bg-clip-text text-transparent">
                LEXORA
              </h1>
              <p className="text-xs text-gray-400 font-semibold tracking-widest uppercase">
                AI Risk Analyzer, Rephraser & Humanizer
              </p>
            </div>
          </div>

          <div className="flex flex-col gap-4">
            <h2 className="text-2xl font-bold tracking-tight text-foreground">
              Review and Optimize Academic Writing
            </h2>
            <p className="text-xs text-gray-400 leading-relaxed">
              Lexora evaluates semantic and syntactic metrics associated with LLMs (symmetry, burstiness, cliches) without claiming certainty. It gives you explainable scores and direct suggestions to adapt writing patterns for major journal submissions.
            </p>
          </div>

          <div className="flex flex-col gap-3">
            <div className="flex items-start gap-3 bg-gray-500/5 p-3.5 rounded-2xl border border-border">
              <Star className="text-yellow-400 shrink-0 mt-0.5" size={16} />
              <p className="text-[11px] text-gray-300">
                <b>Explainable Risk Engine</b>: Analyzes 14+ indices (Lexical complexity, passive frequency, repetitive connectors) to segment sentence risk patterns.
              </p>
            </div>
            <div className="flex items-start gap-3 bg-gray-500/5 p-3.5 rounded-2xl border border-border">
              <Star className="text-purple-400 shrink-0 mt-0.5" size={16} />
              <p className="text-[11px] text-gray-300">
                <b>Semantic Paraphraser & Humanizer</b>: Varies sentence pacing (burstiness injection) and strips rigid filler sentences while preserving math equations/citations.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Forms Column */}
      <div className="flex-1 flex items-center justify-center p-6 relative z-10">
        <div className="w-full max-w-sm glass-panel border border-border p-8 rounded-3xl flex flex-col gap-6 shadow-xl shadow-black/10">
          <div className="text-center">
            <h2 className="text-xl font-extrabold text-foreground">
              {forgotPassword
                ? "Forgot Password"
                : isRegister
                ? "Create Researcher Account"
                : "Access Lexora Portal"}
            </h2>
            <p className="text-xs text-gray-400 mt-1">
              {forgotPassword
                ? "Request account recovery link"
                : isRegister
                ? "Join academic researchers worldwide"
                : "Secure workspace login panel"}
            </p>
          </div>

          {/* Messages */}
          {successMessage && (
            <div className="bg-green-500/10 border border-green-500/20 text-green-400 p-4 rounded-2xl flex items-start gap-2 text-[11px] text-left">
              <Check className="shrink-0 mt-0.5 text-green-400" size={16} />
              <p>{successMessage}</p>
            </div>
          )}

          {error && (
            <div className="bg-red-500/10 border border-red-500/20 text-red-400 p-3 rounded-2xl flex items-start gap-2 text-[11px] text-left">
              <AlertCircle size={16} className="shrink-0 mt-0.5" />
              <div>
                <p>{error}</p>
                {showResendVerification && (
                  <button
                    type="button"
                    disabled={loading || !isEmailValid}
                    onClick={handleResendVerification}
                    className="mt-2 font-semibold underline disabled:opacity-50"
                  >
                    {loading ? "Sending..." : "Resend verification link"}
                  </button>
                )}
              </div>
            </div>
          )}

          {forgotPassword ? (
            /* Forgot Password Form */
            <form onSubmit={handleForgotPasswordSubmit} className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] uppercase font-bold tracking-wider text-gray-400">Email Address</label>
                <input
                  type="email"
                  required
                  placeholder="researcher@university.edu"
                  value={email}
                  disabled={loading}
                  onChange={(e) => setEmail(e.target.value)}
                  className="bg-gray-500/5 border border-border rounded-xl px-4 py-2.5 text-xs text-foreground focus:outline-none focus:border-primary transition-colors"
                />
              </div>
              <button
                type="submit"
                disabled={loading || !isEmailValid}
                className="w-full bg-primary hover:bg-primary-hover text-white text-xs font-bold py-3 rounded-xl flex items-center justify-center gap-2 transition-all hover:scale-102 disabled:opacity-50"
              >
                <Mail size={16} />
                {loading ? "Processing..." : "Send Reset Instructions"}
              </button>
              <button
                type="button"
                disabled={loading}
                onClick={() => {
                  setForgotPassword(false);
                  setError(null);
                  setSuccessMessage(null);
                }}
                className="text-xs text-gray-400 hover:text-foreground font-semibold text-center mt-2 disabled:opacity-50"
              >
                Return to Login screen
              </button>
            </form>
          ) : (
            /* Login / Register Form */
            <form onSubmit={handleSubmit} className="flex flex-col gap-4">
              {isRegister && (
                <div className="flex flex-col gap-1.5">
                  <label className="text-[10px] uppercase font-bold tracking-wider text-gray-400">Full Name</label>
                  <input
                    type="text"
                    required
                    placeholder="Dr. Jane Doe"
                    value={fullName}
                    disabled={loading}
                    onChange={(e) => setFullName(e.target.value)}
                    className="bg-gray-500/5 border border-border rounded-xl px-4 py-2.5 text-xs text-foreground focus:outline-none focus:border-primary transition-colors"
                  />
                </div>
              )}

              <div className="flex flex-col gap-1.5">
                <label className="text-[10px] uppercase font-bold tracking-wider text-gray-400">Email Address</label>
                <input
                  type="email"
                  required
                  placeholder="researcher@university.edu"
                  value={email}
                  disabled={loading}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    setShowResendVerification(false);
                  }}
                  className="bg-gray-500/5 border border-border rounded-xl px-4 py-2.5 text-xs text-foreground focus:outline-none focus:border-primary transition-colors"
                />
              </div>

              <div className="flex flex-col gap-1.5">
                <div className="flex justify-between items-center">
                  <label className="text-[10px] uppercase font-bold tracking-wider text-gray-400">Password</label>
                  {!isRegister && (
                    <button
                      type="button"
                      disabled={loading}
                      onClick={() => {
                        setForgotPassword(true);
                        setError(null);
                        setSuccessMessage(null);
                      }}
                      className="text-[10px] font-bold text-primary hover:underline disabled:opacity-50"
                    >
                      Forgot password?
                    </button>
                  )}
                </div>
                <div className="relative">
                  <input
                    type={showPassword ? "text" : "password"}
                    required
                    placeholder="••••••••"
                    value={password}
                    disabled={loading}
                    onChange={(e) => setPassword(e.target.value)}
                    className="w-full bg-gray-500/5 border border-border rounded-xl pl-4 pr-10 py-2.5 text-xs text-foreground focus:outline-none focus:border-primary transition-colors"
                  />
                  <button
                    type="button"
                    disabled={loading}
                    onClick={() => setShowPassword(!showPassword)}
                    className="absolute right-3.5 top-3 text-gray-400 hover:text-foreground disabled:opacity-50"
                  >
                    {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
                  </button>
                </div>
              </div>

              {/* Password Complexity Requirements Visual Guide */}
              {isRegister && password && (
                <div className="flex flex-col gap-1.5 bg-gray-500/5 p-3.5 rounded-2xl border border-border">
                  <p className="text-[9px] uppercase font-extrabold tracking-wider text-gray-400 mb-1">Required Complexity</p>
                  <div className="flex flex-col gap-1">
                    {passwordRequirements.map((req, idx) => (
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
                  </div>
                </div>
              )}

              <button
                type="submit"
                disabled={loading || (isRegister && !allRequirementsMet)}
                className="w-full bg-primary hover:bg-primary-hover text-white text-xs font-bold py-3.5 rounded-xl flex items-center justify-center gap-2 transition-all hover:scale-102 hover:shadow-md hover:shadow-primary/10 disabled:opacity-50"
              >
                {isRegister ? <UserPlus size={16} /> : <LogIn size={16} />}
                {loading ? "Processing..." : isRegister ? "Register Credentials" : "Sign In Workspace"}
              </button>
            </form>
          )}

          {!forgotPassword && (
            <>
              <div className="relative my-1">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-border" />
                </div>
                <div className="relative flex justify-center text-[10px] uppercase font-bold tracking-widest">
                  <span className="bg-card px-3 text-gray-400">Or SSO</span>
                </div>
              </div>

              <button
                onClick={handleGoogleLogin}
                disabled={loading || isGoogleConfigured === false}
                className="w-full bg-gray-500/5 hover:bg-gray-500/10 text-foreground border border-border text-xs font-bold py-3.5 rounded-xl flex items-center justify-center gap-2 transition-all hover:scale-102 disabled:opacity-50"
              >
                <div className="flex gap-0.5">
                  <div className="w-1.5 h-1.5 rounded-full bg-red-500" />
                  <div className="w-1.5 h-1.5 rounded-full bg-yellow-500" />
                  <div className="w-1.5 h-1.5 rounded-full bg-green-500" />
                  <div className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                </div>
                Sign In with Google Account
              </button>

              {isGoogleConfigured === false && (
                <p className="text-[10px] text-yellow-500 text-center mt-1">
                  Google Sign-In is currently disabled. Please contact your administrator to configure Google OAuth credentials.
                </p>
              )}

              <div className="text-center text-xs">
                <button
                  type="button"
                  disabled={loading}
                  onClick={() => {
                    setIsRegister(!isRegister);
                    setError(null);
                    setSuccessMessage(null);
                  }}
                  className="text-primary hover:underline font-semibold disabled:opacity-50"
                >
                  {isRegister ? "Already registered? Sign In" : "Need an account? Register here"}
                </button>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
