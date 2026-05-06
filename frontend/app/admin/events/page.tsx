"use client";

import { useEffect, useState } from "react";
import { Calendar, Plus, FileText, Upload, Star, PartyPopper, Pin, Pencil, Trash2 } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  adminEventsApi,
  type AdminEventCreate,
  type EventResponse,
  type EventType,
  type TargetAudience,
} from "@/lib/api";
import { useT, type TKey } from "@/lib/i18n";

const TYPE_META: Record<EventType, { Icon: React.ElementType; color: string; labelKey: TKey }> = {
  exam:       { Icon: FileText,    color: "text-red-600",    labelKey: "events.type.exam" },
  submission: { Icon: Upload,      color: "text-orange-600", labelKey: "events.type.submission" },
  activity:   { Icon: PartyPopper, color: "text-blue-600",   labelKey: "events.type.activity" },
  evaluation: { Icon: Star,        color: "text-purple-600", labelKey: "events.type.evaluation" },
};

function emptyForm(): AdminEventCreate {
  return {
    title: "",
    description: "",
    event_type: "exam",
    target_audience: "all",
    target_value: null,
    start_time: "",
    end_time: null,
    is_mandatory: false,
  };
}

function toLocalIso(local: string): string {
  // datetime-local returns "YYYY-MM-DDTHH:mm" without timezone — treat as local
  if (!local) return "";
  return new Date(local).toISOString();
}

function fromLocalIso(utcString: string): string {
  if (!utcString) return "";
  const d = new Date(utcString);
  if (isNaN(d.getTime())) return "";
  const pad = (n: number) => n.toString().padStart(2, '0');
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
}

