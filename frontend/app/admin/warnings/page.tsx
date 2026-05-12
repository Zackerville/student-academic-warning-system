"use client";
import { SkeletonTable } from "@/components/ui/skeleton";

import { useEffect, useState } from "react";
import { Bot, Hourglass, Mail, CheckCheck, Settings, Play, Eye, AlertTriangle, GraduationCap, BookOpen, TrendingDown } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { Separator } from "@/components/ui/separator";
import { adminApi, type PendingWarningItem, type AdminStudentDetail } from "@/lib/api";
import { Input } from "@/components/ui/input";
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
  const [editingThreshold, setEditingThreshold] = useState("");
  const [savingThreshold, setSavingThreshold] = useState(false);
  const [thresholdError, setThresholdError] = useState<string | null>(null);

  const [detailItem, setDetailItem] = useState<PendingWarningItem | null>(null);
  const [studentDetail, setStudentDetail] = useState<AdminStudentDetail | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);

  const openDetail = async (item: PendingWarningItem) => {
    setDetailItem(item);
    setStudentDetail(null);
    setDetailLoading(true);
    try {
      const r = await adminApi.studentDetail(item.student_id);
      setStudentDetail(r.data);
    } catch {
      // show what we have from the list item
    } finally {
      setDetailLoading(false);
    }
  };

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

  const handleSaveThreshold = async () => {
    const val = parseFloat(editingThreshold);
    if (isNaN(val) || val <= 0 || val >= 1) {
      setThresholdError("Ngưỡng phải là số trong khoảng (0, 1), ví dụ: 0.6");
      return;
    }
    setSavingThreshold(true);
    setThresholdError(null);
    try {
      const r = await adminApi.updateThreshold(val);
      setThreshold(r.data.ai_early_warning_threshold);
      setEditingThreshold("");
      setShowThreshold(false);
    } catch {
      setThresholdError("Lưu thất bại, thử lại.");
    } finally {
      setSavingThreshold(false);
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
          <CardContent className="pt-5 pb-5 space-y-3">
            <p className="font-medium text-blue-900 text-sm">Ngưỡng AI Early Warning</p>
            <p className="text-blue-900/80 text-sm">
              Hiện tại: <span className="font-bold text-blue-900">{(threshold * 100).toFixed(0)}%</span>
              <span className="text-blue-900/60"> — predictions có risk_score ≥ ngưỡng xuất hiện ở danh sách &quot;Chờ duyệt&quot;.</span>
            </p>
            <div className="flex items-center gap-2">
              <Input
                type="number"
                step="0.05"
                min="0.05"
                max="0.95"
                placeholder={`Ngưỡng mới (VD: ${threshold})`}
                value={editingThreshold}
                onChange={(e) => { setEditingThreshold(e.target.value); setThresholdError(null); }}
                className="h-8 w-40 text-sm bg-white"
              />
              <Button size="sm" onClick={handleSaveThreshold} disabled={savingThreshold || !editingThreshold}>
                {savingThreshold ? "Đang lưu..." : "Lưu"}
              </Button>
              <Button size="sm" variant="ghost" onClick={() => { setShowThreshold(false); setEditingThreshold(""); setThresholdError(null); }}>
                Huỷ
              </Button>
            </div>
            {thresholdError && <p className="text-xs text-destructive">{thresholdError}</p>}
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
        <SkeletonTable rows={6} />
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
                      <Button size="sm" variant="outline" onClick={() => openDetail(it)}>
                        <Eye className="h-3.5 w-3.5 mr-1" />
                        Chi tiết
                      </Button>
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

      {/* Detail Dialog */}
      <Dialog open={!!detailItem} onOpenChange={(open: boolean) => { if (!open) setDetailItem(null); }}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <AlertTriangle className="h-5 w-5 text-orange-500" />
              Chi tiết cảnh báo học vụ
            </DialogTitle>
          </DialogHeader>

          {detailItem && (
            <div className="space-y-4 text-sm">
              {/* Student basic info */}
              <div className="rounded-lg border p-4 space-y-2">
                <p className="font-semibold text-base flex items-center gap-2">
                  <GraduationCap className="h-4 w-4 text-primary" />
                  {detailItem.full_name}
                  <span className="font-mono text-xs text-muted-foreground">{detailItem.mssv}</span>
                </p>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-muted-foreground">
                  <span>Khoa</span>
                  <span className="text-foreground font-medium">{detailItem.faculty}</span>
                  {studentDetail?.major && (
                    <>
                      <span>Ngành</span>
                      <span className="text-foreground font-medium">{studentDetail.major}</span>
                    </>
                  )}
                  {studentDetail?.cohort && (
                    <>
                      <span>Khóa</span>
                      <span className="text-foreground font-medium">{studentDetail.cohort}</span>
                    </>
                  )}
                  {studentDetail?.email && (
                    <>
                      <span>Email</span>
                      <span className="text-foreground font-medium break-all">{studentDetail.email}</span>
                    </>
                  )}
                </div>
              </div>

              {/* Academic stats */}
              <div className="rounded-lg border p-4 space-y-2">
                <p className="font-semibold flex items-center gap-2">
                  <BookOpen className="h-4 w-4 text-primary" />
                  Tình trạng học tập
                </p>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-muted-foreground">
                  <span>GPA tích lũy</span>
                  <span className={`font-bold ${detailItem.gpa_cumulative < 1.2 ? "text-destructive" : detailItem.gpa_cumulative < 2.0 ? "text-orange-600" : "text-green-600"}`}>
                    {detailItem.gpa_cumulative.toFixed(2)}
                  </span>
                  {studentDetail && (
                    <>
                      <span>Tín chỉ tích lũy</span>
                      <span className="text-foreground font-medium">{studentDetail.credits_earned} TC</span>
                      <span>Môn F hiện tại</span>
                      <span className={`font-medium ${studentDetail.failed_courses_total > 0 ? "text-destructive" : "text-foreground"}`}>
                        {studentDetail.failed_courses_total} môn
                      </span>
                      <span>Mức cảnh báo hiện tại</span>
                      <span className="font-medium">
                        {studentDetail.warning_level === 0 ? "Không cảnh báo" : `Mức ${studentDetail.warning_level}`}
                      </span>
                    </>
                  )}
                  {detailLoading && <span className="col-span-2 text-muted-foreground italic">Đang tải thêm thông tin...</span>}
                </div>
              </div>

              {/* Warning being reviewed */}
              <div className={`rounded-lg border-l-4 p-4 space-y-2 ${
                detailItem.suggested_level >= 3 ? "border-l-red-600 bg-red-50/50"
                : detailItem.suggested_level >= 2 ? "border-l-orange-500 bg-orange-50/50"
                : "border-l-yellow-500 bg-yellow-50/50"
              }`}>
                <p className="font-semibold flex items-center gap-2">
                  <TrendingDown className="h-4 w-4 text-destructive" />
                  Cảnh báo đề xuất
                </p>
                <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-muted-foreground">
                  <span>Mức đề xuất</span>
                  <Badge variant={detailItem.suggested_level >= 2 ? "destructive" : "secondary"} className="w-fit">
                    {detailItem.suggested_level === 3 ? "Buộc thôi học" : `Cảnh báo mức ${detailItem.suggested_level}`}
                  </Badge>
                  <span>Risk score AI</span>
                  <span className="font-bold text-destructive">{(detailItem.risk_score * 100).toFixed(1)}%</span>
                  <span>Mức rủi ro</span>
                  <span className="font-medium capitalize">{detailItem.risk_level}</span>
                  <span>Học kỳ</span>
                  <span className="font-medium">{detailItem.semester}</span>
                </div>
                <Separator className="my-1" />
                <p className="font-medium text-foreground">Lý do:</p>
                <p className="text-foreground leading-relaxed">{detailItem.reason}</p>
              </div>

              {/* Warning history */}
              {studentDetail?.warnings && studentDetail.warnings.length > 0 && (
                <div className="rounded-lg border p-4 space-y-2">
                  <p className="font-semibold">Lịch sử cảnh báo ({studentDetail.warnings.length})</p>
                  <div className="space-y-1.5">
                    {studentDetail.warnings.slice(0, 5).map((w, i) => (
                      <div key={i} className="flex items-center justify-between text-xs">
                        <span className="text-muted-foreground">HK {w.semester}</span>
                        <Badge variant={w.level >= 2 ? "destructive" : "secondary"} className="text-xs">
                          {w.level === 3 ? "Buộc thôi học" : `Mức ${w.level}`}
                        </Badge>
                        <span className={w.is_resolved ? "text-green-600" : "text-orange-600"}>
                          {w.is_resolved ? "Đã xử lý" : "Chưa xử lý"}
                        </span>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* Actions */}
              <div className="flex gap-2 pt-1">
                <Button
                  className="flex-1"
                  onClick={() => { handleApprove(detailItem); setDetailItem(null); }}
                  disabled={busyId === detailItem.student_id}
                >
                  {busyId === detailItem.student_id ? t("adminWarnings.approving") : "Duyệt cảnh báo"}
                </Button>
                <Button variant="outline" onClick={() => setDetailItem(null)}>Đóng</Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
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
