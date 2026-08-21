"use client";

import React, { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { useAppStore } from "../lib/store";
import { Scan as ScanIcon, LayoutDashboard, Users, Ban, FileText, Settings as SettingsIcon, Shield, Search, ChevronRight, User, History, Bell, AlertTriangle, LogOut, PlayCircle, ScrollText, Building2, Users2 } from "lucide-react";
import { Dashboard } from "../components/Dashboard";
import { CustomerProfile } from "../components/CustomerProfile";
import { HistoryFeed } from "../components/HistoryFeed";
import { NotificationFeed } from "../components/NotificationFeed";
import { UsersAdmin } from "../components/Users";
import { VenuesAdmin } from "../components/Venues";
import { Occupancy } from "../components/Occupancy";
import { motion, AnimatePresence } from "framer-motion";
import { apiFetch, getToken, getSession, clearSession, setOnUnauthorized, runRetentionNow, getRetentionLogs, RetentionLog } from "../lib/api";

export default function Home() {
  const router = useRouter();
  const { activeTab, setActiveTab, setCustomers, customers, resetStore } = useAppStore();
  const [mounted, setMounted] = useState(false);
  const [checkingAuth, setCheckingAuth] = useState(true);
  const [searchTerm, setSearchTerm] = useState("");
  const [selectedCustomerId, setSelectedCustomerId] = useState<string | null>(null);
  // Resolved live from the polling-refreshed `customers` list each render
  // (not a static snapshot) so actions taken on this screen — e.g. banning
  // this customer — are reflected immediately instead of requiring the
  // admin to back out and re-select the row to see the updated status.
  const selectedCustomer = selectedCustomerId ? customers.find((c) => c.id === selectedCustomerId) ?? null : null;
  const [session, setSession] = useState<{ email: string | null; role: string | null }>({ email: null, role: null });
  const [retentionLogs, setRetentionLogs] = useState<RetentionLog[]>([]);
  const [retentionRunning, setRetentionRunning] = useState(false);
  const [retentionError, setRetentionError] = useState<string | null>(null);

  const fetchRetentionLogs = async () => {
    try {
      setRetentionLogs(await getRetentionLogs());
    } catch (err) {
      console.error("Error fetching retention logs:", err);
    }
  };

  const handleRunRetention = async () => {
    setRetentionRunning(true);
    setRetentionError(null);
    try {
      await runRetentionNow();
      await fetchRetentionLogs();
    } catch (err: any) {
      setRetentionError(err.message);
    } finally {
      setRetentionRunning(false);
    }
  };

  const fetchVisitors = async () => {
    try {
      const response = await apiFetch("/visitors?limit=500");
      if (response.ok) {
        const data = await response.json();
        setCustomers(data);
      }
    } catch (err) {
      console.error("Error fetching visitors:", err);
    }
  };

  const handleLogout = () => {
    clearSession();
    resetStore();
    router.push("/login");
  };

  useEffect(() => {
    setOnUnauthorized(() => {
      resetStore();
      router.push("/login");
    });
    const token = getToken();
    if (!token) {
      router.push("/login");
      return;
    }
    const s = getSession();
    setSession(s);
    setCheckingAuth(false);
    setMounted(true);
    fetchVisitors();
    if (s.role === "super_admin") {
      fetchRetentionLogs();
    }
    // Each visitor row carries two freshly-signed S3 URLs (face + ID photo),
    // so polling this too aggressively both hammers the backend (an S3
    // presign call per image per customer, every tick) and constantly
    // swaps each <img>'s src to a new signature — which makes the browser
    // re-fetch the image and flicker even though the underlying photo
    // hasn't changed. 20s keeps the list reasonably fresh without either.
    const interval = setInterval(fetchVisitors, 20000);
    return () => clearInterval(interval);
  }, []);

  if (!mounted || checkingAuth) return null;

  const filteredCustomers = customers.filter(c => 
    c.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    c.documentNumber.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="flex h-screen overflow-hidden text-foreground bg-background selection:bg-primary selection:text-primary-foreground">
      
      {/* Sidebar Navigation */}
      <aside className="w-64 border-r border-border bg-card/50 backdrop-blur flex flex-col justify-between">
        <div>
          {/* Logo / Title */}
          <div className="h-16 flex items-center gap-3 px-6 border-b border-border">
            <Image src="/logo.svg" alt="VenuePass" width={28} height={28} className="rounded-md" />
            <span className="font-bold tracking-widest text-foreground uppercase text-sm">VenuePass</span>
          </div>

          {/* Nav Items */}
          <nav className="p-4 space-y-1">
            {[
              { id: 'dashboard', label: 'Platform Analytics', icon: LayoutDashboard },
              { id: 'history', label: 'Session History', icon: History },
              { id: 'notifications', label: 'Alerts & Notifications', icon: Bell },
              { id: 'visitors', label: 'Visitor Directory', icon: Users },
              { id: 'occupancy', label: 'Occupancy', icon: Users2 },
              ...(session.role === 'super_admin' || session.role === 'venue_admin'
                ? [{ id: 'users', label: 'Staff Accounts', icon: Shield }]
                : []),
              ...(session.role === 'super_admin'
                ? [{ id: 'venues', label: 'Venues', icon: Building2 }]
                : []),
              { id: 'settings', label: 'Settings', icon: SettingsIcon },
            ].map(item => {
              const Icon = item.icon;
              const active = activeTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => setActiveTab(item.id as any)}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium transition-all ${
                    active 
                      ? 'bg-primary/10 text-primary shadow-sm' 
                      : 'text-muted-foreground hover:bg-muted/50 hover:text-foreground'
                  }`}
                >
                  <Icon className="h-4 w-4" />
                  {item.label}
                </button>
              );
            })}
          </nav>
        </div>

        {/* User profile / footer */}
        <div className="p-4 border-t border-border">
          <div className="flex items-center gap-3 bg-muted/30 p-3 rounded-xl border border-border/50">
            <div className="h-8 w-8 rounded-full bg-primary/20 flex items-center justify-center font-bold text-xs text-primary border border-primary/30">
              {(session.email || "?").slice(0, 2).toUpperCase()}
            </div>
            <div className="flex-1 min-w-0">
              <p className="text-xs font-bold truncate">{session.email || "Unknown"}</p>
              <p className="text-[10px] text-muted-foreground font-medium capitalize">{(session.role || "").replace(/_/g, " ")}</p>
            </div>
            <button
              onClick={handleLogout}
              title="Sign out"
              className="p-1.5 rounded-lg text-muted-foreground hover:text-destructive hover:bg-destructive/10 transition-colors"
            >
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="flex-1 flex flex-col overflow-hidden relative">
        {/* Background ambient glow */}
        <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] bg-primary/10 blur-[120px] rounded-full pointer-events-none" />
        <div className="absolute bottom-[-20%] right-[-10%] w-[40%] h-[40%] bg-primary/5 blur-[100px] rounded-full pointer-events-none" />

        {/* Header */}
        <header className="h-16 border-b border-border px-8 flex items-center justify-between bg-card/30 backdrop-blur z-10">
          <div className="flex items-center gap-3">
            <span className="h-2 w-2 rounded-full bg-primary animate-pulse shadow-[0_0_10px_rgba(var(--primary),0.8)]"></span>
            <span className="text-xs text-muted-foreground font-mono font-bold tracking-wider">GATEWAY 1 • L'ETOILE SOHO</span>
          </div>
          <div className="flex items-center gap-6">
            <span className="text-xs text-muted-foreground font-medium">Status: <span className="font-mono font-bold text-primary">ONLINE</span></span>
          </div>
        </header>

        {/* Tab content wrapper */}
        <div className="flex-1 overflow-y-auto p-8 z-10">
          
          <AnimatePresence mode="wait">

            {activeTab === 'dashboard' && (
              <motion.div key="dashboard" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}>
                <Dashboard />
              </motion.div>
            )}

            {activeTab === 'history' && (
              <motion.div key="history" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}>
                <HistoryFeed />
              </motion.div>
            )}

            {activeTab === 'notifications' && (
              <motion.div key="notifications" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}>
                <NotificationFeed />
              </motion.div>
            )}

            {activeTab === 'visitors' && (
              <motion.div key="visitors" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}>
                {selectedCustomer ? (
                  <CustomerProfile customer={selectedCustomer} onBack={() => setSelectedCustomerId(null)} />
                ) : (
                  <div className="space-y-6 max-w-7xl mx-auto">
                    <div className="flex justify-between items-center gap-4 glass-panel p-4 rounded-xl">
                      <div className="relative flex-1 max-w-md">
                        <Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                        <input
                          type="text"
                          value={searchTerm}
                          onChange={(e) => setSearchTerm(e.target.value)}
                          placeholder="Search visitors by name or ID..."
                          className="w-full bg-background border border-border rounded-lg pl-9 pr-4 py-2 text-sm placeholder-muted-foreground text-foreground outline-none focus:border-primary transition-all"
                        />
                      </div>
                    </div>

                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                      {filteredCustomers.map(customer => (
                        <div key={customer.id} className="glass-panel rounded-xl overflow-hidden hover:border-primary/50 transition-all group flex flex-col justify-between">
                          <div className="p-6">
                            <div className="flex justify-between items-start mb-4">
                              <div className="flex items-center gap-3">
                                <div className="w-10 h-10 rounded-full bg-muted flex items-center justify-center shrink-0">
                                  <User className="w-5 h-5 text-muted-foreground" />
                                </div>
                                <div>
                                  <h4 className="text-base font-bold text-foreground">{customer.name}</h4>
                                  <p className="text-[10px] text-muted-foreground font-mono mt-0.5">{customer.documentNumber}</p>
                                </div>
                              </div>
                            </div>

                            <div className="grid grid-cols-2 gap-4">
                              <div className="bg-muted/30 p-3 rounded-lg border border-border/50">
                                <p className="text-[10px] text-muted-foreground font-semibold uppercase tracking-wider mb-1">Status</p>
                                <span className={`text-xs font-bold ${
                                  customer.blacklistStatus === 'permanent' ? 'text-destructive' : 'text-primary'
                                }`}>
                                  {customer.blacklistStatus === 'permanent' ? 'BANNED' : 'CLEARED'}
                                </span>
                              </div>
                              <div className="bg-muted/30 p-3 rounded-lg border border-border/50">
                                <p className="text-[10px] text-muted-foreground font-semibold uppercase tracking-wider mb-1">Visits</p>
                                <span className="text-xs font-bold text-foreground">{customer.visitCount} Total</span>
                              </div>
                            </div>
                          </div>

                          <div className="bg-card/50 border-t border-border/50 px-6 py-3 flex justify-between items-center group-hover:bg-primary/5 transition-colors">
                            <span className="text-[10px] text-muted-foreground font-mono">ID: {customer.id}</span>
                            <button
                              onClick={() => setSelectedCustomerId(customer.id)}
                              className="text-xs font-bold text-primary flex items-center gap-1 hover:translate-x-1 transition-transform"
                            >
                              View Profile <ChevronRight className="h-4 w-4" />
                            </button>
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </motion.div>
            )}

            {activeTab === 'users' && (session.role === 'super_admin' || session.role === 'venue_admin') && (
              <motion.div key="users" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}>
                <UsersAdmin />
              </motion.div>
            )}

            {activeTab === 'venues' && session.role === 'super_admin' && (
              <motion.div key="venues" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}>
                <VenuesAdmin />
              </motion.div>
            )}

            {activeTab === 'occupancy' && (
              <motion.div key="occupancy" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }}>
                <Occupancy />
              </motion.div>
            )}

            {activeTab === 'settings' && (
              <motion.div key="settings" initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="max-w-4xl mx-auto space-y-8">
                <div className="flex items-center gap-3 mb-8">
                  <SettingsIcon className="h-8 w-8 text-primary" />
                  <h2 className="text-2xl font-bold text-foreground">Platform Settings</h2>
                </div>

                {session.role !== 'super_admin' ? (
                  <div className="glass-panel rounded-xl p-8 text-muted-foreground text-sm">
                    Only a super admin can access the danger zone.
                  </div>
                ) : (
                <div className="space-y-8">
                <div className="glass-panel rounded-xl p-8">
                  <h3 className="text-xl font-bold text-foreground mb-2 flex items-center gap-2">
                    <PlayCircle className="w-6 h-6 text-primary" />
                    Data Retention
                  </h3>
                  <p className="text-muted-foreground mb-6">
                    Expired visitor records are anonymized automatically every hour, per each venue's configured
                    retention window (7 days by default after a PASS decision). Blacklisted visitors are never
                    anonymized while their ban is active.
                  </p>

                  {retentionError && (
                    <div className="mb-4 text-sm text-destructive">{retentionError}</div>
                  )}

                  <button
                    onClick={handleRunRetention}
                    disabled={retentionRunning}
                    className="bg-primary/10 hover:bg-primary/20 text-primary border border-primary/30 font-bold py-3 px-6 rounded-lg transition-colors flex items-center gap-2 disabled:opacity-50 mb-6"
                  >
                    <PlayCircle className="w-5 h-5" />
                    {retentionRunning ? "Running..." : "Run Retention Now"}
                  </button>

                  <div className="flex items-center gap-2 mb-3 text-sm font-semibold text-muted-foreground">
                    <ScrollText className="w-4 h-4" />
                    Recent Runs
                  </div>
                  <div className="space-y-2 max-h-72 overflow-y-auto">
                    {retentionLogs.length === 0 ? (
                      <div className="text-sm text-muted-foreground p-4 text-center border border-border/50 rounded-lg">
                        No retention runs recorded yet.
                      </div>
                    ) : (
                      retentionLogs.map((log) => (
                        <div key={log.id} className="flex items-center justify-between text-xs p-3 rounded-lg bg-muted/30 border border-border/50">
                          <div className="flex items-center gap-3">
                            <span className={`font-bold uppercase px-2 py-0.5 rounded ${log.details.trigger === 'manual' ? 'bg-primary/10 text-primary' : 'bg-muted text-muted-foreground'}`}>
                              {log.details.trigger}
                            </span>
                            <span className="text-muted-foreground">{new Date(log.timestamp).toLocaleString()}</span>
                          </div>
                          <div className="text-foreground font-medium">
                            {log.details.anonymized_count} anonymized · {log.details.skipped_blacklisted_count} skipped
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                <div className="glass-panel rounded-xl p-8 border border-destructive/20">
                  <h3 className="text-xl font-bold text-destructive mb-2 flex items-center gap-2">
                    <AlertTriangle className="w-6 h-6" />
                    Danger Zone
                  </h3>
                  <p className="text-muted-foreground mb-6">
                    Permanently flush all visitor data, ID scans, verification sessions, and system notifications.
                    <strong> Data associated with blacklisted/blocked users will be strictly preserved.</strong>
                  </p>

                  <button
                    onClick={async () => {
                      if (!confirm("Are you absolutely sure you want to completely flush all non-blacklisted data? This cannot be undone.")) {
                        return;
                      }
                      try {
                        const res = await apiFetch("/admin/flush", { method: 'POST' });
                        const data = await res.json();
                        if (data.success) {
                          alert(data.message);
                          window.location.reload();
                        } else {
                          alert("Flush failed: " + (data.detail || data.message));
                        }
                      } catch (err) {
                        alert("Error triggering flush.");
                        console.error(err);
                      }
                    }}
                    className="bg-destructive/10 hover:bg-destructive/20 text-destructive border border-destructive/30 font-bold py-3 px-6 rounded-lg transition-colors flex items-center gap-2"
                  >
                    <Ban className="w-5 h-5" />
                    Flush System Data
                  </button>
                </div>
                </div>
                )}
              </motion.div>
            )}
          </AnimatePresence>

        </div>
      </main>
    </div>
  );
}
