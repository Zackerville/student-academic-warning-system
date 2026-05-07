"use client";

import { useEffect, useState } from "react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
} from "recharts";
import Link from "next/link";
import { GraduationCap, BookOpen, AlertTriangle, TrendingUp, Bot } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import {
  studentApi,
  predictionsApi,
  type DashboardData,
  type GpaHistoryEntry,
  type PredictionResponse,
} from "@/lib/api";
import { useT, type TKey } from "@/lib/i18n";

const RISK_COLOR_BY_LEVEL: Record<string, string> = {
  low:      "text-green-600",
  medium:   "text-yellow-600",
  high:     "text-orange-500",
  critical: "text-destructive",
};

const RISK_LABEL_KEYS: Record<string, TKey> = {
  low:      "predictions.riskLevel.low",
  medium:   "predictions.riskLevel.medium",
  high:     "predictions.riskLevel.high",
  critical: "predictions.riskLevel.critical",
};

const WARNING_KEYS: Record<number, { labelKey: TKey; variant: "default" | "secondary" | "destructive" }> = {
  0: { labelKey: "dashboard.warning.0", variant: "default" },
  1: { labelKey: "dashboard.warning.1", variant: "secondary" },
  2: { labelKey: "dashboard.warning.2", variant: "destructive" },
  3: { labelKey: "dashboard.warning.3", variant: "destructive" },
};

