"use client";

import { useEffect, useState } from "react";
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  RadialBarChart, RadialBar, PolarAngleAxis,
} from "recharts";
import { AlertTriangle, RefreshCw, TrendingDown, TrendingUp } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  predictionsApi,
  type PredictionResponse,
  type PredictionHistoryEntry,
  type RiskFactor,
} from "@/lib/api";
import { useT, type TKey } from "@/lib/i18n";

// ─── Helpers ─────────────────────────────────────────────────

const RISK_COLOR: Record<string, string> = {
  low:      "#16a34a", // green
  medium:   "#eab308", // yellow
  high:     "#f97316", // orange
  critical: "#dc2626", // red
};

const RISK_LABEL_KEYS: Record<string, TKey> = {
  low:      "predictions.riskLevel.low",
  medium:   "predictions.riskLevel.medium",
  high:     "predictions.riskLevel.high",
  critical: "predictions.riskLevel.critical",
};

const RISK_BADGE_VARIANTS: Record<string, "default" | "secondary" | "destructive"> = {
  low:      "default",
  medium:   "secondary",
  high:     "destructive",
  critical: "destructive",
};

// ─── Risk Gauge ──────────────────────────────────────────────

function RiskGauge({ score, level, label }: { score: number; level: string; label: string }) {
  const t = useT();
  const color = RISK_COLOR[level] ?? "#6b7280";
  const data = [{ name: "risk", value: score * 100, fill: color }];

  return (
    <div className="relative w-full max-w-sm mx-auto">
      <ResponsiveContainer width="100%" height={260}>
        <RadialBarChart
          innerRadius="70%" outerRadius="100%"
          data={data} startAngle={225} endAngle={-45}
        >
          <PolarAngleAxis type="number" domain={[0, 100]} angleAxisId={0} tick={false} />
          <RadialBar background dataKey="value" cornerRadius={10} fill={color} />
        </RadialBarChart>
      </ResponsiveContainer>
      <div className="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
        <div className="text-5xl font-bold" style={{ color }}>
          {(score * 100).toFixed(0)}%
        </div>
        <div className="text-sm text-muted-foreground mt-1">{t("predictions.riskScore")}</div>
        <Badge variant={RISK_BADGE_VARIANTS[level] ?? "default"} className="mt-2">
          {label}
        </Badge>
      </div>
    </div>
  );
}

// ─── Risk Factor Bar ─────────────────────────────────────────

function FactorBar({ factor }: { factor: RiskFactor }) {
  const isPositive = factor.direction === "+";
  const widthPct = Math.min(100, factor.impact * 100);
  const Icon = isPositive ? TrendingUp : TrendingDown;
  const colorClass = isPositive ? "text-destructive" : "text-green-600";
  const bgColorClass = isPositive ? "bg-destructive/80" : "bg-green-600/80";

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between gap-2 text-sm">
        <div className="flex items-center gap-1.5 truncate">
          <Icon className={`h-3.5 w-3.5 shrink-0 ${colorClass}`} />
          <span className="truncate">{factor.label}</span>
        </div>
        <span className={`font-semibold shrink-0 ${colorClass}`}>{factor.impact_str}</span>
      </div>
      <div className="h-2 bg-muted rounded-full overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${bgColorClass}`}
          style={{ width: `${widthPct}%` }}
        />
      </div>
    </div>
  );
}

// ─── Course Pass Prediction ──────────────────────────────────

function CourseRow({ course }: { course: { course_code: string; course_name: string; credits: number; pass_probability: number } }) {
  const t = useT();
  const pct = course.pass_probability * 100;
  const color = pct >= 70 ? "text-green-600" : pct >= 50 ? "text-yellow-600" : "text-destructive";
  const bg = pct >= 70 ? "bg-green-600" : pct >= 50 ? "bg-yellow-500" : "bg-destructive";

  return (
    <div className="flex items-center gap-3 py-2 border-b last:border-0">
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2">
          <span className="font-mono text-xs text-muted-foreground">{course.course_code}</span>
          <span className="text-xs text-muted-foreground">· {course.credits} TC</span>
        </div>
        <p className="text-sm font-medium truncate">{course.course_name}</p>
      </div>
      <div className="w-32 shrink-0">
        <div className="flex justify-between text-xs mb-0.5">
          <span className="text-muted-foreground">{t("predictions.coursePassProb")}</span>
          <span className={`font-bold ${color}`}>{pct.toFixed(0)}%</span>
        </div>
        <div className="h-1.5 bg-muted rounded-full overflow-hidden">
          <div className={`h-full ${bg}`} style={{ width: `${pct}%` }} />
        </div>
      </div>
    </div>
  );
}

// ─── Main Page ───────────────────────────────────────────────

