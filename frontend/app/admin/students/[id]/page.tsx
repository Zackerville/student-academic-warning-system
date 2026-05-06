"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from "recharts";
import { ArrowLeft, BellPlus, AlertTriangle, GraduationCap, BookOpen, ShieldAlert } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { adminApi, type AdminStudentDetail } from "@/lib/api";
import { useT } from "@/lib/i18n";

export default function AdminStudentDetailPage() {
  const t = useT();
  const params = useParams<{ id: string }>();
  const router = useRouter();
  const studentId = params.id;

  const [data, setData] = useState<AdminStudentDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showManual, setShowManual] = useState(false);

  const reload = async () => {
    setLoading(true);
    try {
      const r = await adminApi.studentDetail(studentId);
      setData(r.data);
    } catch {
      setError("Không tải được chi tiết sinh viên");
    } finally {
      setLoading(false);
    }
  };

  // eslint-disable-next-line react-hooks/exhaustive-deps
  useEffect(() => { reload(); }, [studentId]);

  if (loading) return <div className="text-muted-foreground animate-pulse">{t("common.loading")}</div>;
  if (error || !data) return <div className="rounded-md bg-destructive/10 text-destructive px-4 py-3">{error}</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={() => router.back()}>
            <ArrowLeft className="h-4 w-4 mr-1" /> {t("adminStudentDetail.back")}
          </Button>
          <div>
            <h1 className="text-2xl font-bold text-primary">{data.full_name}</h1>
            <p className="text-muted-foreground text-sm">
              {data.mssv} · {data.faculty} · {data.major} · K{data.cohort}
            </p>
          </div>
        </div>
        <Button onClick={() => setShowManual((s) => !s)}>
          <BellPlus className="h-4 w-4 mr-1.5" />
          {t("adminStudentDetail.sendManualWarning")}
        </Button>
      </div>

      {showManual && (
        <ManualWarningForm
          studentId={data.student_id}
          studentName={data.full_name}
          onSuccess={() => { setShowManual(false); reload(); }}
          onCancel={() => setShowManual(false)}
        />
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        {/* Profile */}
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-base">{t("adminStudentDetail.profileTitle")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            <Row label="MSSV" value={data.mssv} />
            <Row label="Email" value={data.email} />
            <Row label="Khoa" value={data.faculty} />
            <Row label="Ngành" value={data.major} />
            <Row label="Khóa" value={String(data.cohort)} />
            <Row label="Trạng thái" value={data.is_active ? "Active" : "Disabled"} />
            {data.warning_level >= 1 && (
              <div className="mt-3 p-3 rounded-md bg-orange-50 border border-orange-200">
                <Badge variant={data.warning_level >= 2 ? "destructive" : "secondary"}>
                  {data.warning_level === 3 ? "Buộc thôi học" : `Cảnh báo Mức ${data.warning_level}`}
                </Badge>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Stats */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">{t("adminStudentDetail.statsTitle")}</CardTitle>
          </CardHeader>
          <CardContent className="grid grid-cols-2 gap-4 lg:grid-cols-4">
            <MiniStat icon={GraduationCap} label={t("adminStudentDetail.gpaCumulative")} value={data.gpa_cumulative.toFixed(2)} />
            <MiniStat icon={BookOpen} label={t("adminStudentDetail.creditsEarned")} value={String(data.credits_earned)} />
            <MiniStat icon={AlertTriangle} label={t("adminStudentDetail.failed")} value={String(data.failed_courses_total)} color={data.failed_courses_total > 0 ? "text-destructive" : ""} />
            <MiniStat
              icon={ShieldAlert}
              label={t("adminStudentDetail.riskScore")}
              value={data.risk_score !== null ? `${(data.risk_score * 100).toFixed(0)}%` : "—"}
              color={data.risk_score !== null && data.risk_score >= 0.6 ? "text-destructive" : ""}
            />
          </CardContent>
        </Card>
      </div>

      {/* Risk factors */}
      {data.risk_factors.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("adminStudentDetail.riskFactors")}</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {data.risk_factors.slice(0, 5).map((f, i) => {
              const label = String(f.label ?? f.feature ?? `Yếu tố ${i + 1}`);
              const impact = Number(f.impact ?? 0);
              const direction = String(f.direction ?? "+");
              const isPositive = direction === "+";
              const widthPct = Math.min(100, Math.abs(impact) * 100);
              return (
                <div key={i}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="truncate pr-2">
                      <span className={isPositive ? "text-destructive" : "text-green-600"}>
                        {isPositive ? "+ " : "− "}
                      </span>
                      {label}
                    </span>
                    <span className="font-semibold shrink-0">{(Math.abs(impact) * 100).toFixed(0)}%</span>
                  </div>
                  <div className="h-2 bg-muted rounded-full overflow-hidden">
                    <div className={`h-full ${isPositive ? "bg-destructive/80" : "bg-green-600/80"}`} style={{ width: `${widthPct}%` }} />
                  </div>
                </div>
              );
            })}
          </CardContent>
        </Card>
      )}

      {/* GPA chart */}
      {data.gpa_history.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("adminStudentDetail.gpaTrend")}</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={data.gpa_history} margin={{ top: 4, right: 16, left: -16, bottom: 0 }}>
                <defs>
                  <linearGradient id="adminGpaGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="semester" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
                <YAxis domain={[0, 4]} ticks={[0, 1, 2, 3, 4]} tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
                <Tooltip formatter={(v) => [typeof v === "number" ? v.toFixed(2) : v, "GPA"]} contentStyle={{ fontSize: 12 }} />
                <Area type="monotone" dataKey="semester_gpa" stroke="hsl(var(--primary))" strokeWidth={2} fill="url(#adminGpaGrad)" dot={{ r: 4 }} />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* Warnings history */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("adminStudentDetail.warningsHistory")}</CardTitle>
        </CardHeader>
        <CardContent>
          {data.warnings.length === 0 ? (
            <p className="text-sm text-muted-foreground py-4 text-center">{t("adminStudentDetail.noWarnings")}</p>
          ) : (
            <div className="space-y-2">
              {data.warnings.map((w) => (
                <div
                  key={w.id}
                  className={`rounded-md border-l-4 px-4 py-3 ${
                    w.level === 3 ? "border-l-red-600 bg-red-50/40"
                    : w.level === 2 ? "border-l-orange-500 bg-orange-50/40"
                    : "border-l-yellow-500 bg-yellow-50/40"
                  } ${w.is_resolved ? "opacity-60" : ""}`}
                >
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <Badge variant={w.level >= 2 ? "destructive" : "secondary"}>
                      Mức {w.level}
                    </Badge>
                    <span className="text-sm font-medium">HK {w.semester}</span>
                    <span className="text-xs text-muted-foreground">
                      {w.created_by === "system" ? "Hệ thống" : "Admin"}
                    </span>
                    {w.is_resolved && <Badge className="bg-green-600 hover:bg-green-600">Đã xử lý</Badge>}
                  </div>
                  <p className="text-sm">{w.reason}</p>
                  <p className="text-xs text-muted-foreground mt-1">
                    GPA: {w.gpa_at_warning.toFixed(2)} ·{" "}
                    {w.sent_at ? new Date(w.sent_at).toLocaleString("vi-VN") : "—"}
                  </p>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-2">
      <span className="text-muted-foreground">{label}</span>
      <span className="font-medium text-right truncate">{value}</span>
    </div>
  );
}

function MiniStat({
  icon: Icon, label, value, color,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <div className="space-y-1">
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <Icon className="h-3.5 w-3.5" />
        {label}
      </div>
      <p className={`text-2xl font-bold ${color ?? ""}`}>{value}</p>
    </div>
  );
}

function ManualWarningForm({
  studentId, studentName, onSuccess, onCancel,
}: {
  studentId: string;
  studentName: string;
  onSuccess: () => void;
  onCancel: () => void;
}) {
  const t = useT();
  const [level, setLevel] = useState(1);
  const [semester, setSemester] = useState("241");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const submit = async () => {
    if (!reason.trim()) {
      setErr("Vui lòng nhập lý do");
      return;
    }
    setBusy(true);
    setErr(null);
    try {
      await adminApi.manualWarning({ student_id: studentId, level, semester: semester.trim(), reason: reason.trim() });
      onSuccess();
    } catch {
      setErr("Không tạo được cảnh báo. Kiểm tra dữ liệu rồi thử lại.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Card className="border-orange-300 bg-orange-50/40">
      <CardHeader>
        <CardTitle className="text-base">
          {t("adminStudentDetail.manualTitle")} — {studentName}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid gap-3 md:grid-cols-2">
          <div>
            <label className="block text-sm font-medium mb-1">{t("adminStudentDetail.manualLevel")}</label>
            <select
              value={level}
              onChange={(e) => setLevel(Number(e.target.value))}
              className="w-full h-10 px-3 rounded-md border bg-white text-sm"
            >
              <option value={1}>Mức 1</option>
              <option value={2}>Mức 2</option>
              <option value={3}>Buộc thôi học</option>
            </select>
          </div>
          <div>
            <label className="block text-sm font-medium mb-1">{t("adminStudentDetail.manualSemester")}</label>
            <Input value={semester} onChange={(e) => setSemester(e.target.value)} placeholder="241" />
          </div>
        </div>
        <div>
          <label className="block text-sm font-medium mb-1">{t("adminStudentDetail.manualReason")}</label>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={3}
            className="w-full px-3 py-2 rounded-md border bg-white text-sm"
            placeholder="VD: GPA tích lũy 1.4 — vi phạm quy chế"
          />
        </div>
        {err && <p className="text-sm text-destructive">{err}</p>}
        <div className="flex justify-end gap-2">
          <Button variant="outline" onClick={onCancel} disabled={busy}>{t("adminEvents.cancel")}</Button>
          <Button onClick={submit} disabled={busy}>
            {busy ? t("common.saving") : t("adminStudentDetail.manualSubmit")}
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
