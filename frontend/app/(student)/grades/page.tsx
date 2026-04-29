"use client";

import { useEffect, useState, useCallback } from "react";
import { ClipboardPaste, PenLine, CheckCircle2, Clock, XCircle, Plus, X } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import { studentApi, apiClient, type EnrollmentResponse, type ImportResult } from "@/lib/api";

// ─── Helpers ─────────────────────────────────────────────────

const STATUS_CONFIG: Record<string, { label: string; icon: React.ElementType; color: string }> = {
  enrolled: { label: "Đang học", icon: Clock, color: "text-blue-500" },
  passed: { label: "Đạt", icon: CheckCircle2, color: "text-green-600" },
  failed: { label: "Không đạt", icon: XCircle, color: "text-destructive" },
  withdrawn: { label: "Rút môn", icon: XCircle, color: "text-muted-foreground" },
  exempt: { label: "Miễn", icon: CheckCircle2, color: "text-yellow-600" },
};

const GRADE_COLOR: Record<string, string> = {
  "A+": "text-green-600", A: "text-green-600",
  "B+": "text-blue-600", B: "text-blue-600",
  "C+": "text-yellow-600", C: "text-yellow-600",
  "D+": "text-orange-500", D: "text-orange-500",
  F: "text-destructive",
};

function gradeBadge(letter: string | null) {
  if (!letter) return <span className="text-muted-foreground">—</span>;
  return <span className={`font-bold ${GRADE_COLOR[letter] ?? "text-foreground"}`}>{letter}</span>;
}

// ─── Import myBK mode ────────────────────────────────────────