export default function PredictionsPage() {
  const t = useT();
  const [pred, setPred] = useState<PredictionResponse | null>(null);
  const [history, setHistory] = useState<PredictionHistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const load = async () => {
    setLoading(true);
    setError(null);
    try {
      const [predRes, histRes] = await Promise.all([
        predictionsApi.me(),
        predictionsApi.history(30),
      ]);
      setPred(predRes.data);
      setHistory(histRes.data);
    } catch (e: unknown) {
      const status = (e as { response?: { status?: number } })?.response?.status;
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      if (status === 503) {
        setError(t("predictions.empty.notReady"));
      } else if (status === 422) {
        setError(t("predictions.empty.cta"));
      } else {
        setError(msg ?? t("common.unknownError"));
      }
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    try {
      const res = await predictionsApi.refresh();
      setPred(res.data);
      const hist = await predictionsApi.history(30);
      setHistory(hist.data);
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? t("common.unknownError"));
    } finally {
      setRefreshing(false);
    }
  };

  useEffect(() => { load(); /* eslint-disable-next-line react-hooks/exhaustive-deps */ }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-muted-foreground animate-pulse">{t("common.loading")}</div>
      </div>
    );
  }

  if (error || !pred) {
    return (
      <div className="space-y-6">
        <div>
          <h1 className="text-2xl font-bold text-primary">{t("predictions.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("predictions.subtitle")}</p>
        </div>
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground space-y-3">
            <AlertTriangle className="mx-auto h-10 w-10 opacity-30" />
            <p className="font-medium text-foreground">{t("predictions.empty.title")}</p>
            <p className="text-sm">{error ?? t("predictions.empty.cta")}</p>
          </CardContent>
        </Card>
      </div>
    );
  }

  const levelLabel = t(RISK_LABEL_KEYS[pred.risk_level]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-start justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-2xl font-bold text-primary">{t("predictions.title")}</h1>
          <p className="text-sm text-muted-foreground">{t("predictions.subtitle")}</p>
          {pred.created_at && (
            <p className="text-xs text-muted-foreground mt-1">
              {t("predictions.lastUpdate")} {new Date(pred.created_at).toLocaleString("vi-VN")}
            </p>
          )}
        </div>
        <Button size="sm" variant="outline" onClick={handleRefresh} disabled={refreshing}>
          <RefreshCw className={`h-4 w-4 mr-1 ${refreshing ? "animate-spin" : ""}`} />
          {refreshing ? t("predictions.refreshing") : t("predictions.refresh")}
        </Button>
      </div>

      {/* Risk gauge + Factors side by side */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card className="lg:col-span-1">
          <CardHeader>
            <CardTitle className="text-base">{t("predictions.semester")} {pred.semester}</CardTitle>
          </CardHeader>
          <CardContent>
            <RiskGauge score={pred.risk_score} level={pred.risk_level} label={levelLabel} />
          </CardContent>
        </Card>

        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">{t("predictions.factorsTitle")}</CardTitle>
            <CardDescription className="text-xs">{t("predictions.factorsHint")}</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            {pred.risk_factors.length === 0 ? (
              <p className="text-sm text-muted-foreground italic">—</p>
            ) : (
              pred.risk_factors.map((f, i) => <FactorBar key={i} factor={f} />)
            )}
          </CardContent>
        </Card>
      </div>

      {/* Course predictions */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("predictions.coursesTitle")}</CardTitle>
        </CardHeader>
        <CardContent>
          {pred.predicted_courses.length === 0 ? (
            <p className="text-sm text-muted-foreground italic">{t("predictions.coursesEmpty")}</p>
          ) : (
            <div>
              {pred.predicted_courses.map((c) => (
                <CourseRow key={c.course_id} course={c} />
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* History chart */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("predictions.historyTitle")}</CardTitle>
        </CardHeader>
        <CardContent>
          {history.length < 2 ? (
            <p className="text-sm text-muted-foreground italic py-4 text-center">
              {t("predictions.historyEmpty")}
            </p>
          ) : (
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart
                data={history.map((h) => ({
                  ...h,
                  date: h.created_at
                    ? new Date(h.created_at).toLocaleDateString("vi-VN", { day: "2-digit", month: "2-digit" })
                    : "",
                  risk_pct: h.risk_score * 100,
                }))}
                margin={{ top: 4, right: 16, left: -16, bottom: 0 }}
              >
                <defs>
                  <linearGradient id="riskGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#dc2626" stopOpacity={0.4} />
                    <stop offset="95%" stopColor="#dc2626" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" className="stroke-muted" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} tickLine={false} axisLine={false} />
                <YAxis
                  domain={[0, 100]}
                  ticks={[0, 25, 50, 75, 100]}
                  tick={{ fontSize: 11 }}
                  tickLine={false}
                  axisLine={false}
                  unit="%"
                />
                <Tooltip
                  formatter={(v) => [typeof v === "number" ? `${v.toFixed(1)}%` : v, "Risk"]}
                  contentStyle={{ fontSize: 12 }}
                />
                <Area
                  type="monotone"
                  dataKey="risk_pct"
                  stroke="#dc2626"
                  strokeWidth={2}
                  fill="url(#riskGradient)"
                  dot={{ r: 3, fill: "#dc2626" }}
                />
              </AreaChart>
            </ResponsiveContainer>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
