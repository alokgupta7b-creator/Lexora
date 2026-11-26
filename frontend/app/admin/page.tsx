"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { ShieldCheck, Users, HardDrive, Activity, Radio, ToggleLeft, ToggleRight, Sparkles } from "lucide-react";
import Navbar from "@/components/navbar";
import Sidebar from "@/components/sidebar";

interface UserItem {
  id: number;
  email: string;
  full_name: string | null;
  role: string;
  is_active: boolean;
  created_at: string;
}

export default function AdminPage() {
  const router = useRouter();

  const [users, setUsers] = useState<UserItem[]>([]);
  const [stats, setStats] = useState<any>(null);
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchAdminData = async () => {
    const token = localStorage.getItem("token");
    const role = localStorage.getItem("userRole");

    if (!token || role !== "admin") {
      router.push("/dashboard");
      return;
    }

    try {
      setLoading(true);
      setError(null);

      // 1. Fetch system statistics
      const statsRes = await fetch("http://localhost:8000/api/v1/admin/system-stats", {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (!statsRes.ok) throw new Error("Could not download admin telemetry");
      const statsData = await statsRes.json();
      setStats(statsData);

      // 2. Fetch users list
      const usersRes = await fetch("http://localhost:8000/api/v1/admin/users", {
        headers: { Authorization: `Bearer ${token}` }
      });
      if (usersRes.ok) {
        const usersData = await usersRes.json();
        setUsers(usersData);
      }
      
    } catch (err: any) {
      setError(err.message || "Failed to fetch administrative metrics.");
    } finally {
      setLoading(false);
    }
  };

  const handleToggleStatus = async (user: UserItem) => {
    const token = localStorage.getItem("token");
    try {
      const response = await fetch(`http://localhost:8000/api/v1/admin/user/${user.id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          role: user.role,
          is_active: !user.is_active
        })
      });

      if (response.ok) {
        fetchAdminData();
      }
    } catch (err) {
      console.error(err);
    }
  };

  const handleToggleRole = async (user: UserItem) => {
    const token = localStorage.getItem("token");
    const nextRole = user.role === "admin" ? "user" : "admin";
    try {
      const response = await fetch(`http://localhost:8000/api/v1/admin/user/${user.id}`, {
        method: "PUT",
        headers: {
          "Content-Type": "application/json",
          Authorization: `Bearer ${token}`
        },
        body: JSON.stringify({
          role: nextRole,
          is_active: user.is_active
        })
      });

      if (response.ok) {
        fetchAdminData();
      }
    } catch (err) {
      console.error(err);
    }
  };

  useEffect(() => {
    fetchAdminData();
  }, []);

  if (loading) {
    return (
      <div className="flex-grow flex justify-center items-center">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-4 border-primary border-t-transparent rounded-full animate-spin" />
          <span className="text-xs font-bold text-gray-400">Loading Administrative Telemetry...</span>
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
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight">Admin Control Center</h1>
            <p className="text-xs text-gray-400 mt-1">
              Monitor active server telemetry, grant administrator roles, or suspend user access.
            </p>
          </div>

          {/* Server Telemetry Hud */}
          {stats && (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
              <div className="glass-panel border border-border p-6 rounded-3xl flex items-center gap-4">
                <div className="bg-primary/10 border border-primary/20 text-primary p-3 rounded-2xl">
                  <Activity size={24} />
                </div>
                <div>
                  <p className="text-[10px] text-gray-400 uppercase tracking-widest font-bold">CPU Load</p>
                  <h3 className="text-xl font-black text-foreground mt-1">{stats.telemetry?.cpu_utilization_percent}%</h3>
                </div>
              </div>

              <div className="glass-panel border border-border p-6 rounded-3xl flex items-center gap-4">
                <div className="bg-purple-500/10 border border-purple-500/20 text-purple-400 p-3 rounded-2xl">
                  <HardDrive size={24} />
                </div>
                <div>
                  <p className="text-[10px] text-gray-400 uppercase tracking-widest font-bold">RAM utilization</p>
                  <h3 className="text-xl font-black text-foreground mt-1">{stats.telemetry?.ram_utilization_percent}%</h3>
                </div>
              </div>

              <div className="glass-panel border border-border p-6 rounded-3xl flex items-center gap-4">
                <div className="bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 p-3 rounded-2xl">
                  <Radio size={24} />
                </div>
                <div>
                  <p className="text-[10px] text-gray-400 uppercase tracking-widest font-bold">API Success Rate</p>
                  <h3 className="text-xl font-black text-foreground mt-1">{stats.telemetry?.api_request_success_rate}%</h3>
                </div>
              </div>

              <div className="glass-panel border border-border p-6 rounded-3xl flex items-center gap-4">
                <div className="bg-yellow-500/10 border border-yellow-500/20 text-yellow-400 p-3 rounded-2xl">
                  <ShieldCheck size={24} />
                </div>
                <div>
                  <p className="text-[10px] text-gray-400 uppercase tracking-widest font-bold">System Risk avg</p>
                  <h3 className="text-xl font-black text-foreground mt-1">{stats.stats?.system_average_ai_risk}%</h3>
                </div>
              </div>
            </div>
          )}

          <div className="grid grid-cols-1 xl:grid-cols-3 gap-8">
            {/* System counts HUD */}
            <div className="xl:col-span-1 flex flex-col gap-6">
              <div className="glass-panel border border-border p-6 rounded-3xl flex flex-col gap-4">
                <h2 className="text-sm font-bold uppercase tracking-wider flex items-center gap-2 pb-2 border-b border-border">
                  <Users size={18} className="text-primary" />
                  System Statistics
                </h2>
                {stats && (
                  <div className="flex flex-col gap-3 text-xs">
                    <div className="flex justify-between items-center bg-gray-500/5 p-3 rounded-xl border border-border">
                      <span className="text-gray-400 font-semibold">Total Accounts:</span>
                      <span className="font-bold text-foreground">{stats.stats?.total_users}</span>
                    </div>
                    <div className="flex justify-between items-center bg-gray-500/5 p-3 rounded-xl border border-border">
                      <span className="text-gray-400 font-semibold">Total Uploaded papers:</span>
                      <span className="font-bold text-foreground">{stats.stats?.total_documents}</span>
                    </div>
                    <div className="flex justify-between items-center bg-gray-500/5 p-3 rounded-xl border border-border">
                      <span className="text-gray-400 font-semibold">Stylistic Audits:</span>
                      <span className="font-bold text-foreground">{stats.stats?.total_analyses_completed}</span>
                    </div>
                    <div className="flex justify-between items-center bg-gray-500/5 p-3 rounded-xl border border-border">
                      <span className="text-gray-400 font-semibold">Reports Exported:</span>
                      <span className="font-bold text-foreground">{stats.stats?.total_reports_exported}</span>
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* User Accounts Management list */}
            <div className="xl:col-span-2 glass-panel border border-border p-6 rounded-3xl flex flex-col gap-4">
              <h2 className="text-sm font-bold uppercase tracking-wider flex items-center gap-2">
                <Users size={18} className="text-primary" />
                Moderation Table
              </h2>

              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs border-collapse">
                  <thead>
                    <tr className="border-b border-border text-gray-400 font-bold">
                      <th className="pb-3">Researcher</th>
                      <th className="pb-3">Status</th>
                      <th className="pb-3">Role</th>
                      <th className="pb-3 text-right">Moderations</th>
                    </tr>
                  </thead>
                  <tbody>
                    {users.map((user) => (
                      <tr key={user.id} className="border-b border-border hover:bg-gray-500/5 transition-colors">
                        <td className="py-4">
                          <h4 className="font-semibold text-foreground">{user.full_name || "Scholar"}</h4>
                          <span className="text-[10px] text-gray-400 mt-0.5">{user.email}</span>
                        </td>
                        <td className="py-4">
                          <span className={`text-[10px] font-bold px-2 py-0.5 rounded ${
                            user.is_active ? "bg-emerald-500/10 text-emerald-400" : "bg-red-500/10 text-red-400"
                          }`}>
                            {user.is_active ? "Active" : "Suspended"}
                          </span>
                        </td>
                        <td className="py-4 uppercase text-[9px] font-bold">
                          <span className="bg-gray-500/10 px-2.5 py-1 rounded border border-border text-gray-300">
                            {user.role}
                          </span>
                        </td>
                        <td className="py-4 text-right flex items-center justify-end gap-2">
                          <button
                            onClick={() => handleToggleRole(user)}
                            className="bg-gray-500/5 hover:bg-gray-500/10 border border-border text-[9px] font-bold uppercase px-3 py-1.5 rounded-xl transition-all"
                          >
                            Toggle Role
                          </button>
                          <button
                            onClick={() => handleToggleStatus(user)}
                            className={`p-1.5 rounded-xl transition-all ${
                              user.is_active ? "text-red-400 hover:bg-red-500/10" : "text-emerald-400 hover:bg-emerald-500/10"
                            }`}
                          >
                            {user.is_active ? <ToggleRight size={24} /> : <ToggleLeft size={24} />}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}
