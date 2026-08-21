import React, { useState, useEffect } from "react";
import { Building2, PlusCircle, ShieldOff, Pencil } from "lucide-react";
import { listVenues, createVenue, updateVenue, deactivateVenue, getVenueConfig, updateVenueConfig, Venue } from "../lib/api";

export function VenuesAdmin() {
  const [venues, setVenues] = useState<Venue[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ name: "", address: "", max_capacity: "" });

  const [editingVenue, setEditingVenue] = useState<Venue | null>(null);
  const [editForm, setEditForm] = useState({ name: "", address: "", max_capacity: "", occupancy_auto_expire_hours: "" });
  const [editLoading, setEditLoading] = useState(false);
  const [savingEdit, setSavingEdit] = useState(false);

  const refresh = async () => {
    try {
      setVenues(await listVenues());
    } catch (err: any) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refresh();
  }, []);

  const handleCreate = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    setCreating(true);
    try {
      await createVenue({
        name: form.name,
        address: form.address,
        max_capacity: form.max_capacity ? parseInt(form.max_capacity, 10) : null,
      });
      setForm({ name: "", address: "", max_capacity: "" });
      await refresh();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setCreating(false);
    }
  };

  const handleDeactivate = async (venue: Venue) => {
    if (!confirm(`Deactivate "${venue.name}"? Staff and data are preserved, but it will be hidden from the active venue list.`)) {
      return;
    }
    setError(null);
    try {
      await deactivateVenue(venue.id);
      await refresh();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const openEdit = async (venue: Venue) => {
    setError(null);
    setEditingVenue(venue);
    setEditLoading(true);
    setEditForm({
      name: venue.name,
      address: venue.address,
      max_capacity: venue.max_capacity?.toString() ?? "",
      occupancy_auto_expire_hours: "",
    });
    try {
      const config = await getVenueConfig(venue.id);
      setEditForm((f) => ({ ...f, occupancy_auto_expire_hours: config.occupancy_auto_expire_hours?.toString() ?? "6" }));
    } catch (err: any) {
      setError(err.message);
    } finally {
      setEditLoading(false);
    }
  };

  const handleSaveEdit = async () => {
    if (!editingVenue) return;
    setError(null);
    setSavingEdit(true);
    try {
      await updateVenue(editingVenue.id, {
        name: editForm.name,
        address: editForm.address,
        max_capacity: editForm.max_capacity ? parseInt(editForm.max_capacity, 10) : null,
      });
    } catch (err: any) {
      setError(`Failed to save venue details: ${err.message}`);
      setSavingEdit(false);
      return;
    }
    try {
      const hours = parseInt(editForm.occupancy_auto_expire_hours, 10);
      if (!Number.isNaN(hours) && hours > 0) {
        await updateVenueConfig(editingVenue.id, { occupancy_auto_expire_hours: hours });
      }
    } catch (err: any) {
      setError(`Venue details saved, but the auto-expire setting failed to save: ${err.message}`);
      setSavingEdit(false);
      setEditingVenue(null);
      await refresh();
      return;
    }
    setEditingVenue(null);
    setSavingEdit(false);
    await refresh();
  };

  if (loading) {
    return <div className="flex justify-center items-center h-64 text-muted-foreground">Loading venues...</div>;
  }

  return (
    <div className="space-y-6 max-w-5xl mx-auto">
      <div className="flex items-center gap-3 mb-8">
        <Building2 className="h-8 w-8 text-primary" />
        <h2 className="text-2xl font-bold text-foreground">Venues</h2>
      </div>

      {error && (
        <div className="glass-panel rounded-xl p-4 border border-destructive/30 text-destructive text-sm">{error}</div>
      )}

      <form onSubmit={handleCreate} className="glass-panel rounded-xl p-6 grid grid-cols-1 md:grid-cols-4 gap-4 items-end">
        <div>
          <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1 block">Name</label>
          <input
            type="text"
            required
            value={form.name}
            onChange={(e) => setForm({ ...form, name: e.target.value })}
            className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm outline-none focus:border-primary transition-all"
          />
        </div>
        <div>
          <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1 block">Address</label>
          <input
            type="text"
            required
            value={form.address}
            onChange={(e) => setForm({ ...form, address: e.target.value })}
            className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm outline-none focus:border-primary transition-all"
          />
        </div>
        <div>
          <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1 block">Max Capacity</label>
          <input
            type="number"
            min={1}
            placeholder="Uncapped"
            value={form.max_capacity}
            onChange={(e) => setForm({ ...form, max_capacity: e.target.value })}
            className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm outline-none focus:border-primary transition-all"
          />
        </div>
        <button
          type="submit"
          disabled={creating}
          className="bg-primary/10 hover:bg-primary/20 text-primary border border-primary/30 font-bold py-2 px-4 rounded-lg transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
        >
          <PlusCircle className="w-4 h-4" />
          {creating ? "Creating..." : "Create Venue"}
        </button>
      </form>

      <div className="glass-panel rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border/50 text-xs text-muted-foreground uppercase tracking-wider">
              <th className="text-left px-6 py-3 font-semibold">Name</th>
              <th className="text-left px-6 py-3 font-semibold">Address</th>
              <th className="text-left px-6 py-3 font-semibold">Capacity</th>
              <th className="text-left px-6 py-3 font-semibold">Status</th>
              <th className="text-right px-6 py-3 font-semibold">Actions</th>
            </tr>
          </thead>
          <tbody>
            {venues.map((v) => (
              <tr key={v.id} className="border-b border-border/30 last:border-0">
                <td className="px-6 py-3 font-medium text-foreground">{v.name}</td>
                <td className="px-6 py-3 text-muted-foreground">{v.address}</td>
                <td className="px-6 py-3 text-muted-foreground">{v.max_capacity ?? "Uncapped"}</td>
                <td className="px-6 py-3">
                  <span className={`text-xs font-bold ${v.is_active ? "text-primary" : "text-muted-foreground"}`}>
                    {v.is_active ? "ACTIVE" : "DEACTIVATED"}
                  </span>
                </td>
                <td className="px-6 py-3 text-right space-x-2 whitespace-nowrap">
                  <button
                    onClick={() => openEdit(v)}
                    className="inline-flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-lg border border-border text-foreground hover:bg-muted/50 transition-colors"
                  >
                    <Pencil className="w-3.5 h-3.5" />
                    Edit
                  </button>
                  {v.is_active && (
                    <button
                      onClick={() => handleDeactivate(v)}
                      className="inline-flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-lg border transition-colors text-destructive border-destructive/30 hover:bg-destructive/10"
                    >
                      <ShieldOff className="w-3.5 h-3.5" />
                      Deactivate
                    </button>
                  )}
                </td>
              </tr>
            ))}
            {venues.length === 0 && (
              <tr>
                <td colSpan={5} className="px-6 py-12 text-center text-muted-foreground">No venues found.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {editingVenue && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setEditingVenue(null)}>
          <div className="glass-panel rounded-xl p-6 w-full max-w-md space-y-4 bg-background" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-bold text-foreground">Edit {editingVenue.name}</h3>
            <div>
              <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1 block">Name</label>
              <input
                type="text"
                value={editForm.name}
                onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm outline-none focus:border-primary transition-all"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1 block">Address</label>
              <input
                type="text"
                value={editForm.address}
                onChange={(e) => setEditForm({ ...editForm, address: e.target.value })}
                className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm outline-none focus:border-primary transition-all"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1 block">Max Capacity</label>
              <input
                type="number"
                min={1}
                placeholder="Uncapped"
                value={editForm.max_capacity}
                onChange={(e) => setEditForm({ ...editForm, max_capacity: e.target.value })}
                className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm outline-none focus:border-primary transition-all"
              />
            </div>
            <div>
              <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1 block">Auto-checkout after (hours)</label>
              <input
                type="number"
                min={1}
                disabled={editLoading}
                value={editForm.occupancy_auto_expire_hours}
                onChange={(e) => setEditForm({ ...editForm, occupancy_auto_expire_hours: e.target.value })}
                className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm outline-none focus:border-primary transition-all disabled:opacity-50"
              />
              <p className="text-xs text-muted-foreground mt-1">
                Guests still checked in after this many hours are automatically checked out.
              </p>
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setEditingVenue(null)}
                className="px-4 py-2 text-sm rounded-lg border border-border text-foreground hover:bg-muted/50 transition-colors"
              >
                Cancel
              </button>
              <button
                disabled={savingEdit || editLoading}
                onClick={handleSaveEdit}
                className="px-4 py-2 text-sm rounded-lg bg-primary/10 text-primary border border-primary/30 font-bold hover:bg-primary/20 transition-colors disabled:opacity-50"
              >
                {savingEdit ? "Saving..." : "Save"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