export default function AdminEventsPage() {
  const t = useT();
  const [items, setItems] = useState<EventResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [showForm, setShowForm] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState<AdminEventCreate>(emptyForm());
  const [busy, setBusy] = useState(false);

  const reload = async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await adminEventsApi.list();
      setItems(r.data);
    } catch {
      setError("Không tải được sự kiện");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { reload(); }, []);

  const handleSubmit = async () => {
    if (!form.title.trim() || !form.start_time) return;
    setBusy(true);
    try {
      const payload = {
        ...form,
        start_time: toLocalIso(form.start_time),
        end_time: form.end_time ? toLocalIso(form.end_time) : null,
      };
      if (editingId) {
        await adminEventsApi.update(editingId, payload);
      } else {
        await adminEventsApi.create(payload);
      }
      setShowForm(false);
      setEditingId(null);
      setForm(emptyForm());
      await reload();
    } catch {
      alert(editingId ? "Không cập nhật được sự kiện" : "Không tạo được sự kiện");
    } finally {
      setBusy(false);
    }
  };

  const handleEditClick = (ev: EventResponse) => {
    setEditingId(ev.id);
    setForm({
      title: ev.title,
      description: ev.description ?? "",
      event_type: ev.event_type,
      target_audience: ev.target_audience,
      target_value: ev.target_value ?? null,
      start_time: fromLocalIso(ev.start_time),
      end_time: ev.end_time ? fromLocalIso(ev.end_time) : null,
      is_mandatory: ev.is_mandatory,
    });
    setShowForm(true);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const handleDelete = async (id: string) => {
    if (!confirm(t("adminEvents.deleteConfirm"))) return;
    try {
      await adminEventsApi.remove(id);
      setItems((prev) => prev.filter((e) => e.id !== id));
    } catch {
      alert("Không xóa được");
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-primary">{t("adminEvents.title")}</h1>
          <p className="text-muted-foreground text-sm mt-0.5">{t("adminEvents.subtitle")}</p>
        </div>
        <Button onClick={() => { setShowForm((s) => !s); if (editingId) { setEditingId(null); setForm(emptyForm()); } }}>
          <Plus className="h-4 w-4 mr-1.5" />
          {t("adminEvents.createNew")}
        </Button>
      </div>

      {showForm && (
        <Card>
          <CardHeader><CardTitle className="text-base">{editingId ? "Cập nhật sự kiện" : t("adminEvents.createNew")}</CardTitle></CardHeader>
          <CardContent className="space-y-3">
            <div className="grid gap-3 md:grid-cols-2">
              <div>
                <label className="block text-sm font-medium mb-1">{t("adminEvents.formTitle")}</label>
                <Input value={form.title} onChange={(e) => setForm({ ...form, title: e.target.value })} placeholder="VD: Thi cuối kỳ CO3093" />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">{t("adminEvents.formType")}</label>
                <select
                  value={form.event_type}
                  onChange={(e) => setForm({ ...form, event_type: e.target.value as EventType })}
                  className="w-full h-10 px-3 rounded-md border bg-white text-sm"
                >
                  <option value="exam">Thi cử</option>
                  <option value="submission">Deadline</option>
                  <option value="activity">Hoạt động</option>
                  <option value="evaluation">Đánh giá</option>
                </select>
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">{t("adminEvents.formStart")}</label>
                <Input type="datetime-local" value={form.start_time} onChange={(e) => setForm({ ...form, start_time: e.target.value })} />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">{t("adminEvents.formEnd")}</label>
                <Input type="datetime-local" value={form.end_time ?? ""} onChange={(e) => setForm({ ...form, end_time: e.target.value || null })} />
              </div>
              <div>
                <label className="block text-sm font-medium mb-1">{t("adminEvents.formAudience")}</label>
                <select
                  value={form.target_audience}
                  onChange={(e) => setForm({ ...form, target_audience: e.target.value as TargetAudience, target_value: null })}
                  className="w-full h-10 px-3 rounded-md border bg-white text-sm"
                >
                  <option value="all">{t("adminEvents.audience.all")}</option>
                  <option value="faculty_specific">{t("adminEvents.audience.faculty_specific")}</option>
                  <option value="cohort_specific">{t("adminEvents.audience.cohort_specific")}</option>
                </select>
              </div>
              {form.target_audience !== "all" && (
                <div>
                  <label className="block text-sm font-medium mb-1">{t("adminEvents.formAudienceValue")}</label>
                  <Input
                    value={form.target_value ?? ""}
                    onChange={(e) => setForm({ ...form, target_value: e.target.value || null })}
                    placeholder={form.target_audience === "faculty_specific" ? "VD: Khoa học và Kỹ thuật Máy tính" : "VD: 2022"}
                  />
                </div>
              )}
            </div>
            <div>
              <label className="block text-sm font-medium mb-1">{t("adminEvents.formDescription")}</label>
              <textarea
                rows={2}
                value={form.description ?? ""}
                onChange={(e) => setForm({ ...form, description: e.target.value })}
                className="w-full px-3 py-2 rounded-md border bg-white text-sm"
                placeholder="Mô tả ngắn..."
              />
            </div>
            <label className="flex items-center gap-2 text-sm">
              <input
                type="checkbox"
                checked={form.is_mandatory}
                onChange={(e) => setForm({ ...form, is_mandatory: e.target.checked })}
              />
              {t("adminEvents.formMandatory")}
            </label>
            <div className="flex justify-end gap-2">
              <Button variant="outline" onClick={() => { setShowForm(false); setEditingId(null); setForm(emptyForm()); }} disabled={busy}>
                {t("adminEvents.cancel")}
              </Button>
              <Button onClick={handleSubmit} disabled={busy || !form.title.trim() || !form.start_time}>
                {busy ? t("adminEvents.submitting") : (editingId ? "Cập nhật" : t("adminEvents.submitCreate"))}
              </Button>
            </div>
          </CardContent>
        </Card>
      )}

      {loading ? (
        <div className="text-muted-foreground animate-pulse">{t("common.loading")}</div>
      ) : error ? (
        <div className="rounded-md bg-destructive/10 text-destructive px-4 py-3">{error}</div>
      ) : items.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <Calendar className="mx-auto h-10 w-10 mb-3 opacity-30" />
            <p>{t("adminEvents.empty")}</p>
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-2">
          {items.map((ev) => {
            const meta = TYPE_META[ev.event_type] ?? TYPE_META.activity;
            const Icon = meta.Icon;
            return (
              <Card key={ev.id} className={ev.is_mandatory ? "border-l-4 border-l-destructive" : ""}>
                <CardContent className="pt-4 pb-4 flex items-start justify-between gap-3 flex-wrap">
                  <div className="flex items-start gap-3 min-w-0 flex-1">
                    <Icon className={`h-5 w-5 mt-0.5 ${meta.color} shrink-0`} />
                    <div className="min-w-0">
                      <div className="flex items-center gap-2 flex-wrap mb-1">
                        <span className="font-medium">{ev.title}</span>
                        <Badge variant="outline">{t(meta.labelKey)}</Badge>
                        {ev.is_mandatory && <Badge variant="destructive">{t("events.mandatory")}</Badge>}
                        {ev.target_audience !== "all" && ev.target_value && (
                          <Badge variant="secondary" className="inline-flex items-center gap-1">
                            <Pin className="h-3 w-3" />
                            {ev.target_value}
                          </Badge>
                        )}
                      </div>
                      <p className="text-xs text-muted-foreground">
                        {new Date(ev.start_time).toLocaleString("vi-VN")}
                        {ev.end_time && ` → ${new Date(ev.end_time).toLocaleString("vi-VN")}`}
                      </p>
                      {ev.description && <p className="text-sm mt-1">{ev.description}</p>}
                    </div>
                  </div>
                  <div className="flex gap-1 shrink-0">
                    <Button size="sm" variant="ghost" onClick={() => handleEditClick(ev)} title="Sửa">
                      <Pencil className="h-3.5 w-3.5" />
                    </Button>
                    <Button size="sm" variant="ghost" onClick={() => handleDelete(ev.id)}>
                      <Trash2 className="h-3.5 w-3.5 text-destructive" />
                    </Button>
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