function MyBKImportPanel({ onSuccess }: { onSuccess: () => void }) {
  const [text, setText] = useState("");
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<ImportResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleImport = async () => {
    if (!text.trim()) return;
    setLoading(true);
    setError(null);
    setResult(null);
    try {
      const res = await studentApi.importMyBK(text);
      setResult(res.data);
      onSuccess();
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? "Import thất bại. Vui lòng thử lại.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-4">
      <div className="rounded-md bg-blue-50 border border-blue-200 text-blue-800 text-sm px-4 py-3 space-y-1">
        <p className="font-medium">Hướng dẫn:</p>
        <ol className="list-decimal list-inside space-y-0.5 text-xs">
          <li>Mở myBK → Kết quả học tập → Bảng điểm học kỳ</li>
          <li>Nhấn <kbd className="bg-blue-100 px-1 rounded">Ctrl+A</kbd> rồi <kbd className="bg-blue-100 px-1 rounded">Ctrl+C</kbd></li>
          <li>Dán vào ô bên dưới và nhấn Import</li>
        </ol>
      </div>

      <div className="space-y-2">
        <Label>Dán nội dung từ myBK</Label>
        <textarea
          className="w-full min-h-[200px] rounded-md border border-input bg-transparent px-3 py-2 text-sm font-mono shadow-sm focus:outline-none focus:ring-1 focus:ring-ring resize-y"
          placeholder={"Học kỳ 1 năm học 2021-2022\nCO1007  Cấu trúc rời rạc    3   8.5   A   Đạt\n..."}
          value={text}
          onChange={(e) => setText(e.target.value)}
        />
      </div>

      {result && (
        <div className="rounded-md bg-green-50 border border-green-200 text-green-700 text-sm px-4 py-3">
          <p className="font-medium">{result.message}</p>
          <p className="text-xs mt-1">
            Học kỳ: {result.semesters.join(", ")} — Tạo mới: {result.created}, Cập nhật: {result.updated}, Tổng: {result.total_courses} môn
          </p>
        </div>
      )}
      {error && (
        <div className="rounded-md bg-destructive/10 text-destructive text-sm px-3 py-2">{error}</div>
      )}

      <Button onClick={handleImport} disabled={loading || !text.trim()} className="w-full">
        {loading ? "Đang import..." : "Import từ myBK"}
      </Button>
    </div>
  );
}

// ─── Manual grade entry ──────────────────────────────────────

function ManualGradeRow({ enrollment, onUpdated }: { enrollment: EnrollmentResponse; onUpdated: () => void }) {
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    midterm_score: enrollment.midterm_score?.toString() ?? "",
    lab_score: enrollment.lab_score?.toString() ?? "",
    other_score: enrollment.other_score?.toString() ?? "",
    final_score: enrollment.final_score?.toString() ?? "",
    attendance_rate: enrollment.attendance_rate?.toString() ?? "",
  });

  const parseScore = (v: string) => (v === "" ? null : parseFloat(v));

  const handleSave = async () => {
    setSaving(true);
    try {
      await studentApi.updateGrades(enrollment.id, {
        midterm_score: parseScore(form.midterm_score),
        lab_score: parseScore(form.lab_score),
        other_score: parseScore(form.other_score),
        final_score: parseScore(form.final_score),
        attendance_rate: parseScore(form.attendance_rate),
      });
      setEditing(false);
      onUpdated();
    } catch {
      // keep editing on error
    } finally {
      setSaving(false);
    }
  };

  const sc = STATUS_CONFIG[enrollment.status] ?? STATUS_CONFIG.enrolled;
  const StatusIcon = sc.icon;

  return (
    <div className="border rounded-lg p-4 space-y-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="flex items-center gap-2">
            <span className="font-mono text-sm text-muted-foreground">{enrollment.course.course_code}</span>
            {enrollment.is_finalized && (
              <Badge variant="secondary" className="text-[10px] py-0">myBK</Badge>
            )}
          </div>
          <p className="font-medium">{enrollment.course.name}</p>
          <p className="text-xs text-muted-foreground">{enrollment.course.credits} tín chỉ · HK {enrollment.semester}</p>
        </div>
        <div className="text-right shrink-0">
          <div className="text-2xl font-bold">{gradeBadge(enrollment.grade_letter)}</div>
          <div className={`flex items-center gap-1 text-xs ${sc.color} justify-end`}>
            <StatusIcon className="h-3 w-3" />
            {sc.label}
          </div>
          {enrollment.total_score !== null && (
            <div className="text-xs text-muted-foreground">{enrollment.total_score.toFixed(2)}/10</div>
          )}
        </div>
      </div>

      {/* Score components */}
      {!enrollment.is_finalized && (
        <>
          {editing ? (
            <div className="grid grid-cols-2 sm:grid-cols-5 gap-2">
              {[
                { key: "midterm_score", label: `GK (${Math.round(enrollment.midterm_weight * 100)}%)`, show: enrollment.midterm_weight > 0 },
                { key: "lab_score", label: `TN (${Math.round(enrollment.lab_weight * 100)}%)`, show: enrollment.lab_weight > 0 },
                { key: "other_score", label: `BTL (${Math.round(enrollment.other_weight * 100)}%)`, show: enrollment.other_weight > 0 },
                { key: "final_score", label: `CK (${Math.round(enrollment.final_weight * 100)}%)`, show: enrollment.final_weight > 0 },
                { key: "attendance_rate", label: "Điểm danh %", show: true },
              ]
                .filter((f) => f.show)
                .map(({ key, label }) => (
                  <div key={key} className="space-y-1">
                    <Label className="text-xs">{label}</Label>
                    <Input
                      type="number"
                      step="0.1"
                      min="0"
                      max={key === "attendance_rate" ? "100" : "10"}
                      className="h-8 text-sm"
                      value={(form as Record<string, string>)[key]}
                      onChange={(e) => setForm((f) => ({ ...f, [key]: e.target.value }))}
                    />
                  </div>
                ))}
            </div>
          ) : (
            <div className="flex flex-wrap gap-3 text-xs text-muted-foreground">
              {enrollment.midterm_weight > 0 && (
                <span>GK: <b>{enrollment.midterm_score ?? "—"}</b> ({Math.round(enrollment.midterm_weight * 100)}%)</span>
              )}
              {enrollment.lab_weight > 0 && (
                <span>TN: <b>{enrollment.lab_score ?? "—"}</b> ({Math.round(enrollment.lab_weight * 100)}%)</span>
              )}
              {enrollment.other_weight > 0 && (
                <span>BTL: <b>{enrollment.other_score ?? "—"}</b> ({Math.round(enrollment.other_weight * 100)}%)</span>
              )}
              {enrollment.final_weight > 0 && (
                <span>CK: <b>{enrollment.final_score ?? "—"}</b> ({Math.round(enrollment.final_weight * 100)}%)</span>
              )}
              {enrollment.attendance_rate !== null && (
                <span>Điểm danh: <b>{enrollment.attendance_rate}%</b></span>
              )}
            </div>
          )}

          <div className="flex gap-2">
            {editing ? (
              <>
                <Button size="sm" onClick={handleSave} disabled={saving}>
                  {saving ? "Đang lưu..." : "Lưu"}
                </Button>
                <Button size="sm" variant="outline" onClick={() => setEditing(false)}>Hủy</Button>
              </>
            ) : (
              <Button size="sm" variant="outline" onClick={() => setEditing(true)}>
                <PenLine className="h-3 w-3 mr-1" /> Nhập điểm
              </Button>
            )}
          </div>
        </>
      )}
    </div>
  );
}

