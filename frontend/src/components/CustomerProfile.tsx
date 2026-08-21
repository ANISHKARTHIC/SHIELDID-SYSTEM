"use client";

import React, { useState } from "react";
import { CustomerProfile as CustomerProfileType } from "../lib/store";
import { User, Shield, AlertTriangle, ShieldCheck, ChevronRight, Clock, Star, Users, Ban, ShieldOff } from "lucide-react";
import { createBan, removeBan, getSession } from "../lib/api";

interface CustomerProfileProps {
  customer: CustomerProfileType;
  onBack: () => void;
}

// Mirrors the backend's require_supervisor gate on DELETE /blacklist/{id} —
// door_staff can create a ban but not lift one. Checked client-side purely
// to hide a button that would otherwise 403; the backend is still the real
// enforcement point.
const CAN_UNBAN_ROLES = new Set(["manager", "venue_admin", "super_admin"]);

export function CustomerProfile({ customer, onBack }: CustomerProfileProps) {
  const [showBanForm, setShowBanForm] = useState(false);
  const [banReason, setBanReason] = useState("");
  const [banning, setBanning] = useState(false);
  const [banError, setBanError] = useState<string | null>(null);
  const [banResult, setBanResult] = useState<string | null>(null);
  const [unbanning, setUnbanning] = useState(false);

  const canUnban = CAN_UNBAN_ROLES.has(getSession().role || "");

  const handleBan = async (e: React.FormEvent) => {
    e.preventDefault();
    setBanning(true);
    setBanError(null);
    try {
      const result = await createBan({ customer_id: parseInt(customer.id, 10), reason: banReason });
      setBanResult(
        result.currently_inside
          ? "Ban created. Alert broadcast — this person is currently inside."
          : "Ban created."
      );
      setShowBanForm(false);
      setBanReason("");
    } catch (err: any) {
      setBanError(err.message);
    } finally {
      setBanning(false);
    }
  };

  const handleUnban = async () => {
    if (!window.confirm(`Lift the ban on ${customer.name}? Their photos will return to routine retention.`)) {
      return;
    }
    setUnbanning(true);
    setBanError(null);
    try {
      await removeBan(parseInt(customer.id, 10));
      setBanResult("Ban removed.");
    } catch (err: any) {
      setBanError(err.message);
    } finally {
      setUnbanning(false);
    }
  };

  return (
    <div className="space-y-6 animate-in fade-in slide-in-from-right-8 duration-500">
      <div className="flex items-center justify-between">
        <button
          onClick={onBack}
          className="text-sm text-muted-foreground hover:text-foreground flex items-center transition-colors"
        >
          <ChevronRight className="w-4 h-4 rotate-180 mr-1" />
          Back to Directory
        </button>
        {customer.blacklistStatus === 'none' && (
          <button
            onClick={() => setShowBanForm(!showBanForm)}
            className="inline-flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-lg border transition-colors text-destructive border-destructive/30 hover:bg-destructive/10"
          >
            <Ban className="w-3.5 h-3.5" />
            Ban Customer
          </button>
        )}
        {customer.blacklistStatus !== 'none' && canUnban && (
          <button
            onClick={handleUnban}
            disabled={unbanning}
            className="inline-flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-lg border transition-colors text-green-500 border-green-500/30 hover:bg-green-500/10 disabled:opacity-50"
          >
            <ShieldOff className="w-3.5 h-3.5" />
            {unbanning ? "Removing Ban..." : "Remove Ban"}
          </button>
        )}
      </div>

      {banResult && (
        <div className="glass-panel rounded-xl p-4 border border-primary/30 text-primary text-sm">{banResult}</div>
      )}
      {banError && (
        <div className="glass-panel rounded-xl p-4 border border-destructive/30 text-destructive text-sm">{banError}</div>
      )}

      {showBanForm && (
        <form onSubmit={handleBan} className="glass-panel rounded-xl p-4 flex gap-3 items-end">
          <div className="flex-1">
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1 block">Reason</label>
            <input
              type="text"
              required
              value={banReason}
              onChange={(e) => setBanReason(e.target.value)}
              className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm outline-none focus:border-destructive transition-all"
            />
          </div>
          <button
            type="submit"
            disabled={banning}
            className="bg-destructive/10 hover:bg-destructive/20 text-destructive border border-destructive/30 font-bold py-2 px-4 rounded-lg transition-colors disabled:opacity-50"
          >
            {banning ? "Banning..." : "Confirm Ban"}
          </button>
        </form>
      )}

      <div className="flex flex-col md:flex-row gap-6">
        <div className="w-full md:w-1/3 space-y-6">
          <div className="glass-panel rounded-2xl p-6 text-center">
            <div className="relative inline-block mb-4">
              <div className="w-32 h-32 rounded-full overflow-hidden border-4 border-background shadow-xl mx-auto bg-muted">
                {customer.photoUrl ? (
                  <img src={customer.photoUrl} alt={customer.name} className="w-full h-full object-cover" />
                ) : (
                  <User className="w-full h-full p-6 text-muted-foreground" />
                )}
              </div>
              <div className={`absolute bottom-2 right-2 w-5 h-5 rounded-full border-2 border-background ${
                customer.blacklistStatus === 'permanent' ? 'bg-destructive' :
                customer.blacklistStatus === 'temporary' ? 'bg-yellow-500' :
                'bg-green-500'
              }`} />
            </div>
            
            <h2 className="text-2xl font-bold">{customer.name}</h2>
            <p className="text-muted-foreground">Age: {customer.age} • {customer.nationality}</p>
            
            <div className="flex justify-center gap-2 mt-4">
              {customer.vipTier && customer.vipTier !== 'none' && (
                <span className="px-3 py-1 bg-yellow-500/20 text-yellow-500 rounded-full text-xs font-semibold flex items-center gap-1">
                  <Star className="w-3 h-3" />
                  VIP: {customer.vipTier}
                </span>
              )}
              {customer.warnings && customer.warnings > 0 ? (
                <span className="px-3 py-1 bg-yellow-500/20 text-yellow-500 rounded-full text-xs font-semibold flex items-center gap-1">
                  <AlertTriangle className="w-3 h-3" />
                  {customer.warnings} Warnings
                </span>
              ) : null}
            </div>
          </div>
          
          <div className="glass-panel rounded-2xl p-6">
            <h3 className="font-semibold text-lg mb-4 flex items-center gap-2">
              <ShieldCheck className="w-5 h-5 text-primary" />
              ID Document
            </h3>
            
            {customer.idScanUrl && (
              <div className="mb-6 rounded-lg overflow-hidden border border-border/50">
                <img src={customer.idScanUrl} alt="Scanned ID" className="w-full h-auto object-cover" />
              </div>
            )}
            
            <div className="space-y-3 text-sm">
              <div className="flex justify-between border-b border-border/50 pb-2">
                <span className="text-muted-foreground">Type</span>
                <span className="capitalize font-medium">{customer.documentType.replace('_', ' ')}</span>
              </div>
              <div className="flex justify-between border-b border-border/50 pb-2">
                <span className="text-muted-foreground">Number</span>
                <span className="font-mono">{customer.documentNumber}</span>
              </div>
              <div className="flex justify-between border-b border-border/50 pb-2">
                <span className="text-muted-foreground">Expires</span>
                <span className="font-medium">{customer.expiryDate}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="w-full md:w-2/3 space-y-6">
          <div className="grid grid-cols-2 gap-4">
            <div className="glass-panel rounded-2xl p-5 flex items-center gap-4">
              <div className="p-3 bg-primary/20 text-primary rounded-xl">
                <Users className="w-6 h-6" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Total Visits</p>
                <p className="text-2xl font-bold">{customer.visitCount}</p>
              </div>
            </div>
            <div className="glass-panel rounded-2xl p-5 flex items-center gap-4">
              <div className="p-3 bg-destructive/20 text-destructive rounded-xl">
                <AlertTriangle className="w-6 h-6" />
              </div>
              <div>
                <p className="text-sm text-muted-foreground">Incidents</p>
                <p className="text-2xl font-bold">{customer.incidentsCount}</p>
              </div>
            </div>
          </div>

          <div className="glass-panel rounded-2xl p-6">
            <h3 className="font-semibold text-lg mb-4">Manager Notes</h3>
            <div className="p-4 bg-card/50 rounded-xl border border-border/50 min-h-[100px]">
              {customer.managerNotes ? (
                <p className="text-sm leading-relaxed">{customer.managerNotes}</p>
              ) : (
                <p className="text-sm text-muted-foreground italic">No manager notes available.</p>
              )}
            </div>
          </div>
          
          <div className="glass-panel rounded-2xl p-6">
            <h3 className="font-semibold text-lg mb-4 flex items-center gap-2">
              <Clock className="w-5 h-5 text-primary" />
              Timeline
            </h3>
            <div className="space-y-4 relative before:absolute before:inset-0 before:ml-5 before:-translate-x-px md:before:mx-auto md:before:translate-x-0 before:h-full before:w-0.5 before:bg-gradient-to-b before:from-transparent before:via-border before:to-transparent">
              <div className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                <div className="flex items-center justify-center w-10 h-10 rounded-full border-4 border-background bg-primary shadow shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10">
                  <ShieldCheck className="w-4 h-4 text-primary-foreground" />
                </div>
                <div className="w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] glass-panel p-4 rounded-xl border border-border/50">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold">Verified Access</span>
                    <span className="text-xs text-muted-foreground">Today, 10:42 PM</span>
                  </div>
                  <p className="text-sm text-muted-foreground">ID scanned successfully. Authenticity 98%.</p>
                </div>
              </div>
              <div className="relative flex items-center justify-between md:justify-normal md:odd:flex-row-reverse group is-active">
                <div className="flex items-center justify-center w-10 h-10 rounded-full border-4 border-background bg-card border-border shadow shrink-0 md:order-1 md:group-odd:-translate-x-1/2 md:group-even:translate-x-1/2 z-10">
                  <User className="w-4 h-4 text-muted-foreground" />
                </div>
                <div className="w-[calc(100%-4rem)] md:w-[calc(50%-2.5rem)] glass-panel p-4 rounded-xl border border-border/50">
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold">Profile Created</span>
                    <span className="text-xs text-muted-foreground">14 days ago</span>
                  </div>
                  <p className="text-sm text-muted-foreground">First visit recorded in the system.</p>
                </div>
              </div>
            </div>
          </div>

        </div>
      </div>
    </div>
  );
}
