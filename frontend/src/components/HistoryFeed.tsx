import React, { useState, useEffect } from "react";
import { History, CheckCircle, XCircle, AlertTriangle, Ban } from "lucide-react";
import { apiFetch } from "../lib/api";

const DECISION_BADGES: Record<string, { label: string; className: string; icon: React.ComponentType<{ className?: string }> }> = {
  pass: { label: "PASS", className: "text-green-500", icon: CheckCircle },
  deny: { label: "DENY", className: "text-red-500", icon: XCircle },
  check: { label: "CHECK", className: "text-orange-500", icon: AlertTriangle },
  block: { label: "BLOCKED", className: "text-red-500", icon: Ban },
  restrict: { label: "BLOCKED", className: "text-red-500", icon: Ban },
};

export function HistoryFeed() {
  const [history, setHistory] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const response = await apiFetch("/sessions/history?limit=500");
        if (response.ok) {
          const data = await response.json();
          setHistory(data);
        }
      } catch (err) {
        console.error("Error fetching history:", err);
      } finally {
        setLoading(false);
      }
    };
    
    fetchHistory();
    // 20s: a historical log doesn't need near-real-time refresh, and each
    // tick pulls up to 500 rows.
    const interval = setInterval(fetchHistory, 20000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return <div className="flex justify-center items-center h-64 text-muted-foreground">Loading history...</div>;
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center gap-3 mb-8">
        <History className="h-8 w-8 text-primary" />
        <h2 className="text-2xl font-bold text-foreground">Session History</h2>
      </div>

      <div className="glass-panel rounded-xl overflow-hidden">
        <table className="w-full text-left text-sm text-muted-foreground">
          <thead className="text-xs uppercase bg-muted/50 text-foreground">
            <tr>
              <th className="px-6 py-4">Session ID</th>
              <th className="px-6 py-4">Timestamp</th>
              <th className="px-6 py-4">Status</th>
              <th className="px-6 py-4">Final Decision</th>
            </tr>
          </thead>
          <tbody>
            {history.length === 0 ? (
              <tr>
                <td colSpan={4} className="px-6 py-8 text-center">No history available</td>
              </tr>
            ) : (
              history.map((session, i) => (
                <tr key={i} className="border-b border-border/50 hover:bg-muted/20 transition-colors">
                  <td className="px-6 py-4 font-mono text-foreground">{session.session_id.substring(0, 8)}</td>
                  <td className="px-6 py-4">{new Date(session.created_at).toLocaleString()}</td>
                  <td className="px-6 py-4">{session.status}</td>
                  <td className="px-6 py-4">
                    {(() => {
                      const decision = (session.final_decision || "").toLowerCase();
                      const badge = DECISION_BADGES[decision];
                      if (badge) {
                        const Icon = badge.icon;
                        return (
                          <span className={`flex items-center gap-2 ${badge.className}`}>
                            <Icon className="h-4 w-4" /> {badge.label}
                          </span>
                        );
                      }
                      return <span className="text-muted-foreground">{session.final_decision || "PENDING"}</span>;
                    })()}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
