"use client";

import { useEffect, useState } from "react";
import { Calendar, FileText, Upload, Star, PartyPopper, Pin } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { eventsApi, type EventResponse, type EventType } from "@/lib/api";
import { useT, type TKey } from "@/lib/i18n";

type Tab = "upcoming" | "all";

const TYPE_META: Record<EventType, { Icon: React.ComponentType<{ className?: string }>; color: string; labelKey: TKey }> = {
  exam:       { Icon: FileText,    color: "text-red-600",    labelKey: "events.type.exam" },
  submission: { Icon: Upload,      color: "text-orange-600", labelKey: "events.type.submission" },
  activity:   { Icon: PartyPopper, color: "text-blue-600",   labelKey: "events.type.activity" },
  evaluation: { Icon: Star,        color: "text-purple-600", labelKey: "events.type.evaluation" },
};

function formatRange(start: string, end: string | null): string {
  const s = new Date(start);
  const sStr = s.toLocaleString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
  if (!end) return sStr;
  const e = new Date(end);
  const sameDay = s.toDateString() === e.toDateString();
  const eStr = sameDay
    ? e.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" })
    : e.toLocaleString("vi-VN", { day: "2-digit", month: "2-digit", year: "numeric", hour: "2-digit", minute: "2-digit" });
  return `${sStr} → ${eStr}`;
}

function daysFromNow(dateStr: string): number {
  const ms = new Date(dateStr).getTime() - Date.now();
  return Math.round(ms / (1000 * 60 * 60 * 24));
}

export default function EventsPage() {
  const t = useT();
  const [tab, setTab] = useState<Tab>("upcoming");
  const [events, setEvents] = useState<EventResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    const fetcher = tab === "upcoming" ? eventsApi.myUpcoming(50) : eventsApi.myEvents(100);
    fetcher
      .then((r) => setEvents(r.data))
      .catch(() => setError(t("events.loadError")))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [tab]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-primary">{t("events.title")}</h1>
        <p className="text-muted-foreground text-sm mt-0.5">{t("events.subtitle")}</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2">
        <Button variant={tab === "upcoming" ? "default" : "outline"} size="sm" onClick={() => setTab("upcoming")}>
          {t("events.tab.upcoming")}
        </Button>
        <Button variant={tab === "all" ? "default" : "outline"} size="sm" onClick={() => setTab("all")}>
          {t("events.tab.all")}
        </Button>
      </div>

      {loading ? (
        <div className="flex items-center justify-center h-64">
          <div className="text-muted-foreground animate-pulse">{t("common.loading")}</div>
        </div>
      ) : error ? (
        <div className="rounded-md bg-destructive/10 text-destructive px-4 py-3">{error}</div>
      ) : events.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <Calendar className="mx-auto h-10 w-10 mb-3 opacity-30" />
            <p>{tab === "upcoming" ? t("events.empty.upcoming") : t("events.empty.all")}</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {events.map((ev) => {
            const meta = TYPE_META[ev.event_type] ?? TYPE_META.activity;
            const Icon = meta.Icon;
            const days = daysFromNow(ev.start_time);
            const inFuture = days >= 0;
            return (
              <Card key={ev.id} className={ev.is_mandatory ? "border-l-4 border-l-destructive" : ""}>
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between gap-3 flex-wrap">
                    <div className="flex items-center gap-2 flex-wrap">
                      <Icon className={`h-5 w-5 ${meta.color}`} />
                      <CardTitle className="text-base">{ev.title}</CardTitle>
                      <Badge variant="outline">{t(meta.labelKey)}</Badge>
                      {ev.is_mandatory && <Badge variant="destructive">{t("events.mandatory")}</Badge>}
                      {ev.target_audience !== "all" && ev.target_value && (
                        <Badge variant="secondary" className="inline-flex items-center gap-1">
                          <Pin className="h-3 w-3" />
                          {ev.target_value}
                        </Badge>
                      )}
                    </div>
                    {inFuture && days <= 7 && (
                      <Badge variant={days <= 1 ? "destructive" : "secondary"} className="shrink-0">
                        {days === 0
                          ? t("events.today")
                          : days === 1
                            ? t("events.tomorrow")
                            : t("events.inDays").replace("{n}", String(days))}
                      </Badge>
                    )}
                  </div>
                </CardHeader>
                <CardContent className="space-y-2">
                  {ev.description && <p className="text-sm">{ev.description}</p>}
                  <div className="text-xs text-muted-foreground flex items-center gap-1.5">
                    <Calendar className="h-3.5 w-3.5" />
                    {formatRange(ev.start_time, ev.end_time)}
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
