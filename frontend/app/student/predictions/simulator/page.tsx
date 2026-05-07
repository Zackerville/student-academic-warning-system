"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Link from "next/link";
import { ArrowLeft, FlaskConical, TrendingDown, TrendingUp, Minus } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  studentApi,
  predictionsApi,
  type EnrollmentResponse,
  type SimulateResult,
} from "@/lib/api";

const RISK_COLOR: Record<string, string> = {
  low:      "text-green-600",
  medium:   "text-yellow-600",
  high:     "text-orange-500",
  critical: "text-destructive",
};

const RISK_LABEL: Record<string, string> = {
  low:      "Thấp",
  medium:   "Trung bình",
  high:     "Cao",
  critical: "Nghiêm trọng",
};

const GRADE_THRESHOLDS = [
  { min: 9.0, letter: "A+" },
  { min: 8.5, letter: "A" },
  { min: 8.0, letter: "B+" },
  { min: 7.0, letter: "B" },
  { min: 6.5, letter: "C+" },
  { min: 5.5, letter: "C" },
  { min: 5.0, letter: "D+" },
  { min: 4.0, letter: "D" },
  { min: 0.0, letter: "F" },
];

function scoreToGrade(score: number): string {
  for (const t of GRADE_THRESHOLDS) {
    if (score >= t.min) return t.letter;
  }
  return "F";
}

function RiskBadge({ level }: { level: string }) {
  const variant =
    level === "low" ? "default" :
    level === "medium" ? "secondary" : "destructive";
  return <Badge variant={variant}>{RISK_LABEL[level] ?? level}</Badge>;
}

export default function SimulatorPage() {
  const [enrollments, setEnrollments] = useState<EnrollmentResponse[]>([]);
  const [scores, setScores] = useState<Record<string, string>>({});
  const [result, setResult] = useState<SimulateResult | null>(null);
  const [loading, setLoading] = useState(true);
  const [simulating, setSimulating] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Load only currently enrolled (not finalized) courses
  useEffect(() => {
    studentApi.enrollments().then((r) => {
      const current = r.data.filter(
        (e) => e.status === "enrolled" && !e.is_finalized
      );
      setEnrollments(current);
      // Initialize scores from existing total_score
      const init: Record<string, string> = {};
      for (const e of current) {
        init[e.id] = e.total_score != null ? String(e.total_score) : "";
      }
      setScores(init);
    }).finally(() => setLoading(false));
  }, []);

  const runSimulate = useCallback((currentScores: Record<string, string>) => {
    const items = Object.entries(currentScores)
      .filter(([, v]) => v !== "" && !isNaN(Number(v)))
      .map(([id, v]) => ({ enrollment_id: id, hypothetical_score: Number(v) }));

    if (items.length === 0) {
      setResult(null);
      return;
    }

    setSimulating(true);
    predictionsApi.simulate(items)
      .then((r) => setResult(r.data))
      .catch(() => {})
      .finally(() => setSimulating(false));
  }, []);

  const handleScoreChange = (id: string, raw: string) => {
    const next = { ...scores, [id]: raw };
    setScores(next);

    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => runSimulate(next), 600);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64 text-muted-foreground animate-pulse">
        Đang tải...
      </div>
    );
  }

  const delta = result?.delta_risk_score ?? 0;
  const DeltaIcon = delta < -0.005 ? TrendingDown : delta > 0.005 ? TrendingUp : Minus;
  const deltaColor = delta < -0.005 ? "text-green-600" : delta > 0.005 ? "text-destructive" : "text-muted-foreground";

  return (
    <div className="space-y-6 max-w-3xl">
      <div className="flex items-center gap-3">
        <Link href="/student/predictions">
          <Button variant="ghost" size="sm">
            <ArrowLeft className="h-4 w-4 mr-1" />
            Quay lại
          </Button>
        </Link>
        <div>
          <h1 className="text-xl font-bold text-primary flex items-center gap-2">
            <FlaskConical className="h-5 w-5" />
            Mô phỏng điểm số
          </h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Nhập điểm giả định để xem risk score thay đổi như thế nào
          </p>
        </div>
      </div>

      {/* Result panel */}
      {result && (
        <Card className="border-primary/30 bg-primary/5">
          <CardContent className="pt-5">
            <div className="grid grid-cols-3 gap-4 text-center">
              <div>
                <p className="text-xs text-muted-foreground mb-1">Hiện tại</p>
                {result.original_risk_score != null ? (
                  <>
                    <p className={`text-2xl font-bold ${RISK_COLOR[result.original_risk_level ?? "low"]}`}>
                      {(result.original_risk_score * 100).toFixed(0)}%
                    </p>
                    <RiskBadge level={result.original_risk_level ?? "low"} />
                  </>
                ) : (
                  <p className="text-muted-foreground text-sm">Chưa có</p>
                )}
              </div>

              <div className="flex flex-col items-center justify-center">
                <DeltaIcon className={`h-8 w-8 ${deltaColor}`} />
                <p className={`text-sm font-semibold ${deltaColor}`}>
                  {delta === 0 ? "Không đổi" : `${delta > 0 ? "+" : ""}${(delta * 100).toFixed(0)}%`}
                </p>
              </div>

              <div>
                <p className="text-xs text-muted-foreground mb-1">Mô phỏng</p>
                <p className={`text-2xl font-bold ${RISK_COLOR[result.simulated_risk_level]}`}>
                  {(result.simulated_risk_score * 100).toFixed(0)}%
                </p>
                <RiskBadge level={result.simulated_risk_level} />
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {simulating && (
        <p className="text-xs text-muted-foreground animate-pulse">Đang tính toán...</p>
      )}

      {/* Course score inputs */}
      {enrollments.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center text-muted-foreground">
            <FlaskConical className="mx-auto h-10 w-10 mb-3 opacity-30" />
            <p className="font-medium">Không có môn nào đang học</p>
            <p className="text-sm mt-1">Mô phỏng chỉ hoạt động với môn có trạng thái "đang học".</p>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base">Điểm giả định</CardTitle>
            <CardDescription>Nhập điểm dự kiến (0–10) cho từng môn đang học</CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-3">
              {enrollments.map((e) => {
                const val = scores[e.id] ?? "";
                const num = Number(val);
                const valid = val !== "" && !isNaN(num) && num >= 0 && num <= 10;
                const grade = valid ? scoreToGrade(num) : null;
                const gradeColor =
                  grade === "F" ? "text-destructive" :
                  grade && ["D", "D+"].includes(grade) ? "text-orange-500" :
                  "text-green-600";

                return (
                  <div key={e.id} className="flex items-center gap-3">
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{e.course.name}</p>
                      <p className="text-xs text-muted-foreground">
                        {e.course.course_code} · {e.course.credits} TC · HK {e.semester}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <input
                        type="number"
                        min={0}
                        max={10}
                        step={0.1}
                        placeholder="–"
                        value={val}
                        onChange={(ev) => handleScoreChange(e.id, ev.target.value)}
                        className="w-20 text-center rounded-md border border-input bg-background px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                      />
                      {grade && (
                        <span className={`text-sm font-semibold w-8 text-right ${gradeColor}`}>
                          {grade}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}
