"use client";

import { useEffect, useState } from "react";
import { Bell, AlertTriangle, Calendar, Clock, CheckCheck, Mail } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  notificationsApi,
  type NotificationResponse,
  type NotificationType,
} from "@/lib/api";
import { useT, type TKey } from "@/lib/i18n";

const TYPE_META: Record<NotificationType, { Icon: React.ComponentType<{ className?: string }>; color: string; labelKey: TKey }> = {
  warning:  { Icon: AlertTriangle, color: "text-destructive", labelKey: "notifications.type.warning" },
  reminder: { Icon: Clock,         color: "text-orange-500", labelKey: "notifications.type.reminder" },
  event:    { Icon: Calendar,      color: "text-blue-600",   labelKey: "notifications.type.event" },
  system:   { Icon: Bell,          color: "text-gray-600",   labelKey: "notifications.type.system" },
};

export default function NotificationsPage() {
  const t = useT();
  const [items, setItems] = useState<NotificationResponse[]>([]);
  const [emailEnabled, setEmailEnabled] = useState(true);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [busyAll, setBusyAll] = useState(false);
  const [savingPref, setSavingPref] = useState(false);

  useEffect(() => {
    Promise.all([notificationsApi.list(false, 100), notificationsApi.getPreferences()])
      .then(([listRes, prefsRes]) => {
        setItems(listRes.data);
        setEmailEnabled(prefsRes.data.email_notifications_enabled);
      })
      .catch(() => setError(t("notifications.loadError")))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const handleMarkRead = async (id: string) => {
    // optimistic update
    setItems((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: true } : n)));
    try {
      await notificationsApi.markRead(id);
    } catch {
      // revert on fail
      setItems((prev) => prev.map((n) => (n.id === id ? { ...n, is_read: false } : n)));
    }
  };

  const handleMarkAllRead = async () => {
    setBusyAll(true);
    try {
      await notificationsApi.markAllRead();
      setItems((prev) => prev.map((n) => ({ ...n, is_read: true })));
    } catch {
      alert(t("notifications.markAllError"));
    } finally {
      setBusyAll(false);
    }
  };

  const handleTogglePref = async () => {
    const next = !emailEnabled;
    setEmailEnabled(next);
    setSavingPref(true);
    try {
      await notificationsApi.updatePreferences(next);
    } catch {
      setEmailEnabled(!next); // revert
      alert(t("notifications.prefError"));
    } finally {
      setSavingPref(false);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-muted-foreground animate-pulse">{t("common.loading")}</div>
      </div>
    );
  }

  if (error) {
    return <div className="rounded-md bg-destructive/10 text-destructive px-4 py-3">{error}</div>;
  }

  const unread = items.filter((n) => !n.is_read).length;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-primary">{t("notifications.title")}</h1>
          <p className="text-muted-foreground text-sm mt-0.5">
            {unread > 0
              ? t("notifications.unreadCount").replace("{n}", String(unread))
              : t("notifications.allRead")}
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          disabled={unread === 0 || busyAll}
          onClick={handleMarkAllRead}
        >
          <CheckCheck className="h-4 w-4 mr-1" />
          {busyAll ? t("common.saving") : t("notifications.markAllRead")}
        </Button>
      </div>

      {/* Email preference */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-base flex items-center gap-2">
            <Mail className="h-4 w-4 text-primary" />
            {t("notifications.prefTitle")}
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between gap-4">
            <div className="text-sm text-muted-foreground">
              {t("notifications.prefDescription")}
            </div>
            <button
              type="button"
              role="switch"
              aria-checked={emailEnabled}
              disabled={savingPref}
              onClick={handleTogglePref}
              className={`relative inline-flex h-6 w-11 items-center rounded-full transition-colors ${
                emailEnabled ? "bg-primary" : "bg-gray-300"
              }`}
            >
              <span
                className={`inline-block h-4 w-4 transform rounded-full bg-white transition-transform ${
                  emailEnabled ? "translate-x-6" : "translate-x-1"
                }`}
              />
            </button>
          </div>
        </CardContent>
      </Card>

      {/* List */}
      {items.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <Bell className="mx-auto h-10 w-10 mb-3 opacity-30" />
            <p>{t("notifications.empty")}</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {items.map((n) => {
            const meta = TYPE_META[n.type] ?? TYPE_META.system;
            const Icon = meta.Icon;
            return (
              <Card
                key={n.id}
                className={`cursor-pointer transition-colors hover:bg-muted/30 ${
                  !n.is_read ? "border-l-4 border-l-primary" : ""
                }`}
                onClick={() => !n.is_read && handleMarkRead(n.id)}
              >
                <CardContent className="pt-4 pb-4">
                  <div className="flex items-start gap-3">
                    <div className={`mt-0.5 ${meta.color}`}>
                      <Icon className="h-4 w-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 flex-wrap mb-1">
                        <span className={`text-sm font-medium ${!n.is_read ? "text-foreground" : "text-muted-foreground"}`}>
                          {n.title}
                        </span>
                        <Badge variant="outline" className="text-xs">{t(meta.labelKey)}</Badge>
                        {!n.is_read && (
                          <span className="h-2 w-2 rounded-full bg-primary" aria-label="unread" />
                        )}
                      </div>
                      <p className="text-sm text-muted-foreground whitespace-pre-wrap">{n.content}</p>
                      <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
                        <span>{new Date(n.sent_at).toLocaleString("vi-VN")}</span>
                        {n.email_sent_at && (
                          <span className="inline-flex items-center gap-1">
                            <Mail className="h-3 w-3" />
                            {t("notifications.emailSent")}
                          </span>
                        )}
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}
    </div>
  );
}
