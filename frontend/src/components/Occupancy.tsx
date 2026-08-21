import React, { useState, useEffect } from "react";
import { Users2, LogOut, Ban } from "lucide-react";
import { getCurrentOccupants, getLiveCount, checkOutOccupant, createBan, Occupant, OccupancyCount } from "../lib/api";

export function Occupancy() {
  const [occupants, setOccupants] = useState<Occupant[]>([]);
  const [count, setCount] = useState<OccupancyCount | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [checkingOutId, setCheckingOutId] = useState<number | null>(null);
  const [banTarget, setBanTarget] = useState<Occupant | null>(null);
  const [banReason, setBanReason] = useState("");
  const [banning, setBanning] = useState(false);
  const [banNotice, setBanNotice] = useState<string | null>(null);

  const refresh = async () => {
    try {
      const [occupantsData, countData] = await Promise.all([getCurrentOccupants(), getLiveCount()]);
      setOccupants(occupantsData);
      setCount(countData);
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
    // 10s: who's-currently-inside is operationally live-relevant (door
    // staff use it in real time), so this stays faster than the other
    // tabs, but 3s was still excessive.
    const interval = setInterval(refresh, 10000);
    return () => clearInterval(interval);
  }, []);

  const handleCheckout = async (occupant: Occupant) => {
    setCheckingOutId(occupant.occupancy_id);
    setError(null);
    try {
      await checkOutOccupant(occupant.occupancy_id);
      await refresh();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setCheckingOutId(null);
    }
  };

  const handleBan = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!banTarget) return;
    setBanning(true);
    setError(null);
    try {
      const result = await createBan({ customer_id: banTarget.customer_id, reason: banReason });
      setBanNotice(
        result.currently_inside
          ? `${banTarget.customer_name} was banned. Alert broadcast to venue staff — escort in progress.`
          : `${banTarget.customer_name} was banned.`
      );
      setBanTarget(null);
      setBanReason("");
      await refresh();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setBanning(false);
    }
  };

  if (loading) {
    return <div className="flex justify-center items-center h-64 text-muted-foreground">Loading occupancy...</div>;
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center gap-3 mb-8">
        <Users2 className="h-8 w-8 text-primary" />
        <h2 className="text-2xl font-bold text-foreground">Occupancy</h2>
      </div>

      {error && (
        <div className="glass-panel rounded-xl p-4 border border-destructive/30 text-destructive text-sm">{error}</div>
      )}
      {banNotice && (
        <div className="glass-panel rounded-xl p-4 border border-primary/30 text-primary text-sm">{banNotice}</div>
      )}

      {banTarget && (
        <form onSubmit={handleBan} className="glass-panel rounded-xl p-4 flex gap-3 items-end border border-destructive/30">
          <div className="flex-1">
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1 block">
              Reason for banning {banTarget.customer_name}
            </label>
            <input
              type="text"
              required
              autoFocus
              value={banReason}
              onChange={(e) => setBanReason(e.target.value)}
              className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm outline-none focus:border-destructive transition-all"
            />
          </div>
          <button
            type="button"
            onClick={() => { setBanTarget(null); setBanReason(""); }}
            className="text-xs font-bold px-3 py-2 rounded-lg border border-border text-muted-foreground hover:bg-muted/50 transition-colors"
          >
            Cancel
          </button>
          <button
            type="submit"
            disabled={banning}
            className="bg-destructive/10 hover:bg-destructive/20 text-destructive border border-destructive/30 font-bold py-2 px-4 rounded-lg transition-colors disabled:opacity-50"
          >
            {banning ? "Banning..." : "Confirm Ban & Alert"}
          </button>
        </form>
      )}

      {count && (
        <div className="glass-panel rounded-xl p-6 relative overflow-hidden group">
          <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
            <Users2 className="w-16 h-16" />
          </div>
          <p className="text-sm font-medium text-muted-foreground mb-1">Currently Inside</p>
          <p className={`text-4xl font-bold ${count.at_capacity ? "text-destructive" : "text-primary"}`}>
            {count.current_count}
            {count.max_capacity !== null && (
              <span className="text-lg text-muted-foreground font-medium"> / {count.max_capacity}</span>
            )}
          </p>
          {count.at_capacity && (
            <p className="text-xs font-bold text-destructive mt-2 uppercase tracking-wider">At Capacity</p>
          )}
          <p className="text-xs text-muted-foreground mt-2">Auto-checkout after {count.occupancy_auto_expire_hours}h</p>
        </div>
      )}

      <div className="glass-panel rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border/50 text-xs text-muted-foreground uppercase tracking-wider">
              <th className="text-left px-6 py-3 font-semibold">Name</th>
              <th className="text-left px-6 py-3 font-semibold">Time Inside</th>
              <th className="text-right px-6 py-3 font-semibold">Actions</th>
            </tr>
          </thead>
          <tbody>
            {occupants.map((o) => (
              <tr key={o.occupancy_id} className="border-b border-border/30 last:border-0">
                <td className="px-6 py-3 font-medium text-foreground">{o.customer_name}</td>
                <td className="px-6 py-3 text-muted-foreground">
                  <div>{o.minutes_inside !== null ? `${o.minutes_inside} min` : "—"}</div>
                  {o.auto_expire_at && (() => {
                    const remainingMs = new Date(o.auto_expire_at).getTime() - Date.now();
                    const overdue = remainingMs < 0;
                    const nearExpiry = !overdue && remainingMs <= 30 * 60 * 1000;
                    const remainingMin = Math.max(0, Math.floor(Math.abs(remainingMs) / 60000));
                    const label = overdue
                      ? "Auto-checkout overdue"
                      : `Auto-checkout in ${remainingMin >= 60 ? `${Math.floor(remainingMin / 60)}h ${remainingMin % 60}m` : `${remainingMin}m`}`;
                    return (
                      <div className={`text-[11px] font-semibold ${overdue || nearExpiry ? "text-destructive" : "text-muted-foreground/70"}`}>
                        {label}
                      </div>
                    );
                  })()}
                </td>
                <td className="px-6 py-3 text-right space-x-2 whitespace-nowrap">
                  <button
                    onClick={() => { setBanTarget(o); setBanNotice(null); }}
                    className="inline-flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-lg border transition-colors text-destructive border-destructive/30 hover:bg-destructive/10"
                  >
                    <Ban className="w-3.5 h-3.5" />
                    Ban & Alert
                  </button>
                  <button
                    onClick={() => handleCheckout(o)}
                    disabled={checkingOutId === o.occupancy_id}
                    className="inline-flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-lg border transition-colors text-primary border-primary/30 hover:bg-primary/10 disabled:opacity-50"
                  >
                    <LogOut className="w-3.5 h-3.5" />
                    {checkingOutId === o.occupancy_id ? "Checking out..." : "Check Out"}
                  </button>
                </td>
              </tr>
            ))}
            {occupants.length === 0 && (
              <tr>
                <td colSpan={3} className="px-6 py-12 text-center text-muted-foreground">No one is currently inside.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
