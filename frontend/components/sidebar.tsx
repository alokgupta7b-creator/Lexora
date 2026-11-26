"use client";

import { useRouter, usePathname } from "next/navigation";
import { LayoutDashboard, ShieldCheck, RefreshCw, Settings, BookOpen } from "lucide-react";
import { useEffect, useState } from "react";

export default function Sidebar() {
  const router = useRouter();
  const pathname = usePathname();
  const [isAdmin, setIsAdmin] = useState(false);

  useEffect(() => {
    const role = localStorage.getItem("userRole");
    setIsAdmin(role === "admin");
  }, []);

  const menuItems = [
    {
      name: "Dashboard Workspace",
      path: "/dashboard",
      icon: LayoutDashboard,
      desc: "Overview & saved history"
    },
    {
      name: "Linguistic Analyzer",
      path: "/analyze",
      icon: ShieldCheck,
      desc: "Linguistic risk profiling"
    },
    {
      name: "Paraphraser & Humanizer",
      path: "/rephrase",
      icon: RefreshCw,
      desc: "Flow and burstiness engines"
    }
  ];

  if (isAdmin) {
    menuItems.push({
      name: "Admin Control Center",
      path: "/admin",
      icon: Settings,
      desc: "Telemetry & system limits"
    });
  }

  return (
    <aside className="w-80 border-r border-border h-[calc(100vh-73px)] hidden lg:flex flex-col p-6 sticky top-[73px] transition-all bg-sidebar">
      <div className="flex-1 flex flex-col gap-5">
        <div className="px-3">
          <p className="text-[10px] text-gray-400 tracking-wider font-semibold uppercase">
            Workspace Navigation
          </p>
        </div>
        
        <nav className="flex flex-col gap-2">
          {menuItems.map((item) => {
            const isActive = pathname === item.path;
            const Icon = item.icon;
            
            return (
              <button
                key={item.path}
                onClick={() => router.push(item.path)}
                className={`flex gap-4 items-center text-left p-3 rounded-2xl border transition-all duration-300 group hover:scale-[1.02] ${
                  isActive
                    ? "bg-primary text-white border-primary shadow-lg shadow-primary/20"
                    : "border-transparent text-gray-400 hover:text-foreground hover:bg-gray-500/5 hover:border-border"
                }`}
              >
                <div className={`p-2 rounded-xl border ${
                  isActive ? "bg-white/10 border-white/20 text-white" : "bg-gray-500/10 border-border text-gray-400 group-hover:text-primary group-hover:bg-primary/10 group-hover:border-primary/20"
                }`}>
                  <Icon size={20} />
                </div>
                <div>
                  <h3 className={`text-sm font-semibold tracking-wide ${isActive ? "text-white" : "text-foreground"}`}>
                    {item.name}
                  </h3>
                  <p className={`text-[10px] ${isActive ? "text-indigo-200" : "text-gray-400"}`}>
                    {item.desc}
                  </p>
                </div>
              </button>
            );
          })}
        </nav>
      </div>

      <div className="glass-panel p-4 rounded-3xl border border-border flex flex-col gap-3">
        <div className="flex items-center gap-2 text-primary">
          <BookOpen size={16} />
          <h4 className="text-xs font-bold uppercase tracking-wider">Research Policy</h4>
        </div>
        <p className="text-[10px] text-gray-400 leading-relaxed">
          Lexora scores are explainable linguistic metrics based on word variance and templates. We promote academic integrity and structural quality.
        </p>
      </div>
    </aside>
  );
}
