"use client";

import { useEffect, useState } from "react";
import { Bot, Hourglass, Mail, CheckCheck, Settings, Play } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { adminApi, type PendingWarningItem } from "@/lib/api";
import { useT } from "@/lib/i18n";

export default function AdminWarningsPage() {
  const t = useT();
  const [items, setItems] = useState<PendingWarningItem[]>([]);
  const [threshold, setThreshold] = useState(0.6);
  const [lastBatch, setLastBatch] = useState<string | null>(null);
  const [sentCount, setSentCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [busyId, setBusyId] = useState<string | null>(null);
  const [runningBatch, setRunningBatch] = useState(false);
  const [showThreshold, setShowThreshold] = useState(false);

  const reload = async () => {
    setLoading(true);
    setError(null);
    try {
      const r = await adminApi.pendingWarnings();
      setItems(r.data.items);
      setThreshold(r.data.threshold);
      setLastBatch(r.data.last_batch_at);
    } catch {
      setError("Không tải được danh sách");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { reload(); }, []);

  const handleApprove = async (item: PendingWarningItem) => {
    setBusyId(item.student_id);
    try {
      await adminApi.approveWarning({
        student_id: item.student_id,
        semester: item.semester,
        level: item.suggested_level,
        reason: item.reason,
      });
      setItems((prev) => prev.filter((p) => p.student_id !== item.student_id));
      setSentCount((c) => c + 1);
    } catch {
      alert("Không duyệt được. Thử lại.");
    } finally {
      setBusyId(null);
    }
  };

  const handleDismiss = (studentId: string) => {
    setItems((prev) => prev.filter((p) => p.student_id !== studentId));
  };

  const handleRunBatch = async () => {
    if (!confirm("Chạy AI batch toàn hệ thống? Quá trình có thể mất vài phút với DB lớn.")) return;
    setRunningBatch(true);
    try {
      // Step 1: predictions
      await adminApi.runBatchPredictions().catch(() => null);
      // Step 2: warnings (auto regulation-based)
      await adminApi.runBatchWarnings().catch(() => null);
      await reload();
    } finally {
      setRunningBatch(false);
    }
  };

  const lastBatchLabel = lastBatch
    ? new Date(lastBatch).toLocaleString("vi-VN")
    : t("adminWarnings.noBatch");

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-primary">{t("adminWarnings.title")}</h1>
          <p className="text-muted-foreground text-sm mt-0.5">{t("adminWarnings.subtitle")}</p>
        </div>
        <div className="flex gap-2">
          <Button variant="outline" size="sm" onClick={() => setShowThreshold(!showThreshold)}>
            <Settings className="h-4 w-4 mr-1.5" />
            {t("adminWarnings.threshold")}
          </Button>
          <Button onClick={handleRunBatch} disabled={runningBatch}>
            <Play className="h-4 w-4 mr-1.5" />
            {runningBatch ? t("adminWarnings.running") : t("adminWarnings.runBatch")}
          </Button>
        </div>
      </div>

      {showThreshold && (
        <Card className="bg-blue-50 border-blue-200">
          <CardContent className="pt-6 text-sm space-y-1">
            <p className="font-medium text-blue-900">Ngưỡng AI Early Warning</p>
            <p className="text-blue-900/80">
              Hiện tại: <span className="font-semibold">{(threshold * 100).toFixed(0)}%</span> — predictions có risk_score ≥ ngưỡng sẽ xuất hiện ở danh sách &quot;Chờ duyệt&quot;.
            </p>
            <p className="text-xs text-blue-900/60 italic mt-2">
              Sửa ngưỡng tại <code>backend/.env</code> → <code>AI_EARLY_WARNING_THRESHOLD</code>, restart backend.
            </p>
          </CardContent>
        </Card>
      )}

      {/* Stats */}
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <StatCard icon={Hourglass} label={t("adminWarnings.statPending")} value={items.length} color="text-orange-600" />
        <StatCard icon={Mail} label={t("adminWarnings.statSentSemester")} value={sentCount} />
        <StatCard
          icon={CheckCheck}
          label={t("adminWarnings.statLastBatch")}
          value={lastBatchLabel}
          isText
        />
      </div>

      {/* Pending list */}
      {loading ? (
        <div className="text-muted-foreground animate-pulse">{t("common.loading")}</div>
      ) : error ? (
        <div className="rounded-md bg-destructive/10 text-destructive px-4 py-3">{error}</div>
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("adminWarnings.pendingTitle")}</CardTitle>
          </CardHeader>
          <CardContent>
            {items.length === 0 ? (
              <p className="text-sm text-muted-foreground py-6 text-center">{t("adminWarnings.empty")}</p>
            ) : (
              <div className="space-y-2">
                {items.map((it) => (
                  <div
                    key={it.student_id}
                    className={`flex items-center justify-between gap-3 px-4 py-3 rounded-md border-l-4 ${
                      it.suggested_level >= 3 ? "border-l-red-600 bg-red-50/40"
                      : it.suggested_level >= 2 ? "border-l-orange-500 bg-orange-50/40"
                      : "border-l-yellow-500 bg-yellow-50/40"
                    } flex-wrap`}
                  >
                    <div className="flex items-start gap-2 flex-wrap min-w-0 flex-1">
                      <Bot className="h-4 w-4 text-primary mt-0.5 shrink-0" />
                      <div className="min-w-0">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-medium text-sm">{it.full_name}</span>
                          <span className="font-mono text-xs text-muted-foreground">{it.mssv}</span>
                          <Badge variant={it.suggested_level >= 2 ? "destructive" : "secondary"}>
                            {it.suggested_level === 3 ? "Buộc thôi học" : `Mức ${it.suggested_level}`}
                          </Badge>
                          <Badge variant="outline">{it.faculty}</Badge>
                        </div>
                        <p className="text-xs text-muted-foreground mt-0.5">
                          {it.reason} · HK {it.semester}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="font-bold text-destructive">
                        {(it.risk_score * 100).toFixed(0)}%
                      </span>
                      <Button
                        size="sm"
                        onClick={() => handleApprove(it)}
                        disabled={busyId === it.student_id}
                      >
                        {busyId === it.student_id ? t("adminWarnings.approving") : t("adminWarnings.approve")}
                      </Button>
                      <Button size="sm" variant="ghost" onClick={() => handleDismiss(it.student_id)}>
                        ✕
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}

function StatCard({
  icon: Icon, label, value, color, isText,
}: {
  icon: React.ElementType;
  label: string;
  value: number | string;
  color?: string;
  isText?: boolean;
}) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-start justify-between">
          <div className="min-w-0">
            <p className="text-sm text-muted-foreground">{label}</p>
            <p className={`mt-1 ${isText ? "text-sm font-medium" : "text-3xl font-bold"} ${color ?? ""}`}>
              {value}
            </p>
          </div>
          <div className="p-2 rounded-lg bg-primary/10 shrink-0">
            <Icon className="h-5 w-5 text-primary" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
