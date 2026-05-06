"use client";

import { useEffect, useState } from "react";
import {
  AlertTriangle,
  BarChart3,
  Bot,
  CheckCircle2,
  Download,
  FileText,
  GraduationCap,
  TrendingUp,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { adminApi, type AdminStatistics } from "@/lib/api";
import { useT } from "@/lib/i18n";

const BLUE = "#16358f";
const GREEN = "#43a65a";
const RED = "#e4574f";
const AMBER = "#c98a2c";
const CYAN = "#2d8ac7";
const GRAY = "#98a2b3";
const RISK_COLORS: Record<string, string> = {
  none: GRAY,
  low: GREEN,
  medium: AMBER,
  high: "#e46f38",
  critical: RED,
};

type ReportType = "warnings" | "gpa" | "ai";
type ExportFormat = "pdf" | "xlsx";

export default function AdminReportsPage() {
  const t = useT();
  const [stats, setStats] = useState<AdminStatistics | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState<string | null>(null);

  useEffect(() => {
    adminApi
      .statistics()
      .then((r) => setStats(r.data))
      .catch(() => setError("Không tải được thống kê"))
      .finally(() => setLoading(false));
  }, []);

  const handleExport = async (reportType: ReportType, format: ExportFormat) => {
    const key = `${reportType}-${format}`;
    setExporting(key);
    try {
      const response = await adminApi.exportReport(reportType, format);
      const disposition = response.headers["content-disposition"];
      const filename = filenameFromDisposition(disposition)
        ?? `${reportType}_report.${format === "xlsx" ? "xlsx" : "pdf"}`;
      downloadBlob(response.data, filename);
    } catch {
      alert(t("adminReports.exportError"));
    } finally {
      setExporting(null);
    }
  };

  if (loading) return <div className="text-muted-foreground animate-pulse">{t("common.loading")}</div>;
  if (error || !stats) return <div className="rounded-md bg-destructive/10 text-destructive px-4 py-3">{error}</div>;

  const warningChart = stats.by_semester.map((s) => ({
    name: `HK ${s.semester}`,
    count: s.count,
  }));
  const gpaChart = stats.gpa_distribution.map((g) => ({
    name: g.bucket,
    count: g.count,
  }));
  const riskChart = stats.risk_distribution.filter((r) => r.count > 0);
  const latestPassFail = stats.latest_pass_fail.filter((i) => i.count > 0);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-primary">{t("adminReports.title")}</h1>
        <p className="text-muted-foreground text-sm mt-0.5">{t("adminReports.subtitle")}</p>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard icon={GraduationCap} label={t("adminReports.gpaAvg")} value={stats.gpa_average.toFixed(2)} />
        <StatCard
          icon={AlertTriangle}
          label={t("adminReports.warnRate")}
          value={`${stats.warning_rate_pct}%`}
          color={stats.warning_rate_pct > 10 ? "text-destructive" : "text-orange-500"}
        />
        <StatCard
          icon={TrendingUp}
          label={t("adminReports.improveRate")}
          value={stats.improvement_rate_pct !== null ? `${stats.improvement_rate_pct}%` : "—"}
          color="text-green-600"
        />
        <StatCard
          icon={CheckCircle2}
          label={t("adminReports.passRate")}
          value={stats.pass_rate_pct !== null ? `${stats.pass_rate_pct}%` : "—"}
          color="text-green-600"
        />
      </div>

      <div className="grid gap-4 xl:grid-cols-2">
        <ChartCard
          title={t("adminReports.bySemester")}
          subtitle={stats.semester_now ? `HK hiện tại: ${stats.semester_now}` : t("adminReports.semesters")}
        >
          {warningChart.length === 0 ? (
            <NoData />
          ) : (
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={warningChart} margin={{ top: 8, right: 12, left: -18, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e4e7ec" />
                <XAxis dataKey="name" tickLine={false} axisLine={false} fontSize={12} />
                <YAxis allowDecimals={false} tickLine={false} axisLine={false} fontSize={12} />
                <Tooltip cursor={{ fill: "#eef3ff" }} />
                <Bar dataKey="count" name="Số cảnh báo" fill={BLUE} radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </ChartCard>

        <ChartCard
          title={t("adminReports.gpaDistribution")}
          subtitle={`N = ${stats.total_students}`}
        >
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={gpaChart} margin={{ top: 8, right: 12, left: -18, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#e4e7ec" />
              <XAxis dataKey="name" tickLine={false} axisLine={false} fontSize={12} />
              <YAxis allowDecimals={false} tickLine={false} axisLine={false} fontSize={12} />
              <Tooltip cursor={{ fill: "#f7f9fc" }} />
              <Bar dataKey="count" name="Số sinh viên" radius={[6, 6, 0, 0]}>
                {gpaChart.map((_, index) => (
                  <Cell key={index} fill={[RED, "#e46f38", AMBER, CYAN, GREEN, "#1d8f64"][index] ?? BLUE} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartCard>

        <ChartCard
          title={t("adminReports.riskDistribution")}
          subtitle={`${stats.total_high_risk} SV risk cao · ${stats.total_critical} nghiêm trọng`}
        >
          <div className="grid gap-4 md:grid-cols-[240px_1fr] items-center">
            {riskChart.length === 0 ? (
              <NoData />
            ) : (
              <ResponsiveContainer width="100%" height={240}>
                <PieChart>
                  <Pie data={riskChart} dataKey="count" nameKey="label_vi" innerRadius={62} outerRadius={92} paddingAngle={2}>
                    {riskChart.map((item) => (
                      <Cell key={item.bucket} fill={RISK_COLORS[item.bucket] ?? BLUE} />
                    ))}
                  </Pie>
                  <Tooltip />
                </PieChart>
              </ResponsiveContainer>
            )}
            <div className="space-y-2">
              {stats.risk_distribution.map((item) => (
                <LegendRow
                  key={item.bucket}
                  color={RISK_COLORS[item.bucket] ?? BLUE}
                  label={item.label_vi}
                  value={`${item.count} (${item.pct}%)`}
                />
              ))}
            </div>
          </div>
        </ChartCard>

        <ChartCard
          title={t("adminReports.facultyWarning")}
          subtitle={t("adminReports.facultyWarningSubtitle")}
        >
          <FacultyBars stats={stats} />
        </ChartCard>
      </div>

      {latestPassFail.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{t("adminReports.latestPassFail")}</CardTitle>
            <p className="text-xs text-muted-foreground">HK {stats.semester_now}</p>
          </CardHeader>
          <CardContent>
            <div className="h-5 overflow-hidden rounded-full bg-muted flex">
              {latestPassFail.map((item) => (
                <div
                  key={item.status}
                  className={item.status === "passed" ? "bg-green-500" : "bg-red-500"}
                  style={{ width: `${item.pct}%` }}
                  title={`${item.label}: ${item.count}`}
                />
              ))}
            </div>
            <div className="mt-3 flex gap-4 text-sm text-muted-foreground">
              {latestPassFail.map((item) => (
                <LegendRow
                  key={item.status}
                  color={item.status === "passed" ? GREEN : RED}
                  label={item.label}
                  value={`${item.count} (${item.pct}%)`}
                />
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("adminReports.exportTitle")}</CardTitle>
          <p className="text-xs text-muted-foreground">{t("adminReports.exportHint")}</p>
        </CardHeader>
        <CardContent className="grid gap-3 md:grid-cols-3">
          <ExportPanel
            icon={FileText}
            title={t("adminReports.export.warnings")}
            description={t("adminReports.export.warningsDesc")}
            busyKey={exporting}
            reportType="warnings"
            onExport={handleExport}
          />
          <ExportPanel
            icon={BarChart3}
            title={t("adminReports.export.gpa")}
            description={t("adminReports.export.gpaDesc")}
            busyKey={exporting}
            reportType="gpa"
            onExport={handleExport}
          />
          <ExportPanel
            icon={Bot}
            title={t("adminReports.export.ai")}
            description={t("adminReports.export.aiDesc")}
            busyKey={exporting}
            reportType="ai"
            onExport={handleExport}
          />
        </CardContent>
      </Card>
    </div>
  );
}

function StatCard({
  icon: Icon, label, value, color,
}: {
  icon: React.ElementType;
  label: string;
  value: string;
  color?: string;
}) {
  return (
    <Card>
      <CardContent className="pt-6">
        <div className="flex items-start justify-between">
          <div>
            <p className="text-sm text-muted-foreground">{label}</p>
            <p className={`text-3xl font-bold mt-1 ${color ?? "text-foreground"}`}>{value}</p>
          </div>
          <div className="p-2 rounded-lg bg-primary/10">
            <Icon className="h-5 w-5 text-primary" />
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

function ChartCard({
  title,
  subtitle,
  children,
}: {
  title: string;
  subtitle: string;
  children: React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">{title}</CardTitle>
        <p className="text-xs text-muted-foreground">{subtitle}</p>
      </CardHeader>
      <CardContent>{children}</CardContent>
    </Card>
  );
}

function FacultyBars({ stats }: { stats: AdminStatistics }) {
  const maxPct = Math.max(...stats.by_faculty.map((f) => f.pct), 1);
  if (stats.by_faculty.length === 0) return <NoData />;

  return (
    <div className="space-y-3">
      {stats.by_faculty.map((faculty) => (
        <div key={faculty.faculty} className="space-y-1.5">
          <div className="flex items-center justify-between gap-3 text-sm">
            <span className="truncate font-medium">{faculty.faculty}</span>
            <span className="text-muted-foreground shrink-0">
              {faculty.warning_count}/{faculty.total_students} · {faculty.pct}%
            </span>
          </div>
          <div className="h-2.5 rounded-full bg-muted overflow-hidden">
            <div
              className="h-full rounded-full bg-primary"
              style={{ width: `${Math.max(4, (faculty.pct / maxPct) * 100)}%` }}
            />
          </div>
        </div>
      ))}
    </div>
  );
}

function LegendRow({ color, label, value }: { color: string; label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-3">
      <span className="inline-flex items-center gap-2 min-w-0">
        <span className="h-2.5 w-2.5 rounded-full shrink-0" style={{ backgroundColor: color }} />
        <span className="truncate">{label}</span>
      </span>
      <span className="font-medium text-foreground shrink-0">{value}</span>
    </div>
  );
}

function NoData() {
  return <p className="text-sm text-muted-foreground py-16 text-center">—</p>;
}

function ExportPanel({
  icon: Icon,
  title,
  description,
  reportType,
  busyKey,
  onExport,
}: {
  icon: React.ElementType;
  title: string;
  description: string;
  reportType: ReportType;
  busyKey: string | null;
  onExport: (reportType: ReportType, format: ExportFormat) => void;
}) {
  const t = useT();
  const pdfKey = `${reportType}-pdf`;
  const xlsxKey = `${reportType}-xlsx`;

  return (
    <div className="rounded-lg border bg-muted/15 p-5 space-y-3">
      <Icon className="h-6 w-6 text-primary" />
      <div>
        <p className="font-medium text-sm">{title}</p>
        <p className="text-xs text-muted-foreground mt-1">{description}</p>
      </div>
      <div className="flex gap-2 pt-1">
        <Button size="sm" variant="outline" disabled={!!busyKey} onClick={() => onExport(reportType, "pdf")}>
          <Download className="h-3.5 w-3.5 mr-1" />
          {busyKey === pdfKey ? t("common.loading") : t("adminReports.exportPdf")}
        </Button>
        <Button size="sm" variant="outline" disabled={!!busyKey} onClick={() => onExport(reportType, "xlsx")}>
          <Download className="h-3.5 w-3.5 mr-1" />
          {busyKey === xlsxKey ? t("common.loading") : t("adminReports.exportExcel")}
        </Button>
      </div>
    </div>
  );
}

function filenameFromDisposition(disposition?: string): string | null {
  if (!disposition) return null;
  const match = /filename="?([^"]+)"?/i.exec(disposition);
  return match?.[1] ?? null;
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(url);
}