// ─── Weight templates ────────────────────────────────────────

type Template = { label: string; desc: string; mw: number; lw: number; ow: number; fw: number; custom?: boolean };

const WEIGHT_TEMPLATES: Template[] = [
  { label: "GK 30% + CK 70%",                     desc: "Phổ biến nhất — lý thuyết thuần",               mw:0.3, lw:0.0,  ow:0.0,  fw:0.7 },
  { label: "GK 30% + TN 20% + CK 50%",            desc: "Môn có thí nghiệm (Vật lý, Mạng MT…)",          mw:0.3, lw:0.2,  ow:0.0,  fw:0.5 },
  { label: "GK 20% + TN 30% + CK 50%",            desc: "Môn nặng thực hành",                            mw:0.2, lw:0.3,  ow:0.0,  fw:0.5 },
  { label: "GK 30% + BTL 30% + CK 40%",           desc: "Môn có đồ án / bài tập lớn",                    mw:0.3, lw:0.0,  ow:0.3,  fw:0.4 },
  { label: "GK 20% + BTL 40% + CK 40%",           desc: "Môn nặng đồ án",                                mw:0.2, lw:0.0,  ow:0.4,  fw:0.4 },
  { label: "GK 30% + TN 15% + BTL 15% + CK 40%", desc: "Cả 4 thành phần",                               mw:0.3, lw:0.15, ow:0.15, fw:0.4 },
  { label: "GK 20% + TN 20% + BTL 20% + CK 40%", desc: "Cả 4 thành phần (nặng thực hành)",              mw:0.2, lw:0.2,  ow:0.2,  fw:0.4 },
  { label: "BTL 30% + CK 70%",                    desc: "Không có thi giữa kỳ",                          mw:0.0, lw:0.0,  ow:0.3,  fw:0.7 },
  { label: "TN 30% + CK 70%",                     desc: "Thực hành + cuối kỳ",                           mw:0.0, lw:0.3,  ow:0.0,  fw:0.7 },
  { label: "BTL / Đồ án 100%",                    desc: "Đồ án chuyên ngành, seminar",                   mw:0.0, lw:0.0,  ow:1.0,  fw:0.0 },
  { label: "CK 100%",                             desc: "Chỉ thi cuối kỳ",                               mw:0.0, lw:0.0,  ow:0.0,  fw:1.0 },
  { label: "Tùy chỉnh",                           desc: "Tự nhập % cho từng thành phần",                 mw:0.3, lw:0.0,  ow:0.0,  fw:0.7, custom:true },
];

// ─── Add Course Dialog ───────────────────────────────────────

