import React, { useState, useEffect } from "react";
import { Bell, AlertTriangle, Info, CheckCircle2 } from "lucide-react";
import { apiFetch } from "../lib/api";

export function NotificationFeed() {
  const [notifications, setNotifications] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchNotifications = async () => {
      try {
        const response = await apiFetch("/notifications");
        if (response.ok) {
          const data = await response.json();
          setNotifications(data);
        }
      } catch (err) {
        console.error("Error fetching notifications:", err);
      } finally {
        setLoading(false);
      }
    };
    
    fetchNotifications();
    // 10s: alerts (e.g. a banned customer at the door) are time-sensitive
    // enough to poll faster than the other tabs, but 3s was excessive.
    const interval = setInterval(fetchNotifications, 10000);
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return <div className="flex justify-center items-center h-64 text-muted-foreground">Loading notifications...</div>;
  }

  return (
    <div className="space-y-6 max-w-4xl mx-auto">
      <div className="flex items-center gap-3 mb-8">
        <Bell className="h-8 w-8 text-primary" />
        <h2 className="text-2xl font-bold text-foreground">Alerts & Notifications</h2>
      </div>

      <div className="space-y-4">
        {notifications.length === 0 ? (
          <div className="text-center p-12 glass-panel rounded-xl text-muted-foreground">
            No active notifications
          </div>
        ) : (
          notifications.map((notif, i) => (
            <div key={i} className={`flex items-start gap-4 p-5 rounded-xl border ${notif.type === 'ALERT' ? 'bg-red-500/10 border-red-500/30' : 'bg-muted/30 border-border/50'}`}>
              <div className="mt-1">
                {notif.type === 'ALERT' && <AlertTriangle className="h-6 w-6 text-red-500" />}
                {notif.type === 'INFO' && <Info className="h-6 w-6 text-blue-500" />}
                {notif.type === 'SUCCESS' && <CheckCircle2 className="h-6 w-6 text-green-500" />}
                {!['ALERT', 'INFO', 'SUCCESS'].includes(notif.type) && <Bell className="h-6 w-6 text-primary" />}
              </div>
              <div className="flex-1">
                <p className="text-sm font-semibold text-foreground">{notif.message}</p>
                <p className="text-xs text-muted-foreground mt-1">{new Date(notif.created_at).toLocaleString()}</p>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
