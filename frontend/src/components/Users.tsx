import React, { useState, useEffect } from "react";
import { UserPlus, Users as UsersIcon, ShieldCheck, ShieldOff, Pencil, KeyRound } from "lucide-react";
import { listUsers, createUser, updateUser, resetUserPassword, listVenues, getSession, AdminUser, Venue } from "../lib/api";

const ROLES = ["door_staff", "manager", "venue_admin", "super_admin", "viewer"];

export function UsersAdmin() {
  const session = getSession();
  const isSuperAdmin = session.role === "super_admin";

  const [users, setUsers] = useState<AdminUser[]>([]);
  const [venues, setVenues] = useState<Venue[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ email: "", password: "", role: "door_staff", venue_id: "" as string | number });

  const [editingUser, setEditingUser] = useState<AdminUser | null>(null);
  const [editForm, setEditForm] = useState({ role: "", venue_id: "" as string | number });
  const [savingEdit, setSavingEdit] = useState(false);

  const [resettingPasswordFor, setResettingPasswordFor] = useState<AdminUser | null>(null);
  const [newPassword, setNewPassword] = useState("");
  const [resettingSaving, setResettingSaving] = useState(false);

  const venueName = (id: number | null) => {
    if (id === null) return "—";
    return venues.find((v) => v.id === id)?.name ?? `Venue #${id}`;
  };

  const refresh = async () => {
    try {
      const [u, v] = await Promise.all([listUsers(), listVenues()]);
      setUsers(u);
      setVenues(v);
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
      await createUser({
        email: form.email,
        password: form.password,
        role: form.role,
        venue_id: form.venue_id !== "" ? Number(form.venue_id) : undefined,
      });
      setForm({ email: "", password: "", role: "door_staff", venue_id: "" });
      await refresh();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setCreating(false);
    }
  };

  const toggleActive = async (user: AdminUser) => {
    setError(null);
    try {
      await updateUser(user.id, { is_active: !user.is_active });
      await refresh();
    } catch (err: any) {
      setError(err.message);
    }
  };

  const openEdit = (user: AdminUser) => {
    setEditingUser(user);
    setEditForm({ role: user.role, venue_id: user.venue_id ?? "" });
  };

  const handleSaveEdit = async () => {
    if (!editingUser) return;
    setError(null);
    setSavingEdit(true);
    try {
      const payload: { role?: string; venue_id?: number } = { role: editForm.role };
      if (isSuperAdmin && editForm.venue_id !== "" && Number(editForm.venue_id) !== editingUser.venue_id) {
        payload.venue_id = Number(editForm.venue_id);
      }
      await updateUser(editingUser.id, payload);
      setEditingUser(null);
      await refresh();
    } catch (err: any) {
      setError(err.message);
    } finally {
      setSavingEdit(false);
    }
  };

  const handleResetPassword = async () => {
    if (!resettingPasswordFor) return;
    setError(null);
    setResettingSaving(true);
    try {
      await resetUserPassword(resettingPasswordFor.id, newPassword);
      setResettingPasswordFor(null);
      setNewPassword("");
    } catch (err: any) {
      setError(err.message);
    } finally {
      setResettingSaving(false);
    }
  };

  if (loading) {
    return <div className="flex justify-center items-center h-64 text-muted-foreground">Loading users...</div>;
  }

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      <div className="flex items-center gap-3 mb-8">
        <UsersIcon className="h-8 w-8 text-primary" />
        <h2 className="text-2xl font-bold text-foreground">Staff Accounts</h2>
      </div>

      {error && (
        <div className="glass-panel rounded-xl p-4 border border-destructive/30 text-destructive text-sm">{error}</div>
      )}

      <form onSubmit={handleCreate} className="glass-panel rounded-xl p-6 grid grid-cols-1 md:grid-cols-5 gap-4 items-end">
        <div>
          <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1 block">Email</label>
          <input
            type="email"
            required
            value={form.email}
            onChange={(e) => setForm({ ...form, email: e.target.value })}
            className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm outline-none focus:border-primary transition-all"
          />
        </div>
        <div>
          <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1 block">Password</label>
          <input
            type="password"
            required
            minLength={8}
            value={form.password}
            onChange={(e) => setForm({ ...form, password: e.target.value })}
            className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm outline-none focus:border-primary transition-all"
          />
        </div>
        <div>
          <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1 block">Role</label>
          <select
            value={form.role}
            onChange={(e) => setForm({ ...form, role: e.target.value })}
            className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm outline-none focus:border-primary transition-all"
          >
            {ROLES.map((r) => (
              <option key={r} value={r}>{r.replace(/_/g, " ")}</option>
            ))}
          </select>
        </div>
        {isSuperAdmin && (
          <div>
            <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1 block">Venue</label>
            <select
              value={form.venue_id}
              onChange={(e) => setForm({ ...form, venue_id: e.target.value })}
              className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm outline-none focus:border-primary transition-all"
            >
              <option value="">My venue</option>
              {venues.map((v) => (
                <option key={v.id} value={v.id}>{v.name}</option>
              ))}
            </select>
          </div>
        )}
        <button
          type="submit"
          disabled={creating}
          className="bg-primary/10 hover:bg-primary/20 text-primary border border-primary/30 font-bold py-2 px-4 rounded-lg transition-colors flex items-center justify-center gap-2 disabled:opacity-50"
        >
          <UserPlus className="w-4 h-4" />
          {creating ? "Creating..." : "Create User"}
        </button>
      </form>

      <div className="glass-panel rounded-xl overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border/50 text-xs text-muted-foreground uppercase tracking-wider">
              <th className="text-left px-6 py-3 font-semibold">Email</th>
              <th className="text-left px-6 py-3 font-semibold">Role</th>
              <th className="text-left px-6 py-3 font-semibold">Venue</th>
              <th className="text-left px-6 py-3 font-semibold">Status</th>
              <th className="text-right px-6 py-3 font-semibold">Actions</th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.id} className="border-b border-border/30 last:border-0">
                <td className="px-6 py-3 font-medium text-foreground">{u.email}</td>
                <td className="px-6 py-3 text-muted-foreground capitalize">{u.role.replace(/_/g, " ")}</td>
                <td className="px-6 py-3 text-muted-foreground">{venueName(u.venue_id)}</td>
                <td className="px-6 py-3">
                  <span className={`text-xs font-bold ${u.is_active ? "text-primary" : "text-muted-foreground"}`}>
                    {u.is_active ? "ACTIVE" : "DEACTIVATED"}
                  </span>
                </td>
                <td className="px-6 py-3 text-right space-x-2 whitespace-nowrap">
                  <button
                    onClick={() => openEdit(u)}
                    className="inline-flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-lg border border-border text-foreground hover:bg-muted/50 transition-colors"
                  >
                    <Pencil className="w-3.5 h-3.5" />
                    Edit
                  </button>
                  <button
                    onClick={() => { setResettingPasswordFor(u); setNewPassword(""); }}
                    className="inline-flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-lg border border-border text-foreground hover:bg-muted/50 transition-colors"
                  >
                    <KeyRound className="w-3.5 h-3.5" />
                    Reset Password
                  </button>
                  <button
                    onClick={() => toggleActive(u)}
                    className={`inline-flex items-center gap-1.5 text-xs font-bold px-3 py-1.5 rounded-lg border transition-colors ${
                      u.is_active
                        ? "text-destructive border-destructive/30 hover:bg-destructive/10"
                        : "text-primary border-primary/30 hover:bg-primary/10"
                    }`}
                  >
                    {u.is_active ? <ShieldOff className="w-3.5 h-3.5" /> : <ShieldCheck className="w-3.5 h-3.5" />}
                    {u.is_active ? "Deactivate" : "Reactivate"}
                  </button>
                </td>
              </tr>
            ))}
            {users.length === 0 && (
              <tr>
                <td colSpan={5} className="px-6 py-12 text-center text-muted-foreground">No staff accounts found.</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {editingUser && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setEditingUser(null)}>
          <div className="glass-panel rounded-xl p-6 w-full max-w-md space-y-4 bg-background" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-bold text-foreground">Edit {editingUser.email}</h3>
            <div>
              <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1 block">Role</label>
              <select
                value={editForm.role}
                onChange={(e) => setEditForm({ ...editForm, role: e.target.value })}
                className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm outline-none focus:border-primary transition-all"
              >
                {ROLES.map((r) => (
                  <option key={r} value={r}>{r.replace(/_/g, " ")}</option>
                ))}
              </select>
            </div>
            {isSuperAdmin && (
              <div>
                <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1 block">Venue</label>
                <select
                  value={editForm.venue_id}
                  onChange={(e) => setEditForm({ ...editForm, venue_id: e.target.value })}
                  className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm outline-none focus:border-primary transition-all"
                >
                  {venues.map((v) => (
                    <option key={v.id} value={v.id}>{v.name}</option>
                  ))}
                </select>
              </div>
            )}
            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setEditingUser(null)}
                className="px-4 py-2 text-sm rounded-lg border border-border text-foreground hover:bg-muted/50 transition-colors"
              >
                Cancel
              </button>
              <button
                disabled={savingEdit}
                onClick={handleSaveEdit}
                className="px-4 py-2 text-sm rounded-lg bg-primary/10 text-primary border border-primary/30 font-bold hover:bg-primary/20 transition-colors disabled:opacity-50"
              >
                {savingEdit ? "Saving..." : "Save"}
              </button>
            </div>
          </div>
        </div>
      )}

      {resettingPasswordFor && (
        <div className="fixed inset-0 bg-black/60 flex items-center justify-center z-50" onClick={() => setResettingPasswordFor(null)}>
          <div className="glass-panel rounded-xl p-6 w-full max-w-md space-y-4 bg-background" onClick={(e) => e.stopPropagation()}>
            <h3 className="text-lg font-bold text-foreground">Reset password for {resettingPasswordFor.email}</h3>
            <div>
              <label className="text-xs font-semibold text-muted-foreground uppercase tracking-wider mb-1 block">New Password</label>
              <input
                type="password"
                required
                minLength={8}
                autoFocus
                value={newPassword}
                onChange={(e) => setNewPassword(e.target.value)}
                className="w-full bg-background border border-border rounded-lg px-3 py-2 text-sm outline-none focus:border-primary transition-all"
              />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <button
                onClick={() => setResettingPasswordFor(null)}
                className="px-4 py-2 text-sm rounded-lg border border-border text-foreground hover:bg-muted/50 transition-colors"
              >
                Cancel
              </button>
              <button
                disabled={resettingSaving || newPassword.length < 8}
                onClick={handleResetPassword}
                className="px-4 py-2 text-sm rounded-lg bg-destructive/10 text-destructive border border-destructive/30 font-bold hover:bg-destructive/20 transition-colors disabled:opacity-50"
              >
                {resettingSaving ? "Resetting..." : "Reset Password"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