function AddCourseDialog({ onSuccess }: { onSuccess: () => void }) {
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [templateIdx, setTemplateIdx] = useState(0);
  const [customWeights, setCustomWeights] = useState({ mw:"30", lw:"0", ow:"0", fw:"70" });

  const [form, setForm] = useState({
    course_code: "",
    course_name: "",
    credits: "3",
    semester: "",
    midterm_score: "",
    lab_score: "",
    other_score: "",
    final_score: "",
    attendance_rate: "",
  });

  const tplBase = WEIGHT_TEMPLATES[templateIdx];
  const tpl = tplBase.custom
    ? { ...tplBase, mw: parseFloat(customWeights.mw||"0")/100, lw: parseFloat(customWeights.lw||"0")/100,
                    ow: parseFloat(customWeights.ow||"0")/100, fw: parseFloat(customWeights.fw||"0")/100 }
    : tplBase;

  const set = (k: string, v: string) => setForm((f) => ({ ...f, [k]: v }));

  const handleSubmit = async () => {
    setError(null);
    if (!form.course_code.trim() || !form.course_name.trim() || !form.semester.trim()) {
      setError("Vui lòng điền đầy đủ mã môn, tên môn và học kỳ.");
      return;
    }
    setSaving(true);
    try {
      await apiClient.post("/students/me/enrollments/manual", {
        course_code: form.course_code.trim().toUpperCase(),
        course_name: form.course_name.trim(),
        credits: parseInt(form.credits) || 3,
        semester: form.semester.trim(),
        midterm_weight: tpl.mw,
        lab_weight: tpl.lw,
        other_weight: tpl.ow,
        final_weight: tpl.fw,
        midterm_score: form.midterm_score !== "" ? parseFloat(form.midterm_score) : null,
        lab_score: form.lab_score !== "" ? parseFloat(form.lab_score) : null,
        other_score: form.other_score !== "" ? parseFloat(form.other_score) : null,
        final_score: form.final_score !== "" ? parseFloat(form.final_score) : null,
        attendance_rate: form.attendance_rate !== "" ? parseFloat(form.attendance_rate) : null,
      });
      setOpen(false);
      setForm({
        course_code: "", course_name: "", credits: "3", semester: "",
        midterm_score: "", lab_score: "", other_score: "", final_score: "", attendance_rate: ""
      });
      setTemplateIdx(0);
      onSuccess();
    } catch (e: unknown) {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setError(msg ?? "Thêm môn thất bại.");
    } finally {
      setSaving(false);
    }
  };

  if (!open) {
    return (
      <Button size="sm" onClick={() => setOpen(true)}>
        <Plus className="h-4 w-4 mr-1" /> Thêm môn học
      </Button>
    );
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div className="bg-white rounded-xl shadow-2xl w-full max-w-lg max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between px-6 pt-5 pb-3 border-b">
          <h2 className="font-semibold text-lg">Thêm môn học</h2>
          <button onClick={() => setOpen(false)} className="text-muted-foreground hover:text-foreground">
            <X className="h-5 w-5" />
          </button>
        </div>

        <div className="px-6 py-4 space-y-4">
          {error && (
            <div className="rounded-md bg-destructive/10 text-destructive text-sm px-3 py-2">{error}</div>
          )}

          {/* Course info */}
          <div className="grid grid-cols-3 gap-3">
            <div className="space-y-1 col-span-1">
              <Label className="text-xs">Mã môn *</Label>
              <Input placeholder="CO1007" value={form.course_code}
                onChange={(e) => set("course_code", e.target.value)} className="h-8 text-sm uppercase" />
            </div>
            <div className="space-y-1 col-span-2">
              <Label className="text-xs">Tên môn *</Label>
              <Input placeholder="Cấu trúc rời rạc" value={form.course_name}
                onChange={(e) => set("course_name", e.target.value)} className="h-8 text-sm" />
            </div>
          </div>

          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1">
              <Label className="text-xs">Học kỳ * (VD: 241)</Label>
              <Input placeholder="241" value={form.semester}
                onChange={(e) => set("semester", e.target.value)} className="h-8 text-sm" />
            </div>
            <div className="space-y-1">
              <Label className="text-xs">Số tín chỉ</Label>
              <Input type="number" min="1" max="10" value={form.credits}
                onChange={(e) => set("credits", e.target.value)} className="h-8 text-sm" />
            </div>
          </div>

          {/* Weight template */}
          <div className="space-y-2">
            <Label className="text-xs">Cấu trúc điểm</Label>
            <select
              value={templateIdx}
              onChange={(e) => setTemplateIdx(parseInt(e.target.value))}
              className="flex h-9 w-full rounded-md border border-input bg-transparent px-3 text-sm shadow-sm focus:outline-none focus:ring-1 focus:ring-ring"
            >
              {WEIGHT_TEMPLATES.map((t, i) => (
                <option key={i} value={i}>{t.label}</option>
              ))}
            </select>
            <p className="text-xs text-muted-foreground">{tplBase.desc}</p>

            {/* Custom weight inputs */}
            {tplBase.custom && (
              <div className="grid grid-cols-4 gap-2 pt-1">
                {[
                  { k:"mw", label:"GK (%)" },
                  { k:"lw", label:"TN (%)" },
                  { k:"ow", label:"BTL (%)" },
                  { k:"fw", label:"CK (%)" },
                ].map(({ k, label }) => (
                  <div key={k} className="space-y-1">
                    <Label className="text-xs">{label}</Label>
                    <Input
                      type="number" min="0" max="100" step="5"
                      className="h-8 text-sm"
                      value={customWeights[k as keyof typeof customWeights]}
                      onChange={(e) => setCustomWeights((w) => ({ ...w, [k]: e.target.value }))}
                    />
                  </div>
                ))}
                {(() => {
                  const sum = ["mw","lw","ow","fw"].reduce((s,k) => s + (parseFloat(customWeights[k as keyof typeof customWeights])||0), 0);
                  return sum !== 100
                    ? <p className="col-span-4 text-xs text-destructive">Tổng phải = 100% (hiện: {sum}%)</p>
                    : <p className="col-span-4 text-xs text-green-600">Tổng = 100% ✓</p>;
                })()}
              </div>
            )}
          </div>

          {/* Scores */}
          <div className="space-y-2">
            <Label className="text-xs text-muted-foreground">Điểm thành phần (để trống nếu chưa có)</Label>
            <div className="grid grid-cols-2 gap-2">
              {tpl.mw > 0 && (
                <div className="space-y-1">
                  <Label className="text-xs">Giữa kỳ — GK ({Math.round(tpl.mw * 100)}%)</Label>
                  <Input type="number" step="0.1" min="0" max="10" placeholder="0–10"
                    value={form.midterm_score} onChange={(e) => set("midterm_score", e.target.value)} className="h-8 text-sm" />
                </div>
              )}
              {tpl.lw > 0 && (
                <div className="space-y-1">
                  <Label className="text-xs">Thí nghiệm — TN ({Math.round(tpl.lw * 100)}%)</Label>
                  <Input type="number" step="0.1" min="0" max="10" placeholder="0–10"
                    value={form.lab_score} onChange={(e) => set("lab_score", e.target.value)} className="h-8 text-sm" />
                </div>
              )}
              {tpl.ow > 0 && (
                <div className="space-y-1">
                  <Label className="text-xs">BTL / Đồ án ({Math.round(tpl.ow * 100)}%)</Label>
                  <Input type="number" step="0.1" min="0" max="10" placeholder="0–10"
                    value={form.other_score} onChange={(e) => set("other_score", e.target.value)} className="h-8 text-sm" />
                </div>
              )}
              {tpl.fw > 0 && (
                <div className="space-y-1">
                  <Label className="text-xs">Cuối kỳ — CK ({Math.round(tpl.fw * 100)}%)</Label>
                  <Input type="number" step="0.1" min="0" max="10" placeholder="0–10"
                    value={form.final_score} onChange={(e) => set("final_score", e.target.value)} className="h-8 text-sm" />
                </div>
              )}
              <div className="space-y-1">
                <Label className="text-xs">Tỉ lệ điểm danh (%)</Label>
                <Input type="number" step="1" min="0" max="100" placeholder="0–100"
                  value={form.attendance_rate} onChange={(e) => set("attendance_rate", e.target.value)} className="h-8 text-sm" />
              </div>
            </div>
          </div>
        </div>

        <div className="px-6 pb-5 flex gap-2 justify-end">
          <Button variant="outline" onClick={() => setOpen(false)}>Hủy</Button>
          <Button onClick={handleSubmit} disabled={saving}>
            {saving ? "Đang lưu..." : "Thêm môn"}
          </Button>
        </div>
      </div>
    </div>
  );
}

