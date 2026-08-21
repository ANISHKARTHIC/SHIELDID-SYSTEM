"use client";

import React, { useState, useEffect } from "react";
import { Users, Users2, AlertTriangle, Shield, CheckCircle, Clock, Settings as SettingsIcon, FileText } from "lucide-react";
import { useAppStore } from "../lib/store";
import { apiFetch, getLiveCount, OccupancyCount } from "../lib/api";

export function Dashboard() {
  const { customers, incidents, setActiveTab } = useAppStore();
  const [venueStats, setVenueStats] = useState({ passed: 0, checked: 0, denied: 0 });
  const [fraudQueue, setFraudQueue] = useState<any[]>([]);
  const [occupancy, setOccupancy] = useState<OccupancyCount | null>(null);

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        // Deliberately NOT /operator/stats here — that endpoint is scoped to
        // the calling operator's own sessions from today only (correct for
        // Flutter's "your shift" summary), which would show near-zero
        // numbers for any admin who isn't personally scanning IDs. This
        // dashboard is a venue-wide overview, so it derives its tiles from
        // /sessions/history instead, which is already venue-scoped.
        const historyRes = await apiFetch("/sessions/history?limit=500");

        if (historyRes.ok) {
          const historyData = await historyRes.json();
          const passed = historyData.filter((h: any) => h.final_decision === 'pass').length;
          const checked = historyData.filter((h: any) => h.final_decision === 'check').length;
          const denied = historyData.filter((h: any) => ['deny', 'block', 'restrict'].includes(h.final_decision)).length;
          setVenueStats({ passed, checked, denied });

          const queue = historyData.filter((h: any) => h.final_decision === 'deny' || h.final_decision === 'check' || h.status === 'FRAUD_REVIEW');
          setFraudQueue(queue);
        }

        setOccupancy(await getLiveCount());
      } catch (err) {
        console.error("Error fetching dashboard data:", err);
      }
    };

    fetchDashboardData();
    // 15s: this overview doesn't need sub-5s freshness, and each tick
    // pulls up to 500 session-history rows plus a live occupancy count.
    const interval = setInterval(fetchDashboardData, 15000);
    return () => clearInterval(interval);
  }, []);

  const passed = venueStats.passed;
  const checked = venueStats.checked;
  const denied = venueStats.denied;
  
  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="flex items-center justify-between">
        <h2 className="text-3xl font-bold tracking-tight">Overview</h2>
        <div className="flex items-center gap-2 text-muted-foreground text-sm glass-panel px-4 py-2 rounded-full">
          <Clock className="w-4 h-4" />
          <span>Live Updates</span>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-5">
        <button
          onClick={() => setActiveTab('occupancy')}
          className={`glass-panel rounded-xl p-6 relative overflow-hidden group text-left transition-colors hover:bg-card/60 ${
            occupancy?.at_capacity ? 'border border-destructive/40' : ''
          }`}
        >
          <div className={`absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity ${occupancy?.at_capacity ? 'text-destructive' : 'text-primary'}`}>
            <Users2 className="w-16 h-16" />
          </div>
          <p className="text-sm font-medium text-muted-foreground mb-1">Currently Inside</p>
          <p className={`text-4xl font-bold ${occupancy?.at_capacity ? 'text-destructive' : 'text-primary'}`}>
            {occupancy?.current_count ?? '—'}
            {occupancy?.max_capacity != null && (
              <span className="text-lg text-muted-foreground font-medium"> / {occupancy.max_capacity}</span>
            )}
          </p>
          {occupancy?.at_capacity && (
            <p className="text-xs font-bold text-destructive mt-1 uppercase tracking-wider">At Capacity</p>
          )}
        </button>

        <div className="glass-panel rounded-xl p-6 relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
            <Users className="w-16 h-16" />
          </div>
          <p className="text-sm font-medium text-muted-foreground mb-1">Total Visitors</p>
          <p className="text-4xl font-bold">{customers.length}</p>
        </div>

        <div className="glass-panel rounded-xl p-6 relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity text-primary">
            <CheckCircle className="w-16 h-16" />
          </div>
          <p className="text-sm font-medium text-muted-foreground mb-1">Passed Entries</p>
          <p className="text-4xl font-bold text-primary">{passed}</p>
        </div>

        <div className="glass-panel rounded-xl p-6 relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity text-yellow-500">
            <AlertTriangle className="w-16 h-16" />
          </div>
          <p className="text-sm font-medium text-muted-foreground mb-1">Manual Checks</p>
          <p className="text-4xl font-bold text-yellow-500">{checked}</p>
        </div>

        <div className="glass-panel rounded-xl p-6 relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity text-destructive">
            <Shield className="w-16 h-16" />
          </div>
          <p className="text-sm font-medium text-muted-foreground mb-1">Denied</p>
          <p className="text-4xl font-bold text-destructive">{denied}</p>
        </div>
      </div>

      <div className="grid gap-6 md:grid-cols-2">
        <div className="glass-panel rounded-xl p-6">
          <h3 className="text-lg font-semibold mb-4 text-orange-500">Fraud Review Queue</h3>
          <div className="space-y-4">
            {fraudQueue.length === 0 ? (
              <p className="text-sm text-muted-foreground">No sessions pending supervisor review.</p>
            ) : (
              fraudQueue.slice(0, 5).map((log: any) => (
                <div key={log.session_id} className="flex items-center justify-between p-3 rounded-lg bg-card/50 border border-border/50 border-orange-500/30">
                  <div>
                    <p className="font-mono font-medium text-orange-400">{log.session_id.substring(0, 8)}</p>
                    <p className="text-xs text-muted-foreground">{new Date(log.created_at).toLocaleTimeString()}</p>
                  </div>
                  <button className="px-3 py-1 rounded bg-orange-500/20 text-orange-500 text-xs font-semibold hover:bg-orange-500/40">
                    Review
                  </button>
                </div>
              ))
            )}
          </div>
        </div>

        <div className="glass-panel rounded-xl p-6">
          <h3 className="text-lg font-semibold mb-4 text-blue-400">Enterprise Settings</h3>
          <div className="grid grid-cols-2 gap-4">
            <button className="p-4 rounded-lg bg-card/50 border border-border/50 hover:bg-card/80 transition-colors flex flex-col items-center justify-center gap-2">
              <SettingsIcon className="w-8 h-8 text-muted-foreground" />
              <span className="text-sm font-medium">Policy Engine</span>
            </button>
            <button
              onClick={() => setActiveTab('users')}
              className="p-4 rounded-lg bg-card/50 border border-border/50 hover:bg-card/80 transition-colors flex flex-col items-center justify-center gap-2"
            >
              <Users className="w-8 h-8 text-muted-foreground" />
              <span className="text-sm font-medium">Role Management</span>
            </button>
            <button
              onClick={() => setActiveTab('venues')}
              className="p-4 rounded-lg bg-card/50 border border-border/50 hover:bg-card/80 transition-colors flex flex-col items-center justify-center gap-2"
            >
              <Shield className="w-8 h-8 text-muted-foreground" />
              <span className="text-sm font-medium">Venue Config</span>
            </button>
            <button className="p-4 rounded-lg bg-card/50 border border-border/50 hover:bg-card/80 transition-colors flex flex-col items-center justify-center gap-2">
              <FileText className="w-8 h-8 text-muted-foreground" />
              <span className="text-sm font-medium">Audit Logs</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
