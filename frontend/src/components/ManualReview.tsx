"use client";

import React, { useState } from "react";
import { AlertTriangle, CheckCircle, XCircle, ShieldAlert, ArrowRight } from "lucide-react";

interface ManualReviewProps {
  scanResult: any;
  onDecision: (decision: 'PASS' | 'DENY') => void;
}

const CHECKLIST_ITEMS = [
  { id: 'ear', label: 'Ear Shape', description: 'Match the ears in photo to the visitor' },
  { id: 'hair', label: 'Hair Line', description: 'Check the natural hairline and parting' },
  { id: 'eyes', label: 'Eye Position', description: 'Check distance between eyes and height' },
  { id: 'nose', label: 'Nose Shape', description: 'Check bridge width and tip shape' },
  { id: 'mouth', label: 'Mouth / Jaw', description: 'Check lip thickness and jawline' },
  { id: 'age', label: 'Apparent Age', description: 'Does the visitor look the calculated age?' },
  { id: 'general', label: 'General Appearance', description: 'Overall match of the person' },
  { id: 'security', label: 'Document Security', description: 'Check holograms and physical material' }
];

export function ManualReview({ scanResult, onDecision }: ManualReviewProps) {
  const [checkedItems, setCheckedItems] = useState<Record<string, boolean>>({});

  const handleCheck = (id: string) => {
    setCheckedItems(prev => ({ ...prev, [id]: !prev[id] }));
  };

  const allChecked = CHECKLIST_ITEMS.every(item => checkedItems[item.id]);

  return (
    <div className="animate-in fade-in slide-in-from-bottom-4 duration-500 max-w-2xl mx-auto space-y-6">
      <div className="glass-panel border-yellow-500/30 rounded-2xl overflow-hidden">
        <div className="bg-yellow-500/10 p-6 flex items-start gap-4 border-b border-border/50">
          <div className="p-3 bg-yellow-500/20 rounded-full shrink-0">
            <ShieldAlert className="w-8 h-8 text-yellow-500" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-yellow-500 mb-1">Manual Verification Required</h2>
            <p className="text-sm text-muted-foreground">
              The AI has flagged this scan for manual review. Please verify the following physical traits before making a final decision.
            </p>
          </div>
        </div>

        <div className="p-6">
          <h3 className="font-semibold mb-4 text-lg">Things to Check</h3>
          <div className="space-y-3">
            {CHECKLIST_ITEMS.map((item) => (
              <label 
                key={item.id} 
                className={`flex items-start gap-4 p-4 rounded-xl cursor-pointer transition-colors border ${
                  checkedItems[item.id] ? 'bg-primary/5 border-primary/30' : 'bg-card/50 border-border/50 hover:bg-card'
                }`}
              >
                <div className="pt-1">
                  <div className={`w-6 h-6 rounded-md flex items-center justify-center border transition-colors ${
                    checkedItems[item.id] ? 'bg-primary border-primary text-primary-foreground' : 'border-input bg-transparent'
                  }`}>
                    {checkedItems[item.id] && <CheckCircle className="w-4 h-4" />}
                  </div>
                  {/* Invisible checkbox for accessibility */}
                  <input 
                    type="checkbox" 
                    className="sr-only" 
                    checked={!!checkedItems[item.id]} 
                    onChange={() => handleCheck(item.id)} 
                  />
                </div>
                <div>
                  <div className={`font-medium ${checkedItems[item.id] ? 'text-primary' : ''}`}>
                    {item.label}
                  </div>
                  <div className="text-sm text-muted-foreground">
                    {item.description}
                  </div>
                </div>
              </label>
            ))}
          </div>

          <div className="mt-8 flex gap-4">
            <button
              onClick={() => onDecision('DENY')}
              className="flex-1 py-4 rounded-xl font-bold text-lg flex items-center justify-center gap-2 bg-destructive/10 text-destructive hover:bg-destructive/20 border border-destructive/20 transition-all"
            >
              <XCircle className="w-5 h-5" />
              Deny Entry
            </button>
            <button
              onClick={() => onDecision('PASS')}
              disabled={!allChecked}
              className={`flex-1 py-4 rounded-xl font-bold text-lg flex items-center justify-center gap-2 transition-all ${
                allChecked 
                  ? 'bg-primary text-primary-foreground hover:brightness-110 shadow-[0_0_20px_rgba(var(--primary),0.3)]' 
                  : 'bg-muted text-muted-foreground cursor-not-allowed opacity-50'
              }`}
            >
              <CheckCircle className="w-5 h-5" />
              Pass Entry
            </button>
          </div>
          {!allChecked && (
            <p className="text-center text-xs text-muted-foreground mt-4 flex items-center justify-center gap-1">
              <ArrowRight className="w-3 h-3" />
              Complete checklist to enable Pass Entry
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