// ─── Main page ───────────────────────────────────────────────

type Mode = "list" | "import";

export default function GradesPage() {
  const [mode, setMode] = useState<Mode>("list");
  const [enrollments, setEnrollments] = useState<EnrollmentResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [filterSemester, setFilterSemester] = useState<string>("");

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await studentApi.enrollments();
      setEnrollments(res.data);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const semesters = Array.from(new Set(enrollments.map((e) => e.semester))).sort().reverse();
  const filtered = filterSemester ? enrollments.filter((e) => e.semester === filterSemester) : enrollments;

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div>
          <h1 className="text-2xl font-bold text-primary">Bảng điểm</h1>
          <p className="text-sm text-muted-foreground">Quản lý điểm các môn học</p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <AddCourseDialog onSuccess={load} />
          <Button
            variant={mode === "list" ? "default" : "outline"}
            size="sm"
            onClick={() => setMode("list")}
          >
            <PenLine className="h-4 w-4 mr-1" /> Danh sách
          </Button>
          <Button
            variant={mode === "import" ? "default" : "outline"}
            size="sm"
            onClick={() => setMode("import")}
          >
            <ClipboardPaste className="h-4 w-4 mr-1" /> Import myBK
          </Button>
        </div>
      </div>

      {mode === "import" ? (
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Import từ myBK</CardTitle>
            <CardDescription>
              Dán nội dung bảng điểm copy từ trang myBK để tự động cập nhật tất cả môn học.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <MyBKImportPanel onSuccess={() => { load(); setMode("list"); }} />
          </CardContent>
        </Card>
      ) : (
        <>
          {/* Semester filter */}
          {semesters.length > 1 && (
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-sm text-muted-foreground">Lọc:</span>
              <button
                onClick={() => setFilterSemester("")}
                className={`text-sm px-3 py-1 rounded-full border transition-colors ${filterSemester === "" ? "bg-primary text-primary-foreground border-primary" : "hover:bg-muted border-border"
                  }`}
              >
                Tất cả
              </button>
              {semesters.map((s) => (
                <button
                  key={s}
                  onClick={() => setFilterSemester(s)}
                  className={`text-sm px-3 py-1 rounded-full border transition-colors ${filterSemester === s ? "bg-primary text-primary-foreground border-primary" : "hover:bg-muted border-border"
                    }`}
                >
                  HK {s}
                </button>
              ))}
            </div>
          )}

          {loading ? (
            <div className="text-center py-12 text-muted-foreground animate-pulse">Đang tải...</div>
          ) : filtered.length === 0 ? (
            <Card>
              <CardContent className="py-12 text-center text-muted-foreground space-y-3">
                <ClipboardPaste className="mx-auto h-10 w-10 opacity-30" />
                <p>Chưa có dữ liệu điểm.</p>
                <div className="flex gap-2 justify-center flex-wrap">
                  <AddCourseDialog onSuccess={load} />
                  <Button size="sm" variant="outline" onClick={() => setMode("import")}>
                    <ClipboardPaste className="h-4 w-4 mr-1" /> Import myBK
                  </Button>
                </div>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {filtered.map((e) => (
                <ManualGradeRow key={e.id} enrollment={e} onUpdated={load} />
              ))}
            </div>
          )}
        </>
      )}
    </div>
  );
}
