const TOKEN_KEY = "vips_auth_token";
const EMAIL_KEY = "vips_auth_email";
const ROLE_KEY = "vips_auth_role";

export function getApiBase(): string {
  // Baked in at build time — set NEXT_PUBLIC_API_URL and rebuild to point
  // this at a real deployed backend (e.g. https://venuepass-api.duckdns.org/api/v1).
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL;
  }
  if (typeof window === "undefined") return "";
  // Fallback for local dev when NEXT_PUBLIC_API_URL isn't set: assume the
  // backend is on the same host, default port.
  return `http://${window.location.hostname}:8000/api/v1`;
}

export function getToken(): string | null {
  if (typeof window === "undefined") return null;
  return window.localStorage.getItem(TOKEN_KEY);
}

export function getSession(): { email: string | null; role: string | null } {
  if (typeof window === "undefined") return { email: null, role: null };
  return {
    email: window.localStorage.getItem(EMAIL_KEY),
    role: window.localStorage.getItem(ROLE_KEY),
  };
}

export function saveSession(token: string, email: string, role: string) {
  window.localStorage.setItem(TOKEN_KEY, token);
  window.localStorage.setItem(EMAIL_KEY, email);
  window.localStorage.setItem(ROLE_KEY, role);
}

export function clearSession() {
  window.localStorage.removeItem(TOKEN_KEY);
  window.localStorage.removeItem(EMAIL_KEY);
  window.localStorage.removeItem(ROLE_KEY);
}

let onUnauthorized: (() => void) | null = null;
export function setOnUnauthorized(handler: () => void) {
  onUnauthorized = handler;
}

/** Fetch wrapper that attaches the bearer token and redirects to login on 401. */
export async function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const token = getToken();
  const headers = new Headers(init.headers);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${getApiBase()}${path}`, { ...init, headers });

  if (response.status === 401) {
    clearSession();
    onUnauthorized?.();
  } else if (response.status === 400) {
    // A deactivated account fails every authenticated call with 400
    // "Inactive user" (not 401, since the token itself is still valid) —
    // without this check, a user deactivated mid-session never gets
    // ejected and just sees raw error strings on an otherwise broken screen.
    const clone = response.clone();
    try {
      const data = await clone.json();
      if (data?.detail === "Inactive user") {
        clearSession();
        onUnauthorized?.();
      }
    } catch {
      // Non-JSON 400 body — not the inactive-user case, ignore.
    }
  }

  return response;
}

export async function login(email: string, password: string) {
  const response = await fetch(`${getApiBase()}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username: email, password }),
  });

  if (!response.ok) {
    if (response.status === 401) {
      throw new Error("Incorrect email or password.");
    }
    throw new Error("Sign in failed. Please try again.");
  }

  const data = await response.json();
  saveSession(data.token, data.email, data.role);
  return data;
}

export interface AdminUser {
  id: number;
  email: string;
  role: string;
  venue_id: number | null;
  is_active: boolean;
  created_at: string | null;
}

export async function listUsers(): Promise<AdminUser[]> {
  const response = await apiFetch("/users");
  if (!response.ok) throw new Error("Failed to load users.");
  return response.json();
}

export async function createUser(input: { email: string; password: string; role: string; venue_id?: number | null }): Promise<AdminUser> {
  const response = await apiFetch("/users", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "Failed to create user.");
  }
  return response.json();
}

