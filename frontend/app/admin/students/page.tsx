"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Search } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { adminApi, type AdminStudentListItem } from "@/lib/api";
import { useT } from "@/lib/i18n";

const PAGE_SIZE = 20;

const RISK_COLOR_TEXT: Record<string, string> = {
  low: "text-green-600",
  medium: "text-yellow-600",
  high: "text-orange-500",
  critical: "text-destructive",
};

function warningLabel(level: number): { text: string; variant: "default" | "secondary" | "destructive" } {
  if (level === 0) return { text: "Bình thường", variant: "default" };
  if (level === 1) return { text: "Mức 1", variant: "secondary" };
  if (level === 2) return { text: "Mức 2", variant: "destructive" };
  return { text: "Buộc thôi học", variant: "destructive" };
}

export default function AdminStudentsPage() {
  const t = useT();
  const sp = useSearchParams();
  const initialHighRisk = sp.get("high_risk") === "1";

  const [items, setItems] = useState<AdminStudentListItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [q, setQ] = useState("");
  const [warningFilter, setWarningFilter] = useState<"all" | "warned" | "high_risk">(
    initialHighRisk ? "high_risk" : "all"
  );
  const [page, setPage] = useState(1);

  const params = useMemo(() => {
    const p: Parameters<typeof adminApi.listStudents>[0] = { page, size: PAGE_SIZE };
    if (q.trim()) p.q = q.trim();
    if (warningFilter === "warned") p.warning_level = 1;
    if (warningFilter === "high_risk") p.high_risk = true;
    return p;
  }, [q, warningFilter, page]);

  useEffect(() => {
    setLoading(true);
    setError(null);
    adminApi
      .listStudents(params)
      .then((r) => {
        setItems(r.data.items);
        setTotal(r.data.total);
      })
      .catch(() => setError("Không tải được danh sách"))
      .finally(() => setLoading(false));
  }, [params]);

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-primary">{t("adminStudents.title")}</h1>
          <p className="text-muted-foreground text-sm mt-0.5">{t("adminStudents.subtitle")}</p>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="pt-6 space-y-3">
          <div className="flex items-center gap-2">
            <Search className="h-4 w-4 text-muted-foreground shrink-0" />
            <Input
              placeholder={t("adminStudents.search")}
              value={q}
              onChange={(e) => { setPage(1); setQ(e.target.value); }}
            />
          </div>
          <div className="flex flex-wrap gap-2">
            <Button
              variant={warningFilter === "all" ? "default" : "outline"}
              size="sm"
              onClick={() => { setPage(1); setWarningFilter("all"); }}
            >
              {t("adminStudents.filterAll")}
            </Button>
            <Button
              variant={warningFilter === "warned" ? "default" : "outline"}
              size="sm"
              onClick={() => { setPage(1); setWarningFilter("warned"); }}
            >
              ≥ Mức 1
            </Button>
            <Button
              variant={warningFilter === "high_risk" ? "default" : "outline"}
              size="sm"
              onClick={() => { setPage(1); setWarningFilter("high_risk"); }}
            >
              {t("adminStudents.filterHighRisk")}
            </Button>
          </div>
        </CardContent>
      </Card>

      {loading ? (
        <div className="text-muted-foreground animate-pulse">{t("common.loading")}</div>
      ) : error ? (
        <div className="rounded-md bg-destructive/10 text-destructive px-4 py-3">{error}</div>
      ) : items.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            {t("adminStudents.empty")}
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b bg-muted/30">
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">{t("adminStudents.col.mssv")}</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">{t("adminStudents.col.name")}</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">{t("adminStudents.col.faculty")}</th>
                    <th className="px-4 py-3 text-right font-medium text-muted-foreground">{t("adminStudents.col.gpa")}</th>
                    <th className="px-4 py-3 text-right font-medium text-muted-foreground">{t("adminStudents.col.risk")}</th>
                    <th className="px-4 py-3 text-left font-medium text-muted-foreground">{t("adminStudents.col.warning")}</th>
                    <th className="px-4 py-3"></th>
                  </tr>
                </thead>
                <tbody className="divide-y">
                  {items.map((s) => {
                    const w = warningLabel(s.warning_level);
                    return (
                      <tr key={s.student_id} className="hover:bg-muted/30">
                        <td className="px-4 py-3 font-mono text-xs">{s.mssv}</td>
                        <td className="px-4 py-3 font-medium">{s.full_name}</td>
                        <td className="px-4 py-3 text-muted-foreground">{s.faculty}</td>
                        <td className={`px-4 py-3 text-right font-semibold ${s.gpa_cumulative >= 2.0 ? "text-foreground" : "text-destructive"}`}>
                          {s.gpa_cumulative.toFixed(2)}
                        </td>
                        <td className="px-4 py-3 text-right">
                          {s.risk_score === null ? (
                            <span className="text-muted-foreground">—</span>
                          ) : (
                            <span className={`font-semibold ${RISK_COLOR_TEXT[s.risk_level ?? "low"] ?? ""}`}>
                              {(s.risk_score * 100).toFixed(0)}%
                            </span>
                          )}
                        </td>
                        <td className="px-4 py-3">
                          <Badge variant={w.variant}>{w.text}</Badge>
                        </td>
                        <td className="px-4 py-3 text-right">
                          <Link href={`/admin/students/${s.student_id}`}>
                            <Button size="sm" variant="outline">{t("adminStudents.detail")}</Button>
                          </Link>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>

            {totalPages > 1 && (
              <div className="flex items-center justify-between gap-3 px-4 py-3 border-t text-sm">
                <span className="text-muted-foreground">
                  {(page - 1) * PAGE_SIZE + 1} – {Math.min(page * PAGE_SIZE, total)} / {total}
                </span>
                <div className="flex gap-1">
                  <Button size="sm" variant="outline" disabled={page === 1} onClick={() => setPage(page - 1)}>
                    ←
                  </Button>
                  <span className="px-3 py-1.5 text-sm font-medium">
                    {page} / {totalPages}
                  </span>
                  <Button size="sm" variant="outline" disabled={page >= totalPages} onClick={() => setPage(page + 1)}>
                    →
                  </Button>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}
    </div>
  );
}
