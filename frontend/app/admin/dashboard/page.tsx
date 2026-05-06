"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { Users, AlertTriangle, AlertOctagon, Flame } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { adminApi, type AdminDashboardStats } from "@/lib/api";
import { useT } from "@/lib/i18n";

const RISK_COLOR: Record<string, string> = {
  low: "bg-green-500",
  medium: "bg-yellow-500",
  high: "bg-orange-500",
  critical: "bg-red-600",
};

const FACULTY_COLOR = ["bg-red-500", "bg-orange-500", "bg-yellow-500", "bg-blue-500", "bg-green-500"];

export default function AdminDashboardPage() {
  const t = useT();
  const [data, setData] = useState<AdminDashboardStats | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    adminApi
      .dashboard()
      .then((r) => setData(r.data))
      .catch(() => setError("Không tải được dashboard"))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="text-muted-foreground animate-pulse">{t("common.loading")}</div>;
  if (error || !data) return <div className="rounded-md bg-destructive/10 text-destructive px-4 py-3">{error}</div>;

  const totalRisk = data.by_risk_level.reduce((s, b) => s + b.count, 0) || 1;
  const totalFacultyMax = Math.max(...data.by_faculty.map((f) => f.warning_count), 1);
  const updatedAt = new Date(data.generated_at).toLocaleString("vi-VN");

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-primary">{t("adminDash.title")}</h1>
        <p className="text-muted-foreground text-sm mt-0.5">
          {t("adminDash.subtitle")} {updatedAt}
        </p>
      </div>

      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard icon={Users} label={t("adminDash.totalStudents")} value={data.total_students} />
        <StatCard icon={AlertTriangle} label={t("adminDash.totalWarned")} value={data.total_warned} color="text-orange-600" />
        <StatCard icon={AlertOctagon} label={t("adminDash.highRisk")} value={data.total_high_risk} color="text-orange-500" />
        <StatCard icon={Flame} label={t("adminDash.critical")} value={data.total_critical} color="text-destructive" />
      </div>

      {data.total_students === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <Users className="mx-auto h-10 w-10 mb-3 opacity-30" />
            <p>{t("adminDash.empty")}</p>
            <Link href="/admin/import" className="text-primary text-sm font-medium mt-2 inline-block">
              → {t("adminNav.import")}
            </Link>
          </CardContent>
        </Card>
      ) : (
        <>
          <div className="grid gap-4 lg:grid-cols-2">
            <Card>
              <CardHeader>
                <CardTitle className="text-base">{t("adminDash.riskDistribution")}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {data.by_risk_level.map((b) => {
                  const pct = (b.count / totalRisk) * 100;
                  return (
                    <div key={b.bucket}>
                      <div className="flex justify-between text-sm mb-1">
                        <span>{b.label_vi}</span>
                        <span className="font-medium">{b.count} SV</span>
                      </div>
                      <div className="h-2 bg-muted rounded-full overflow-hidden">
                        <div className={`h-full ${RISK_COLOR[b.bucket]}`} style={{ width: `${pct}%` }} />
                      </div>
                    </div>
                  );
                })}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="text-base">{t("adminDash.byFaculty")}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {data.by_faculty.length === 0 ? (
                  <p className="text-sm text-muted-foreground py-4 text-center">—</p>
                ) : (
                  data.by_faculty.slice(0, 5).map((f, i) => {
                    const pct = (f.warning_count / totalFacultyMax) * 100;
                    return (
                      <div key={f.faculty}>
                        <div className="flex justify-between text-sm mb-1">
                          <span className="truncate pr-2">{f.faculty}</span>
                          <span className="font-medium shrink-0">
                            {f.pct}% ({f.warning_count})
                          </span>
                        </div>
                        <div className="h-2 bg-muted rounded-full overflow-hidden">
                          <div className={`h-full ${FACULTY_COLOR[i % FACULTY_COLOR.length]}`} style={{ width: `${pct}%` }} />
                        </div>
                      </div>
                    );
                  })
                )}
              </CardContent>
            </Card>
          </div>

          <Card>
            <CardHeader className="flex-row items-center justify-between space-y-0">
              <CardTitle className="text-base">{t("adminDash.topRisk")}</CardTitle>
              <Link href="/admin/students?high_risk=1" className="text-sm text-primary">
                {t("adminDash.viewAll")}
              </Link>
            </CardHeader>
            <CardContent>
              {data.top_risk.length === 0 ? (
                <p className="text-sm text-muted-foreground py-4 text-center">—</p>
              ) : (
                <div className="divide-y">
                  {data.top_risk.map((s, i) => (
                    <Link
                      key={s.student_id}
                      href={`/admin/students/${s.student_id}`}
                      className="flex items-center justify-between py-3 hover:bg-muted/30 px-2 rounded-md"
                    >
                      <div className="flex items-center gap-3 min-w-0">
                        <span className="w-6 h-6 rounded-full bg-muted text-xs flex items-center justify-center font-medium shrink-0">
                          {i + 1}
                        </span>
                        <div className="min-w-0">
                          <p className="text-sm font-medium truncate">{s.full_name}</p>
                          <p className="text-xs text-muted-foreground">
                            {s.mssv} · {s.faculty} · GPA {s.gpa_cumulative.toFixed(2)}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2 shrink-0">
                        {s.warning_level >= 1 && (
                          <Badge variant={s.warning_level >= 2 ? "destructive" : "secondary"}>
                            {s.warning_level === 3 ? "Buộc thôi học" : `Mức ${s.warning_level}`}
                          </Badge>
                        )}
                        {s.risk_score !== null && (
                          <span className="font-bold text-destructive text-sm">
                            {(s.risk_score * 100).toFixed(0)}%
                          </span>
                        )}
                      </div>
                    </Link>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </>
      )}
    </div>
  );
}

function StatCard({
  icon: Icon, label, value, color,
}: {
  icon: React.ElementType;
  label: string;
  value: number;
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
