"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { Sun, Moon, LogOut, ShieldAlert, Award } from "lucide-react";

export default function Navbar() {
  const router = useRouter();
  const [theme, setTheme] = useState("dark");
  const [userEmail, setUserEmail] = useState<string | null>(null);

  useEffect(() => {
    // Determine active theme
    const isDark = document.documentElement.classList.contains("dark");
    setTheme(isDark ? "dark" : "light");
    
    // Get user details
    const email = localStorage.getItem("userEmail");
    setUserEmail(email || "Researcher");
  }, []);

  const toggleTheme = () => {
    const nextTheme = theme === "dark" ? "light" : "dark";
    if (nextTheme === "dark") {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
    setTheme(nextTheme);
  };

  const handleLogout = async () => {
    try {
      await fetch("http://localhost:8000/api/v1/auth/logout", {
        method: "POST",
        credentials: "include",
      });
    } catch (err) {
      console.error("Backend logout failed:", err);
    } finally {
      localStorage.removeItem("token");
      localStorage.removeItem("userEmail");
      localStorage.removeItem("userRole");
      router.push("/login");
    }
  };

  return (
    <header className="glass-panel border-b border-border w-full py-4 px-6 sticky top-0 z-50 flex justify-between items-center transition-all duration-300">
      <div className="flex items-center gap-3 cursor-pointer" onClick={() => router.push("/dashboard")}>
        <div className="bg-primary/20 p-2 rounded-xl text-primary border border-primary/30">
          <ShieldAlert size={24} className="animate-pulse" />
        </div>
        <div>
          <h1 className="text-xl font-bold tracking-tight bg-gradient-to-r from-primary via-indigo-400 to-purple-400 bg-clip-text text-transparent">
            LEXORA
          </h1>
          <p className="text-[10px] text-gray-400 tracking-widest font-semibold uppercase">
            Writing Intelligence Platform
          </p>
        </div>
      </div>

      <div className="flex items-center gap-4">
        {userEmail && (
          <div className="hidden sm:flex items-center gap-2 bg-gray-500/10 dark:bg-gray-100/5 px-3 py-1.5 rounded-full border border-border">
            <Award size={16} className="text-yellow-400" />
            <span className="text-xs font-medium text-gray-300">{userEmail}</span>
          </div>
        )}


        <button
          onClick={handleLogout}
          className="flex items-center gap-2 bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 px-3 py-2 rounded-xl text-xs font-semibold transition-all hover:scale-105"
        >
          <LogOut size={16} />
          <span className="hidden md:inline">Sign Out</span>
        </button>
      </div>
    </header>
  );
}
