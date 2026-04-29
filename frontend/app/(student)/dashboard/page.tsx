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
import { GraduationCap, BookOpen, AlertTriangle, TrendingUp } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { studentApi, type DashboardData, type GpaHistoryEntry } from "@/lib/api";

const WARNING_LABELS: Record<number, { label: string; variant: "default" | "secondary" | "destructive" }> = {
  0: { label: "Bình thường", variant: "default" },
  1: { label: "Cảnh báo mức 1", variant: "secondary" },
  2: { label: "Cảnh báo mức 2", variant: "destructive" },
  3: { label: "Buộc thôi học", variant: "destructive" },
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
  const [dashboard, setDashboard] = useState<DashboardData | null>(null);
  const [history, setHistory] = useState<GpaHistoryEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([studentApi.dashboard(), studentApi.gpaHistory()])
      .then(([d, h]) => {
        setDashboard(d.data);
        setHistory(h.data);
      })
      .catch(() => setError("Không thể tải dữ liệu. Vui lòng thử lại."))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-muted-foreground animate-pulse">Đang tải...</div>
      </div>
    );
  }

  if (error || !dashboard) {
    return (
      <div className="rounded-md bg-destructive/10 text-destructive px-4 py-3">
        {error ?? "Lỗi không xác định"}
      </div>
    );
  }

  const { student, current_semester, credits_in_progress, failed_courses_total } = dashboard;
  const warning = WARNING_LABELS[student.warning_level] ?? WARNING_LABELS[0];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-primary">Tổng quan</h1>
          <p className="text-muted-foreground text-sm mt-0.5">
            Xin chào, <span className="font-medium text-foreground">{student.full_name}</span> —{" "}
            {student.mssv}
          </p>
        </div>
        <Badge variant={warning.variant}>{warning.label}</Badge>
      </div>

      {/* Stat cards */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          icon={GraduationCap}
          title="GPA Tích lũy"
          value={student.gpa_cumulative.toFixed(2)}
          sub="Thang điểm 4"
          color={student.gpa_cumulative >= 2.0 ? "text-green-600" : "text-destructive"}
        />
        <StatCard
          icon={BookOpen}
          title="Tín chỉ tích lũy"
          value={student.credits_earned}
          sub={current_semester ? `HK hiện tại: ${current_semester}` : undefined}
        />
        <StatCard
          icon={TrendingUp}
          title="TC đang học"
          value={credits_in_progress}
          sub="Học kỳ này"
        />
        <StatCard
          icon={AlertTriangle}
          title="Môn rớt (tổng)"
          value={failed_courses_total}
          color={failed_courses_total > 0 ? "text-destructive" : "text-green-600"}
        />
      </div>

      {/* GPA Chart */}
      {history.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Xu hướng GPA theo học kỳ</CardTitle>
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
                  formatter={(v) => [typeof v === "number" ? v.toFixed(2) : v, "GPA"]}
                  labelFormatter={(l) => `Học kỳ ${l}`}
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
            <CardTitle className="text-base">Chi tiết từng học kỳ</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-muted-foreground text-left">
                    <th className="pb-2 font-medium">Học kỳ</th>
                    <th className="pb-2 font-medium text-right">GPA HK</th>
                    <th className="pb-2 font-medium text-right">TC đã học</th>
                    <th className="pb-2 font-medium text-right">Số môn</th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {[...history].reverse().map((h) => (
                    <tr key={h.semester} className="hover:bg-muted/30 transition-colors">
                      <td className="py-2 font-medium">{h.semester}</td>
                      <td className={`py-2 text-right font-semibold ${h.semester_gpa >= 2.0 ? "text-green-600" : "text-destructive"}`}>
                        {h.semester_gpa.toFixed(2)}
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
            <p>Chưa có dữ liệu điểm.</p>
            <p className="text-sm mt-1">
              Vào trang <strong>Bảng điểm</strong> để nhập điểm từ myBK hoặc tự nhập thủ công.
            </p>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
