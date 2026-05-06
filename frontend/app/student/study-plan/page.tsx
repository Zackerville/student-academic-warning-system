"use client";

import { useEffect, useState } from "react";
import { Target, BookOpen, AlertTriangle, GraduationCap, Lightbulb, RotateCcw } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { studyPlanApi, type StudyPlanResponse } from "@/lib/api";
import { useT, type TKey } from "@/lib/i18n";

const PRIORITY_META: Record<number, { variant: "default" | "secondary" | "destructive"; labelKey: TKey; ring: string }> = {
  1: { variant: "destructive", labelKey: "studyPlan.priority.high",   ring: "ring-red-300 bg-red-50" },
  2: { variant: "secondary",   labelKey: "studyPlan.priority.medium", ring: "ring-orange-200 bg-orange-50" },
  3: { variant: "secondary",   labelKey: "studyPlan.priority.low",    ring: "ring-yellow-200 bg-yellow-50" },
};

export default function StudyPlanPage() {
  const t = useT();
  const [plan, setPlan] = useState<StudyPlanResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    studyPlanApi
      .me()
      .then((r) => setPlan(r.data))
      .catch(() => setError(t("studyPlan.loadError")))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="text-muted-foreground animate-pulse">{t("common.loading")}</div>
      </div>
    );
  }

  if (error || !plan) {
    return (
      <div className="rounded-md bg-destructive/10 text-destructive px-4 py-3">
        {error ?? t("common.unknownError")}
      </div>
    );
  }

  const { credit_load, retake_courses, suggested_courses, total_unresolved_failed, total_credits_earned, gpa_cumulative } = plan;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-primary">{t("studyPlan.title")}</h1>
        <p className="text-muted-foreground text-sm mt-0.5">{t("studyPlan.subtitle")}</p>
      </div>

      {/* Snapshot */}
      <div className="grid grid-cols-2 gap-4 lg:grid-cols-3">
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground flex items-center gap-1.5">
              <GraduationCap className="h-4 w-4" /> {t("dashboard.gpaCumulative")}
            </p>
            <p className={`text-3xl font-bold mt-1 ${gpa_cumulative >= 2.0 ? "text-green-600" : "text-destructive"}`}>
              {gpa_cumulative.toFixed(1)}
            </p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground flex items-center gap-1.5">
              <BookOpen className="h-4 w-4" /> {t("dashboard.creditsEarned")}
            </p>
            <p className="text-3xl font-bold mt-1">{total_credits_earned}</p>
          </CardContent>
        </Card>
        <Card>
          <CardContent className="pt-6">
            <p className="text-sm text-muted-foreground flex items-center gap-1.5">
              <AlertTriangle className="h-4 w-4" /> {t("studyPlan.unresolvedFailed")}
            </p>
            <p className={`text-3xl font-bold mt-1 ${total_unresolved_failed > 0 ? "text-destructive" : "text-green-600"}`}>
              {total_unresolved_failed}
            </p>
          </CardContent>
        </Card>
      </div>

      {/* Credit load */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Target className="h-4 w-4 text-primary" />
            {t("studyPlan.creditLoadTitle")}
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="grid grid-cols-3 gap-3 text-center">
            <div className="rounded-lg border bg-muted/30 py-4">
              <p className="text-xs text-muted-foreground">{t("studyPlan.min")}</p>
              <p className="text-2xl font-bold mt-1">{credit_load.min_credits}</p>
            </div>
            <div className="rounded-lg border-2 border-primary bg-primary/5 py-4">
              <p className="text-xs text-primary font-medium">{t("studyPlan.recommended")}</p>
              <p className="text-3xl font-bold mt-1 text-primary">{credit_load.recommended_credits}</p>
            </div>
            <div className="rounded-lg border bg-muted/30 py-4">
              <p className="text-xs text-muted-foreground">{t("studyPlan.max")}</p>
              <p className="text-2xl font-bold mt-1">{credit_load.max_credits}</p>
            </div>
          </div>
          <div className="rounded-md bg-blue-50 border border-blue-200 px-4 py-3 text-sm text-blue-900">
            <p className="font-medium mb-1">{t("studyPlan.rationaleTitle")}</p>
            <p>{credit_load.rationale}</p>
          </div>
        </CardContent>
      </Card>

      {/* Retakes */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <RotateCcw className="h-4 w-4 text-destructive" />
            {t("studyPlan.retakeTitle")}
            <Badge variant="outline">{retake_courses.length}</Badge>
          </CardTitle>
        </CardHeader>
        <CardContent>
          {retake_courses.length === 0 ? (
            <p className="text-sm text-muted-foreground py-4 text-center">{t("studyPlan.retakeEmpty")}</p>
          ) : (
            <div className="space-y-2">
              {retake_courses.map((c) => {
                const meta = PRIORITY_META[c.priority] ?? PRIORITY_META[3];
                return (
                  <div
                    key={c.course_id}
                    className={`rounded-md border ring-1 ${meta.ring} px-4 py-3`}
                  >
                    <div className="flex items-start justify-between gap-3 flex-wrap">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 flex-wrap mb-1">
                          <span className="font-mono text-sm font-medium">{c.course_code}</span>
                          <span className="text-sm text-muted-foreground">·</span>
                          <span className="text-sm">{c.course_name}</span>
                          <Badge variant={meta.variant}>{t(meta.labelKey)}</Badge>
                        </div>
                        <div className="text-xs text-muted-foreground flex flex-wrap gap-x-4 gap-y-0.5">
                          <span>{c.credits} TC</span>
                          {c.last_grade_letter && (
                            <span>
                              {t("studyPlan.lastGrade")}:{" "}
                              <span className="font-medium text-foreground">{c.last_grade_letter}</span>
                            </span>
                          )}
                          {c.last_total_score !== null && (
                            <span>
                              {t("studyPlan.lastScore")}:{" "}
                              <span className="font-medium text-foreground">{c.last_total_score.toFixed(1)}</span>
                            </span>
                          )}
                          <span>
                            {t("studyPlan.lastSemester")}:{" "}
                            <span className="font-medium text-foreground">{c.last_semester}</span>
                          </span>
                        </div>
                        <p className="text-xs text-muted-foreground mt-1.5 italic">{c.reason}</p>
                      </div>
                    </div>
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Suggested */}
      {suggested_courses.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center gap-2">
              <Lightbulb className="h-4 w-4 text-yellow-600" />
              {t("studyPlan.suggestedTitle")}
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              {suggested_courses.map((c) => (
                <div key={c.course_id} className="rounded-md border px-4 py-3 hover:bg-muted/30">
                  <div className="flex items-center gap-2 flex-wrap mb-1">
                    <span className="font-mono text-sm font-medium">{c.course_code}</span>
                    <span className="text-sm text-muted-foreground">·</span>
                    <span className="text-sm">{c.course_name}</span>
                    <Badge variant="outline">{c.credits} TC</Badge>
                  </div>
                  <p className="text-xs text-muted-foreground italic">{c.rationale}</p>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