export async function updateUser(id: number, input: { role?: string; is_active?: boolean; venue_id?: number }): Promise<AdminUser> {
  const response = await apiFetch(`/users/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "Failed to update user.");
  }
  return response.json();
}

export async function resetUserPassword(id: number, newPassword: string): Promise<{ success: boolean }> {
  const response = await apiFetch(`/users/${id}/reset-password`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ new_password: newPassword }),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "Failed to reset password.");
  }
  return response.json();
}

export interface RetentionLog {
  id: number;
  timestamp: string;
  details: {
    trigger: string;
    anonymized_count: number;
    skipped_blacklisted_count: number;
    customer_ids: number[];
    error?: string;
  };
}

export async function runRetentionNow(): Promise<{ success: boolean } & RetentionLog["details"]> {
  const response = await apiFetch("/admin/retention/run", { method: "POST" });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "Failed to trigger retention job.");
  }
  return response.json();
}

export async function getRetentionLogs(): Promise<RetentionLog[]> {
  const response = await apiFetch("/admin/retention/logs");
  if (!response.ok) throw new Error("Failed to load retention logs.");
  return response.json();
}

export interface Venue {
  id: number;
  name: string;
  address: string;
  is_active: boolean;
  max_capacity: number | null;
  created_at: string;
}

export async function listVenues(includeInactive = false): Promise<Venue[]> {
  const response = await apiFetch(`/venues${includeInactive ? "?include_inactive=true" : ""}`);
  if (!response.ok) throw new Error("Failed to load venues.");
  return response.json();
}

export async function createVenue(input: { name: string; address: string; max_capacity?: number | null }): Promise<Venue> {
  const response = await apiFetch("/venues", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "Failed to create venue.");
  }
  return response.json();
}

export async function updateVenue(id: number, input: { name?: string; address?: string; max_capacity?: number | null }): Promise<Venue> {
  const response = await apiFetch(`/venues/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "Failed to update venue.");
  }
  return response.json();
}

export interface VenueConfig {
  allowed_documents: string[];
  retention_days_success: number;
  retention_days_manual: number;
  retention_days_incident: number;
  verification_mode: string;
  theme_config: unknown;
  occupancy_auto_expire_hours: number;
}

export async function getVenueConfig(id: number): Promise<VenueConfig> {
  const response = await apiFetch(`/venues/${id}/config`);
  if (!response.ok) throw new Error("Failed to load venue configuration.");
  return response.json();
}

export async function updateVenueConfig(id: number, updates: Partial<VenueConfig>): Promise<void> {
  const response = await apiFetch(`/venues/${id}/config`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updates),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "Failed to update venue configuration.");
  }
}

export async function deactivateVenue(id: number): Promise<Venue> {
  const response = await apiFetch(`/venues/${id}`, { method: "DELETE" });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "Failed to deactivate venue.");
  }
  return response.json();
}

export interface Occupant {
  occupancy_id: number;
  customer_id: number;
  customer_name: string;
  entered_at: string;
  minutes_inside: number | null;
  auto_expire_at: string | null;
}

export interface OccupancyCount {
  current_count: number;
  max_capacity: number | null;
  at_capacity: boolean;
  occupancy_auto_expire_hours: number;
}

export async function getCurrentOccupants(): Promise<Occupant[]> {
  const response = await apiFetch("/occupancy/current");
  if (!response.ok) throw new Error("Failed to load current occupants.");
  return response.json();
}

export async function getLiveCount(): Promise<OccupancyCount> {
  const response = await apiFetch("/occupancy/count");
  if (!response.ok) throw new Error("Failed to load occupancy count.");
  return response.json();
}

export async function checkOutOccupant(occupancyId: number): Promise<void> {
  const response = await apiFetch(`/occupancy/${occupancyId}/checkout`, { method: "POST" });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "Failed to check out.");
  }
}

export interface BanResult {
  success: boolean;
  blacklist_id: number;
  customer_id: number;
  currently_inside: boolean;
}

export async function createBan(input: { customer_id: number; reason: string; manager_notes?: string; expiry_date?: string }): Promise<BanResult> {
  const response = await apiFetch("/blacklist", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "Failed to create ban.");
  }
  return response.json();
}

export interface UnbanResult {
  success: boolean;
  customer_id: number;
}

// Requires manager role or above on the backend (403 for door_staff) —
// lifting a ban is a bigger call than raising one.
export async function removeBan(customerId: number, reason?: string): Promise<UnbanResult> {
  const response = await apiFetch(`/blacklist/${customerId}`, {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ reason: reason || undefined }),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => ({}));
    throw new Error(data.detail || "Failed to remove ban.");
  }
  return response.json();
}