function StatCard({
  icon: Icon,
  title,
  value,
  sub,
  color,
}: {
  icon: React.ElementType;
  title: string;
  value: string | number;
  sub?: string;
  color?: string;
}) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm text-muted-foreground">{title}</p>
            <p className={`text-3xl font-bold mt-1 ${color ?? "text-foreground"}`}>{value}</p>
            {sub && <p className="text-xs text-muted-foreground mt-1">{sub}</p>}
          </div>
          <div className="p-2 rounded-lg bg-primary/10">
            <Icon className="h-5 w-5 text-primary" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export default function DashboardPage() {
  const t = useT();
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [history, setHistory] = useState<GpaHistoryEntry[]>([]);
  const [prediction, setPrediction] = useState<PredictionResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([studentApi.dashboard(), studentApi.gpaHistory()])
      .then(([d, h]) => {
        setDashboard(d.data);
        setHistory(h.data);
      })
      .catch(() => setError(t("dashboard.loadError")))
      .finally(() => setLoading(false));

    // Prediction load — không block dashboard nếu fail (có thể chưa train model)
    predictionsApi.me().then((r) => setPrediction(r.data)).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-muted-foreground animate-pulse">{t("common.loading")}</div>
      </div>
    );
  }

  if (error || !dashboard) {
    return (
      <div className="rounded-md bg-destructive/10 text-destructive px-4 py-3">
        {error ?? t("common.unknownError")}
      </div>
    );
  }

  const { student, current_semester, credits_in_progress } = dashboard;
  const failed_courses_total =
    dashboard.unresolved_failed_courses ?? dashboard.failed_courses_total;
  const warning = WARNING_KEYS[student.warning_level] ?? WARNING_KEYS[0];

  // Compute GPA trend insight from last 2 semesters
  const gpaInsight = (() => {
    if (history.length < 2) return null;
    const sorted = [...history].sort((a, b) => a.semester.localeCompare(b.semester));
    const prev = sorted[sorted.length - 2].semester_gpa;
    const curr = sorted[sorted.length - 1].semester_gpa;
    const delta = curr - prev;
    if (Math.abs(delta) < 0.05) return { text: "GPA ổn định so với HK trước", color: "text-blue-600", emoji: "📊" };
    if (delta > 0) return { text: `GPA tăng ${delta.toFixed(1)} so với HK trước`, color: "text-green-600", emoji: "🎉" };
    return { text: `GPA giảm ${Math.abs(delta).toFixed(1)} so với HK trước`, color: "text-orange-500", emoji: "⚠️" };
  })();

  const insights: { text: string; color: string }[] = [];
  if (student.gpa_cumulative >= 3.2) insights.push({ text: "GPA xuất sắc — tiếp tục duy trì!", color: "bg-green-50 text-green-700 border-green-200" });
  else if (student.gpa_cumulative >= 2.5) insights.push({ text: "GPA khá — còn nhiều tiềm năng cải thiện", color: "bg-blue-50 text-blue-700 border-blue-200" });
  else if (student.gpa_cumulative < 2.0) insights.push({ text: "GPA dưới mốc an toàn 2.0 — cần chú ý!", color: "bg-red-50 text-red-700 border-red-200" });
  if (student.warning_level === 0 && student.credits_earned >= 30) insights.push({ text: "Không có cảnh báo học vụ", color: "bg-green-50 text-green-700 border-green-200" });
  if (student.warning_level >= 2) insights.push({ text: "Đang bị cảnh báo — hãy tư vấn ngay!", color: "bg-red-50 text-red-700 border-red-200" });

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-primary">{t("dashboard.title")}</h1>
          <p className="text-muted-foreground text-sm mt-0.5">
            {t("dashboard.greeting")}{" "}
            <span className="font-medium text-foreground">{student.full_name}</span> —{" "}
            {student.mssv}
          </p>
          {gpaInsight && (
            <p className={`text-sm mt-1 font-medium ${gpaInsight.color}`}>
              {gpaInsight.emoji} {gpaInsight.text}
            </p>
          )}
          {insights.length > 0 && (
            <div className="flex flex-wrap gap-1.5 mt-2">
              {insights.map((ins) => (
                <span key={ins.text} className={`text-xs px-2 py-0.5 rounded-full border font-medium ${ins.color}`}>
                  {ins.text}
                </span>
              ))}
            </div>
          )}
        </div>
        <Badge variant={warning.variant}>{t(warning.labelKey)}</Badge>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-5">
        <StatCard
          icon={GraduationCap}
          title={t("dashboard.gpaCumulative")}
          value={student.gpa_cumulative.toFixed(1)}
          sub={t("dashboard.gpaScale")}
          color={student.gpa_cumulative >= 2.0 ? "text-green-600" : "text-destructive"}
        />
        <StatCard
          icon={BookOpen}
          title={t("dashboard.creditsEarned")}
          value={student.credits_earned}
          sub={current_semester ? `${t("dashboard.currentSemester")} ${current_semester}` : undefined}
        />
        <StatCard
          icon={TrendingUp}
          title={t("dashboard.creditsInProgress")}
          value={credits_in_progress}
          sub={t("dashboard.thisSemester")}
        />
        <StatCard
          icon={AlertTriangle}
          title={t("dashboard.failedTotal")}
          value={failed_courses_total}
          color={failed_courses_total > 0 ? "text-destructive" : "text-green-600"}
        />
        <Link href="/student/predictions" className="block">
          <Card className="hover:shadow-md transition-shadow cursor-pointer h-full">
            <CardContent className="pt-6">
              <div className="flex items-start justify-between">
                <div>
                  <p className="text-sm text-muted-foreground">{t("dashboard.aiRisk")}</p>
                  <p
                    className={`text-3xl font-bold mt-1 ${
                      prediction
                        ? RISK_COLOR_BY_LEVEL[prediction.risk_level] ?? "text-foreground"
                        : "text-muted-foreground"
                    }`}
                  >
                    {prediction
                      ? `${(prediction.risk_score * 100).toFixed(0)}%`
                      : t("dashboard.aiRiskNotReady")}
                  </p>
                  <p className="text-xs text-muted-foreground mt-1">
                    {prediction
                      ? t(RISK_LABEL_KEYS[prediction.risk_level])
                      : t("dashboard.aiRiskSub")}
                  </p>
                </div>
                <div className="p-2 rounded-lg bg-primary/10">
                  <Bot className="h-5 w-5 text-primary" />
                </div>
              </div>
            </CardContent>
          </Card>
        </Link>
      </div>

      {/* GPA Chart */}
      {history.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("dashboard.gpaTrend")}</CardTitle>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={220}>
              <AreaChart data={history} margin={{ top: 4, right: 16, left: -16, bottom: 0 }}>
                <defs>
                  <linearGradient id="gpaGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="hsl(var(--primary))" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="hsl(var(--primary))" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis
                  dataKey="semester"
                  tick={{ fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  domain={[0, 4]}
                  ticks={[0, 1, 2, 3, 4]}
                  tick={{ fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                />
                <Tooltip
                  formatter={(v) => [typeof v === "number" ? v.toFixed(1) : v, "GPA"]}
                  labelFormatter={(l) => `${t("dashboard.tableSemester")} ${l}`}
                  contentStyle={{ fontSize: 12 }}
                />
                <Area
                  type="monotone"
                  dataKey="semester_gpa"
                  stroke="hsl(var(--primary))"
                  strokeWidth={2}
                  fill="url(#gpaGradient)"
                  dot={{ r: 4, fill: "hsl(var(--primary))" }}
                  activeDot={{ r: 6 }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>
      )}

      {/* GPA history table */}
      {history.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("dashboard.semesterDetails")}</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-muted-foreground text-left">
                    <th className="pb-2 font-medium">{t("dashboard.tableSemester")}</th>
                    <th className="pb-2 font-medium text-right">{t("dashboard.tableGpa")}</th>
                    <th className="pb-2 font-medium text-right">{t("dashboard.tableCredits")}</th>
                    <th className="pb-2 font-medium text-right">{t("dashboard.tableCourses")}</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {[...history].reverse().map((h) => (
                    <tr key={h.semester} className="hover:bg-muted/30 transition-colors">
                      <td className="py-2 font-medium">{h.semester}</td>
                      <td className={`py-2 text-right font-semibold ${h.semester_gpa >= 2.0 ? "text-green-600" : "text-destructive"}`}>
                        {h.semester_gpa.toFixed(1)}
                      </td>
                      <td className="py-2 text-right">{h.credits_taken}</td>
                      <td className="py-2 text-right">{h.courses_count}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      )}

      {history.length === 0 && (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <GraduationCap className="mx-auto h-10 w-10 mb-3 opacity-30" />
            <p>{t("dashboard.empty.title")}</p>
            <p className="text-sm mt-1">{t("dashboard.empty.cta")}</p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
