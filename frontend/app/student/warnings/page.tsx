"use client";

import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, CheckCircle2, Bot, ShieldAlert } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { warningsApi, type WarningResponse } from "@/lib/api";
import { useT, type TKey } from "@/lib/i18n";

const LEVEL_BADGE: Record<number, { variant: "default" | "secondary" | "destructive"; labelKey: TKey }> = {
  1: { variant: "secondary",   labelKey: "warnings.level.1" },
  2: { variant: "destructive", labelKey: "warnings.level.2" },
  3: { variant: "destructive", labelKey: "warnings.level.3" },
};

const LEVEL_BORDER: Record<number, string> = {
  1: "border-l-yellow-500",
  2: "border-l-orange-500",
  3: "border-l-red-600",
};

type Filter = "all" | "unresolved" | "resolved";

export default function WarningsPage() {
  const t = useT();
  const [warnings, setWarnings] = useState<WarningResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filter, setFilter] = useState<Filter>("all");
  const [busyId, setBusyId] = useState<string | null>(null);

  useEffect(() => {
    warningsApi
      .list()
      .then((r) => setWarnings(r.data))
      .catch(() => setError(t("warnings.loadError")))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const filtered = useMemo(() => {
    return warnings.filter((w) => {
      if (filter === "unresolved") return !w.is_resolved;
      if (filter === "resolved") return w.is_resolved;
      return true;
    });
  }, [warnings, filter]);

  const stats = useMemo(() => {
    const total = warnings.length;
    const unresolved = warnings.filter((w) => !w.is_resolved).length;
    const byLevel = { 1: 0, 2: 0, 3: 0 } as Record<number, number>;
    warnings.forEach((w) => { byLevel[w.level] = (byLevel[w.level] ?? 0) + 1; });
    return { total, unresolved, byLevel };
  }, [warnings]);

  const handleToggleResolved = async (w: WarningResponse) => {
    setBusyId(w.id);
    try {
      const res = await warningsApi.resolve(w.id, !w.is_resolved);
      setWarnings((prev) => prev.map((x) => (x.id === w.id ? res.data : x)));
    } catch {
      alert(t("warnings.resolveError"));
    } finally {
      setBusyId(null);
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-muted-foreground animate-pulse">{t("common.loading")}</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="rounded-md bg-destructive/10 text-destructive px-4 py-3">{error}</div>
    );
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-primary">{t("warnings.title")}</h1>
        <p className="text-muted-foreground text-sm mt-0.5">{t("warnings.subtitle")}</p>
      </div>

      {/* Summary */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">{t("warnings.stat.total")}</p>
            <p className="text-3xl font-bold mt-1">{stats.total}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">{t("warnings.stat.unresolved")}</p>
            <p className={`text-3xl font-bold mt-1 ${stats.unresolved > 0 ? "text-destructive" : "text-green-600"}`}>
              {stats.unresolved}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">{t("warnings.stat.level1")}</p>
            <p className="text-3xl font-bold mt-1 text-yellow-600">{stats.byLevel[1] ?? 0}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground">{t("warnings.stat.level2plus")}</p>
            <p className="text-3xl font-bold mt-1 text-destructive">
              {(stats.byLevel[2] ?? 0) + (stats.byLevel[3] ?? 0)}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Filter tabs */}
      <div className="flex gap-2">
        {(["all", "unresolved", "resolved"] as Filter[]).map((f) => (
          <Button
            key={f}
            variant={filter === f ? "default" : "outline"}
            size="sm"
            onClick={() => setFilter(f)}
          >
            {t(`warnings.filter.${f}` as TKey)}
          </Button>
        ))}
      </div>

      {/* List */}
      {filtered.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <CheckCircle2 className="mx-auto h-10 w-10 mb-3 opacity-30" />
            <p>{warnings.length === 0 ? t("warnings.empty.none") : t("warnings.empty.filtered")}</p>
            {warnings.length === 0 && (
              <p className="text-sm mt-1">{t("warnings.empty.cta")}</p>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {filtered.map((w) => {
            const isAi = w.created_by === "system" && w.ai_risk_score !== null;
            const badge = LEVEL_BADGE[w.level] ?? LEVEL_BADGE[1];
            const borderCls = LEVEL_BORDER[w.level] ?? "border-l-yellow-500";
            return (
              <Card key={w.id} className={`border-l-4 ${borderCls} ${w.is_resolved ? "opacity-60" : ""}`}>
                <CardHeader className="pb-2">
                  <div className="flex items-start justify-between gap-3">
                    <div className="flex items-center gap-2 flex-wrap">
                      {isAi ? (
                        <Bot className="h-5 w-5 text-primary" />
                      ) : (
                        <ShieldAlert className="h-5 w-5 text-destructive" />
                      )}
                      <CardTitle className="text-base">
                        {t("warnings.semester")} {w.semester}
                      </CardTitle>
                      <Badge variant={badge.variant}>{t(badge.labelKey)}</Badge>
                      {isAi && <Badge variant="default">AI</Badge>}
                      {w.is_resolved && (
                        <Badge variant="default" className="bg-green-600 hover:bg-green-600">
                          {t("warnings.resolved")}
                        </Badge>
                      )}
                    </div>
                    <span className="text-xs text-muted-foreground shrink-0">
                      {w.sent_at ? new Date(w.sent_at).toLocaleDateString("vi-VN") : ""}
                    </span>
                  </div>
                </CardHeader>
                <CardContent className="space-y-3">
                  <p className="text-sm">{w.reason}</p>
                  <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-muted-foreground">
                    <span>
                      {t("warnings.gpaAt")}:{" "}
                      <span className="font-medium text-foreground">{w.gpa_at_warning.toFixed(2)}</span>
                    </span>
                    {w.ai_risk_score !== null && (
                      <span>
                        {t("warnings.aiRiskScore")}:{" "}
                        <span className="font-medium text-foreground">
                          {(w.ai_risk_score * 100).toFixed(0)}%
                        </span>
                      </span>
                    )}
                    <span>
                      {t("warnings.createdBy")}:{" "}
                      <span className="font-medium text-foreground">
                        {w.created_by === "system" ? t("warnings.bySystem") : t("warnings.byAdmin")}
                      </span>
                    </span>
                  </div>
                  <div className="flex justify-end pt-1">
                    <Button
                      variant={w.is_resolved ? "outline" : "default"}
                      size="sm"
                      disabled={busyId === w.id}
                      onClick={() => handleToggleResolved(w)}
                    >
                      {busyId === w.id
                        ? t("common.saving")
                        : w.is_resolved
                          ? t("warnings.markUnresolved")
                          : t("warnings.markResolved")}
                    </Button>
                  </div>
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Info box about regulations */}
      <Card className="bg-blue-50 border-blue-200">
        <CardContent className="pt-6 text-sm text-blue-900 space-y-1">
          <div className="flex items-center gap-2 font-medium">
            <AlertTriangle className="h-4 w-4" />
            {t("warnings.infoTitle")}
          </div>
          <p>{t("warnings.info.l1")}</p>
          <p>{t("warnings.info.l2")}</p>
          <p>{t("warnings.info.l3")}</p>
          <p className="italic mt-2">{t("warnings.info.ai")}</p>
        </CardContent>
      </Card>
    </div>
  );
}
