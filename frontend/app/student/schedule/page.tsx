"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { Upload, CalendarDays, ListTodo, Trash2, Plus, Sparkles, ChevronLeft, ChevronRight, Pencil, X } from "lucide-react";
import { toast } from "sonner";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { Dialog, DialogContent, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { SkeletonCard } from "@/components/ui/skeleton";
import {
  studentApi,
  eventsApi,
  type TimetableSession,
  type ExamEntry,
  type PersonalEvent,
  type EventResponse,
} from "@/lib/api";

type Tab = "week" | "month" | "list";

// HCMUT period schedule (tiết 1-15)
const PERIOD_TIMES: Record<number, string> = {
  1: "07:00", 2: "07:55", 3: "08:50", 4: "09:50", 5: "10:45",
  6: "11:40", 7: "13:00", 8: "13:55", 9: "14:50", 10: "15:50",
  11: "16:45", 12: "17:40", 13: "18:00", 14: "18:55", 15: "19:50",
};
const PERIODS = Array.from({ length: 15 }, (_, i) => i + 1);
const DAYS_VI = ["", "", "Thứ 2", "Thứ 3", "Thứ 4", "Thứ 5", "Thứ 6", "Thứ 7", "Chủ Nhật"];
const DAY_VALUES = [2, 3, 4, 5, 6, 7, 8]; // 2=Mon, 8=Sun

// Stable color palette for courses
const COURSE_COLORS = [
  "bg-blue-100 border-blue-400 text-blue-900",
  "bg-emerald-100 border-emerald-400 text-emerald-900",
  "bg-amber-100 border-amber-400 text-amber-900",
  "bg-pink-100 border-pink-400 text-pink-900",
  "bg-indigo-100 border-indigo-400 text-indigo-900",
  "bg-rose-100 border-rose-400 text-rose-900",
  "bg-cyan-100 border-cyan-400 text-cyan-900",
  "bg-violet-100 border-violet-400 text-violet-900",
];

function hashCode(s: string): number {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (h * 31 + s.charCodeAt(i)) | 0;
  return Math.abs(h);
}
function courseColor(code: string): string {
  return COURSE_COLORS[hashCode(code) % COURSE_COLORS.length];
}

export default function SchedulePage() {
  const [tab, setTab] = useState<Tab>("week");
  const [loading, setLoading] = useState(true);

  const [timetable, setTimetable] = useState<TimetableSession[]>([]);
  const [week1Monday, setWeek1Monday] = useState<string | null>(null);
  const [semester, setSemester] = useState<string>("");
  const [exams, setExams] = useState<ExamEntry[]>([]);
  const [personalEvents, setPersonalEvents] = useState<PersonalEvent[]>([]);
  const [adminEvents, setAdminEvents] = useState<EventResponse[]>([]);

  const [tkbModalOpen, setTkbModalOpen] = useState(false);
  const [examModalOpen, setExamModalOpen] = useState(false);
  const [eventModalOpen, setEventModalOpen] = useState(false);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const [tkbR, examR, peR, evR] = await Promise.all([
        studentApi.getTimetable().catch(() => null),
        studentApi.getExamSchedule().catch(() => null),
        studentApi.listPersonalEvents().catch(() => null),
        eventsApi.myUpcoming(50).catch(() => null),
      ]);
      if (tkbR) {
        setTimetable(tkbR.data.sessions || []);
        setSemester(tkbR.data.semester || "");
        setWeek1Monday(tkbR.data.week_1_monday || null);
      }
      if (examR) setExams(examR.data.exams || []);
      if (peR) setPersonalEvents(peR.data.items || []);
      if (evR) setAdminEvents(evR.data || []);
    } finally {
      setLoading(false);
    }
  }, []);

  const handleDeleteSessions: DeleteSessionFn = useCallback(async (params) => {
    try {
      await studentApi.deleteTimetableSessions(params);
      toast.success("Đã xóa khỏi TKB");
      await reload();
    } catch {
      toast.error("Xóa thất bại");
    }
  }, [reload]);

  const handleDeleteExam: DeleteExamFn = useCallback(async (params) => {
    try {
      await studentApi.deleteExamEntries(params);
      toast.success("Đã xóa lịch thi");
      await reload();
    } catch {
      toast.error("Xóa thất bại");
    }
  }, [reload]);

  useEffect(() => { reload(); }, [reload]);

  const sessionsWithSchedule = useMemo(
    () => timetable.filter((s) => s.day_of_week != null && s.start_period != null),
    [timetable]
  );
  const sessionsNoSchedule = useMemo(
    () => timetable.filter((s) => s.day_of_week == null || s.start_period == null),
    [timetable]
  );

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between gap-3 flex-wrap">
        <div>
          <h1 className="text-2xl font-bold text-primary flex items-center gap-2">
            <CalendarDays className="h-6 w-6" /> Thời khóa biểu và
          </h1>
          <p className="text-muted-foreground text-sm mt-0.5">
            Quản lý thời khóa biểu, lịch thi và các sự kiện học vụ {semester && <Badge variant="outline" className="ml-2">HK {semester}</Badge>}
          </p>
        </div>
        <div className="flex gap-2 flex-wrap">
          <Button variant="outline" size="sm" onClick={() => setEventModalOpen(true)}>
            <Plus className="h-4 w-4 mr-1.5" /> Thêm sự kiện
          </Button>
          <Button variant="outline" size="sm" onClick={() => setExamModalOpen(true)}>
            <Upload className="h-4 w-4 mr-1.5" /> Import Lịch thi
          </Button>
          <Button size="sm" onClick={() => setTkbModalOpen(true)}>
            <Upload className="h-4 w-4 mr-1.5" /> Import TKB
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 bg-muted/40 p-1 rounded-lg w-fit">
        {([
          ["week", "Tuần", CalendarDays],
          ["month", "Tháng", CalendarDays],
          ["list", "Danh sách", ListTodo],
        ] as const).map(([k, label, Icon]) => (
          <button
            key={k}
            onClick={() => setTab(k)}
            className={`px-4 py-1.5 rounded-md text-sm flex items-center gap-1.5 transition-colors ${
              tab === k ? "bg-white shadow-sm font-medium text-primary" : "text-muted-foreground hover:text-foreground"
            }`}
          >
            <Icon className="h-3.5 w-3.5" /> {label}
          </button>
        ))}
      </div>

      {loading ? (
        <SkeletonCard />
      ) : (
        <>
          {tab === "week" && (
            <WeekView
              sessions={sessionsWithSchedule}
              noScheduleSessions={sessionsNoSchedule}
              onDeleteSessions={handleDeleteSessions}
            />
          )}
          {tab === "month" && (
            <MonthView
              exams={exams}
              adminEvents={adminEvents}
              personalEvents={personalEvents}
              sessions={sessionsWithSchedule}
              week1Monday={week1Monday}
              onDeletePersonal={async (id) => {
                await studentApi.deletePersonalEvent(id);
                toast.success("Đã xóa sự kiện");
                reload();
              }}
              onDeleteSessions={handleDeleteSessions}
              onDeleteExam={handleDeleteExam}
            />
          )}
          {tab === "list" && (
            <UpcomingList
              exams={exams}
              adminEvents={adminEvents}
              personalEvents={personalEvents}
              onDeletePersonal={async (id) => {
                await studentApi.deletePersonalEvent(id);
                toast.success("Đã xóa sự kiện");
                reload();
              }}
              onDeleteExam={handleDeleteExam}
            />
          )}
        </>
      )}

      {/* Modals */}
      <ImportTkbModal open={tkbModalOpen} onClose={() => setTkbModalOpen(false)} onDone={reload} />
      <ImportExamModal open={examModalOpen} onClose={() => setExamModalOpen(false)} onDone={reload} />
      <AddPersonalEventModal open={eventModalOpen} onClose={() => setEventModalOpen(false)} onDone={reload} />
    </div>
  );
}

// ───────────────────────────────────────────────────────────────
// Week View
// ───────────────────────────────────────────────────────────────
type DeleteSessionFn = (params: { course_code: string; group?: string; day_of_week?: number; start_period?: number }) => Promise<void>;
type DeleteExamFn = (params: { course_code: string; exam_date?: string; exam_type?: string }) => Promise<void>;

function WeekView({
  sessions, noScheduleSessions, onDeleteSessions,
}: {
  sessions: TimetableSession[];
  noScheduleSessions: TimetableSession[];
  onDeleteSessions: DeleteSessionFn;
}) {
  const [deleteTarget, setDeleteTarget] = useState<TimetableSession | null>(null);

  const grid = useMemo(() => {
    const g: Record<string, TimetableSession & { isStart: boolean; span: number }> = {};
    for (const s of sessions) {
      if (s.day_of_week == null || s.start_period == null || s.end_period == null) continue;
      const span = s.end_period - s.start_period + 1;
      for (let p = s.start_period; p <= s.end_period; p++) {
        g[`${s.day_of_week}-${p}`] = { ...s, isStart: p === s.start_period, span };
      }
    }
    return g;
  }, [sessions]);

  if (sessions.length === 0 && noScheduleSessions.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground">
          <CalendarDays className="h-12 w-12 mx-auto mb-3 opacity-40" />
          <p className="font-medium">Chưa có thời khóa biểu</p>
          <p className="text-sm mt-1">Nhấn &quot;Import TKB&quot; để dán TKB từ myBK vào hệ thống</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <>
      <div className="space-y-4">
        <Card>
          <CardContent className="p-0 overflow-x-auto">
            <table className="w-full text-xs border-collapse">
              <thead className="bg-muted/40">
                <tr>
                  <th className="w-20 px-2 py-2 border text-muted-foreground font-medium">Tiết</th>
                  {DAY_VALUES.map((d) => (
                    <th key={d} className="px-2 py-2 border text-foreground font-medium">{DAYS_VI[d]}</th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {PERIODS.map((p) => (
                  <tr key={p}>
                    <td className="border px-2 py-1 text-center bg-muted/20">
                      <div className="font-medium">{p}</div>
                      <div className="text-muted-foreground text-[10px]">{PERIOD_TIMES[p]}</div>
                    </td>
                    {DAY_VALUES.map((d) => {
                      const key = `${d}-${p}`;
                      const cell = grid[key];
                      if (!cell) return <td key={d} className="border h-12"></td>;
                      if (!cell.isStart) return null;
                      return (
                        <td
                          key={d}
                          rowSpan={cell.span}
                          className={`border-2 px-2 py-1.5 align-top relative group ${courseColor(cell.course_code)}`}
                        >
                          <button
                            onClick={() => setDeleteTarget(cell)}
                            className="absolute top-1 right-1 hidden group-hover:flex items-center justify-center w-4 h-4 rounded-full bg-white/80 hover:bg-red-100 text-red-500 shadow-sm"
                            title="Xóa khỏi TKB"
                          >
                            <X className="w-2.5 h-2.5" />
                          </button>
                          <div className="font-semibold text-xs leading-tight">{cell.course_code}</div>
                          <div className="text-[11px] mt-0.5 leading-tight line-clamp-2">{cell.course_name}</div>
                          <div className="text-[10px] mt-1 opacity-80">
                            📍 {cell.room} · {cell.start_time}–{cell.end_time}
                          </div>
                          <div className="text-[10px] opacity-70">Nhóm {cell.group}</div>
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </CardContent>
        </Card>

        {noScheduleSessions.length > 0 && (
          <Card>
            <CardHeader className="pb-2">
              <CardTitle className="text-sm">Môn không có lịch cố định ({noScheduleSessions.length})</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {noScheduleSessions.map((s) => (
                  <div key={`${s.course_code}-${s.group}`} className={`p-3 rounded border-2 relative group ${courseColor(s.course_code)}`}>
                    <button
                      onClick={() => setDeleteTarget(s)}
                      className="absolute top-1 right-1 hidden group-hover:flex items-center justify-center w-5 h-5 rounded-full bg-white/80 hover:bg-red-100 text-red-500 shadow-sm"
                      title="Xóa khỏi TKB"
                    >
                      <X className="w-3 h-3" />
                    </button>
                    <div className="font-semibold text-sm">{s.course_code}</div>
                    <div className="text-xs mt-0.5">{s.course_name}</div>
                    <div className="text-xs opacity-70 mt-1">Nhóm {s.group} · {s.credits} TC</div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {deleteTarget && (
        <DeleteSessionDialog
          session={deleteTarget}
          onClose={() => setDeleteTarget(null)}
          onDeleteOne={async () => {
            await onDeleteSessions({
              course_code: deleteTarget.course_code,
              group: deleteTarget.group,
              day_of_week: deleteTarget.day_of_week ?? undefined,
              start_period: deleteTarget.start_period ?? undefined,
            });
            setDeleteTarget(null);
          }}
          onDeleteAll={async () => {
            await onDeleteSessions({ course_code: deleteTarget.course_code });
            setDeleteTarget(null);
          }}
        />
      )}
    </>
  );
}

// ───────────────────────────────────────────────────────────────
// Delete Session Confirm Dialog
// ───────────────────────────────────────────────────────────────
function DeleteSessionDialog({
  session, onClose, onDeleteOne, onDeleteAll,
}: {
  session: TimetableSession;
  onClose: () => void;
  onDeleteOne: () => Promise<void>;
  onDeleteAll: () => Promise<void>;
}) {
  const [busy, setBusy] = useState(false);
  const dayLabel = session.day_of_week != null ? DAYS_VI[session.day_of_week] : null;
  const periodLabel = session.start_period != null
    ? `tiết ${session.start_period}${session.end_period && session.end_period !== session.start_period ? `–${session.end_period}` : ""}`
    : null;

  const run = async (fn: () => Promise<void>) => {
    setBusy(true);
    try { await fn(); } finally { setBusy(false); }
  };

  return (
    <Dialog open onOpenChange={(o) => { if (!o && !busy) onClose(); }}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Trash2 className="h-4 w-4 text-destructive" /> Xóa khỏi TKB
          </DialogTitle>
        </DialogHeader>
        <p className="text-sm text-muted-foreground">
          Môn <strong>{session.course_code}</strong> — {session.course_name}
          {dayLabel && periodLabel && <> · {dayLabel} {periodLabel}</>}
        </p>
        <div className="flex flex-col gap-2 pt-1">
          {session.day_of_week != null && (
            <Button
              variant="outline"
              className="justify-start text-sm"
              disabled={busy}
              onClick={() => run(onDeleteOne)}
            >
              <X className="h-4 w-4 mr-2 text-orange-500" />
              Xóa buổi {dayLabel} {periodLabel} của nhóm {session.group}
            </Button>
          )}
          <Button
            variant="destructive"
            className="justify-start text-sm"
            disabled={busy}
            onClick={() => run(onDeleteAll)}
          >
            <Trash2 className="h-4 w-4 mr-2" />
            Xóa toàn bộ môn {session.course_code} khỏi TKB
          </Button>
          <Button variant="ghost" onClick={onClose} disabled={busy}>Hủy</Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

// ───────────────────────────────────────────────────────────────
// Month View
// ───────────────────────────────────────────────────────────────
function MonthView({
  exams, adminEvents, personalEvents, sessions, week1Monday, onDeletePersonal, onDeleteSessions, onDeleteExam,
}: {
  exams: ExamEntry[];
  adminEvents: EventResponse[];
  personalEvents: PersonalEvent[];
  sessions: TimetableSession[];
  week1Monday: string | null;
  onDeletePersonal: (id: string) => Promise<void>;
  onDeleteSessions: DeleteSessionFn;
  onDeleteExam: DeleteExamFn;
}) {
  const [cursor, setCursor] = useState(() => {
    const now = new Date();
    return { year: now.getFullYear(), month: now.getMonth() };
  });
  const [selectedDay, setSelectedDay] = useState<string | null>(null);

  const firstDay = new Date(cursor.year, cursor.month, 1);
  const lastDay = new Date(cursor.year, cursor.month + 1, 0);
  const startOffset = (firstDay.getDay() + 6) % 7; // Mon=0
  const daysInMonth = lastDay.getDate();
  const today = new Date();
  const todayKey = `${today.getFullYear()}-${String(today.getMonth() + 1).padStart(2, "0")}-${String(today.getDate()).padStart(2, "0")}`;

  // Index events by date — includes recurring TKB classes if week1Monday is known
  const dayEvents = useMemo(() => {
    const map: Record<string, { exams: ExamEntry[]; admin: EventResponse[]; personal: PersonalEvent[]; classes: TimetableSession[] }> = {};
    const add = (
      key: string,
      type: "exams" | "admin" | "personal" | "classes",
      value: ExamEntry | EventResponse | PersonalEvent | TimetableSession,
    ) => {
      if (!map[key]) map[key] = { exams: [], admin: [], personal: [], classes: [] };
      if (type === "exams") map[key].exams.push(value as ExamEntry);
      else if (type === "admin") map[key].admin.push(value as EventResponse);
      else if (type === "personal") map[key].personal.push(value as PersonalEvent);
      else map[key].classes.push(value as TimetableSession);
    };
    exams.forEach((e) => add(e.exam_date, "exams", e));
    adminEvents.forEach((e) => {
      const dt = new Date(e.start_time);
      const k = `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, "0")}-${String(dt.getDate()).padStart(2, "0")}`;
      add(k, "admin", e);
    });
    personalEvents.forEach((e) => {
      const dt = new Date(e.start_time);
      const k = `${dt.getFullYear()}-${String(dt.getMonth() + 1).padStart(2, "0")}-${String(dt.getDate()).padStart(2, "0")}`;
      add(k, "personal", e);
    });

    // Expand recurring TKB classes onto each active week's day
    if (week1Monday) {
      const w1 = new Date(`${week1Monday}T00:00:00`);
      sessions.forEach((s) => {
        if (s.day_of_week == null || !s.active_weeks?.length) return;
        s.active_weeks.forEach((wk) => {
          const d = new Date(w1);
          // day_of_week: 2=Mon..7=Sat, 8=Sun → offset from Monday
          const dayOffset = s.day_of_week === 8 ? 6 : (s.day_of_week as number) - 2;
          d.setDate(d.getDate() + (wk - 1) * 7 + dayOffset);
          const k = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
          add(k, "classes", s);
        });
      });
    }

    return map;
  }, [exams, adminEvents, personalEvents, sessions, week1Monday]);

  const monthName = new Date(cursor.year, cursor.month, 1).toLocaleDateString("vi-VN", { month: "long", year: "numeric" });

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between pb-3">
        <CardTitle className="text-base capitalize">{monthName}</CardTitle>
        <div className="flex gap-1">
          <Button variant="ghost" size="sm" onClick={() => setCursor((c) => ({ year: c.month === 0 ? c.year - 1 : c.year, month: (c.month + 11) % 12 }))}>
            <ChevronLeft className="h-4 w-4" />
          </Button>
          <Button variant="ghost" size="sm" onClick={() => { const now = new Date(); setCursor({ year: now.getFullYear(), month: now.getMonth() }); }}>
            Hôm nay
          </Button>
          <Button variant="ghost" size="sm" onClick={() => setCursor((c) => ({ year: c.month === 11 ? c.year + 1 : c.year, month: (c.month + 1) % 12 }))}>
            <ChevronRight className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-7 gap-1 text-xs">
          {["T2", "T3", "T4", "T5", "T6", "T7", "CN"].map((d) => (
            <div key={d} className="text-center font-medium text-muted-foreground pb-2">{d}</div>
          ))}
          {Array.from({ length: startOffset }).map((_, i) => <div key={`pad-${i}`} />)}
          {Array.from({ length: daysInMonth }).map((_, i) => {
            const day = i + 1;
            const key = `${cursor.year}-${String(cursor.month + 1).padStart(2, "0")}-${String(day).padStart(2, "0")}`;
            const evs = dayEvents[key];
            const isToday = key === todayKey;
            return (
              <button
                key={key}
                onClick={() => setSelectedDay(key)}
                className={`min-h-[80px] p-1.5 rounded border text-left transition-colors hover:bg-muted/40 ${
                  isToday ? "border-primary bg-primary/5" : "border-border"
                }`}
              >
                <div className={`font-medium text-sm ${isToday ? "text-primary" : ""}`}>{day}</div>
                {evs && (
                  <div className="space-y-0.5 mt-1">
                    {evs.classes.slice(0, 2).map((s, idx) => (
                      <div key={`c${idx}`} className={`text-[10px] truncate px-1 py-0.5 rounded ${courseColor(s.course_code)}`}>
                        <span className="font-medium">{s.course_code}</span>
                        {s.course_name && <span className="opacity-75"> · {s.course_name}</span>}
                        {s.start_time && <span className="opacity-60"> {s.start_time}</span>}
                      </div>
                    ))}
                    {evs.classes.length > 2 && (
                      <div className="text-[10px] text-muted-foreground px-1">+{evs.classes.length - 2} lớp</div>
                    )}
                    {evs.exams.map((e, idx) => (
                      <div key={`x${idx}`} className={`text-[10px] truncate px-1 py-0.5 rounded ${e.exam_type === "CK" ? "bg-red-100 text-red-800" : "bg-orange-100 text-orange-800"}`}>
                        {e.exam_type} {e.course_code}
                      </div>
                    ))}
                    {evs.admin.map((e, idx) => (
                      <div key={`a${idx}`} className="text-[10px] truncate px-1 py-0.5 rounded bg-blue-100 text-blue-800">
                        {e.title}
                      </div>
                    ))}
                    {evs.personal.map((e, idx) => (
                      <div key={`p${idx}`} className="text-[10px] truncate px-1 py-0.5 rounded bg-purple-100 text-purple-800">
                        {e.title}
                      </div>
                    ))}
                  </div>
                )}
              </button>
            );
          })}
        </div>

        {selectedDay && (
          <DayDetailDialog
            dayKey={selectedDay}
            events={dayEvents[selectedDay]}
            onClose={() => setSelectedDay(null)}
            onDeletePersonal={onDeletePersonal}
            onDeleteSessions={onDeleteSessions}
            onDeleteExam={onDeleteExam}
          />
        )}
      </CardContent>
    </Card>
  );
}

function DayDetailDialog({
  dayKey, events, onClose, onDeletePersonal, onDeleteSessions, onDeleteExam,
}: {
  dayKey: string;
  events?: { exams: ExamEntry[]; admin: EventResponse[]; personal: PersonalEvent[]; classes: TimetableSession[] };
  onClose: () => void;
  onDeletePersonal: (id: string) => Promise<void>;
  onDeleteSessions: DeleteSessionFn;
  onDeleteExam: DeleteExamFn;
}) {
  const date = new Date(dayKey);
  const dateLabel = date.toLocaleDateString("vi-VN", { weekday: "long", day: "numeric", month: "long", year: "numeric" });
  const hasAny = events && (events.exams.length + events.admin.length + events.personal.length + events.classes.length) > 0;

  return (
    <Dialog open onOpenChange={(o: boolean) => { if (!o) onClose(); }}>
      <DialogContent className="max-w-md max-h-[80vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="capitalize">{dateLabel}</DialogTitle>
        </DialogHeader>
        {!hasAny && (
          <p className="text-sm text-muted-foreground py-6 text-center">Không có sự kiện nào</p>
        )}
        {events?.classes.map((s, idx) => (
          <div key={`c${idx}`} className={`p-3 rounded border-2 ${courseColor(s.course_code)}`}>
            <div className="flex items-center gap-2 flex-wrap">
              <Badge variant="outline">Lớp học</Badge>
              <span className="font-semibold text-sm">{s.course_code}</span>
              <span className="text-xs">Nhóm {s.group}</span>
            </div>
            <p className="text-sm mt-1">{s.course_name}</p>
            <p className="text-xs opacity-80 mt-1">
              🕐 Tiết {s.start_period}–{s.end_period} ({s.start_time}–{s.end_time}) · 📍 {s.room} ({s.campus})
            </p>
            <div className="flex gap-2 mt-2">
              <Button
                size="sm" variant="outline"
                className="text-xs h-7 px-2 text-orange-700 border-orange-300 hover:bg-orange-50"
                onClick={() => onDeleteSessions({
                  course_code: s.course_code, group: s.group,
                  day_of_week: s.day_of_week ?? undefined, start_period: s.start_period ?? undefined,
                }).then(onClose)}
              >
                <X className="h-3 w-3 mr-1" /> Xóa buổi này
              </Button>
              <Button
                size="sm" variant="outline"
                className="text-xs h-7 px-2 text-destructive border-destructive/30 hover:bg-red-50"
                onClick={() => onDeleteSessions({ course_code: s.course_code }).then(onClose)}
              >
                <Trash2 className="h-3 w-3 mr-1" /> Xóa cả môn
              </Button>
            </div>
          </div>
        ))}
        {events?.exams.map((e, idx) => (
          <div key={`x${idx}`} className={`p-3 rounded border-l-4 ${e.exam_type === "CK" ? "border-l-red-600 bg-red-50" : "border-l-orange-500 bg-orange-50"}`}>
            <div className="flex items-center gap-2">
              <Badge variant={e.exam_type === "CK" ? "destructive" : "secondary"}>{e.exam_type === "CK" ? "Cuối kỳ" : "Giữa kỳ"}</Badge>
              <span className="font-semibold text-sm">{e.course_code}</span>
            </div>
            <p className="text-sm mt-1">{e.course_name}</p>
            <p className="text-xs text-muted-foreground mt-1">🕐 {e.start_time} ({e.duration_min} phút) · 📍 {e.room} ({e.campus})</p>
            <p className="text-xs text-muted-foreground">Nhóm {e.group}</p>
            <div className="flex gap-2 mt-2">
              <Button
                size="sm" variant="outline"
                className="text-xs h-7 px-2 text-orange-700 border-orange-300 hover:bg-orange-50"
                onClick={() => onDeleteExam({ course_code: e.course_code, exam_date: e.exam_date, exam_type: e.exam_type }).then(onClose)}
              >
                <X className="h-3 w-3 mr-1" /> Xóa lịch thi này
              </Button>
              <Button
                size="sm" variant="outline"
                className="text-xs h-7 px-2 text-destructive border-destructive/30 hover:bg-red-50"
                onClick={() => onDeleteExam({ course_code: e.course_code }).then(onClose)}
              >
                <Trash2 className="h-3 w-3 mr-1" /> Xóa cả môn
              </Button>
            </div>
          </div>
        ))}
        {events?.admin.map((e, idx) => (
          <div key={`a${idx}`} className="p-3 rounded border-l-4 border-l-blue-500 bg-blue-50">
            <div className="flex items-center gap-2 flex-wrap">
              <Badge>{e.event_type}</Badge>
              {e.is_mandatory && <Badge variant="destructive">Bắt buộc</Badge>}
              <span className="font-semibold text-sm">{e.title}</span>
            </div>
            <p className="text-xs text-muted-foreground mt-1">🕐 {new Date(e.start_time).toLocaleString("vi-VN")}</p>
            {e.description && <p className="text-xs text-foreground mt-1">{e.description}</p>}
          </div>
        ))}
        {events?.personal.map((e, idx) => (
          <div key={`p${idx}`} className="p-3 rounded border-l-4 border-l-purple-500 bg-purple-50">
            <div className="flex items-center justify-between">
              <div className="flex-1">
                <span className="font-semibold text-sm">{e.title}</span>
                <p className="text-xs text-muted-foreground mt-1">🕐 {new Date(e.start_time).toLocaleString("vi-VN")}</p>
                {e.description && <p className="text-xs text-foreground mt-1">{e.description}</p>}
              </div>
              <Button variant="ghost" size="sm" onClick={() => onDeletePersonal(e.id)}>
                <Trash2 className="h-4 w-4 text-destructive" />
              </Button>
            </div>
          </div>
        ))}
      </DialogContent>
    </Dialog>
  );
}

// ───────────────────────────────────────────────────────────────
// Upcoming List
// ───────────────────────────────────────────────────────────────
function UpcomingList({
  exams, adminEvents, personalEvents, onDeletePersonal, onDeleteExam,
}: {
  exams: ExamEntry[];
  adminEvents: EventResponse[];
  personalEvents: PersonalEvent[];
  onDeletePersonal: (id: string) => Promise<void>;
  onDeleteExam: DeleteExamFn;
}) {
  type Item = { date: Date; type: "exam" | "admin" | "personal"; data: ExamEntry | EventResponse | PersonalEvent };
  const items = useMemo<Item[]>(() => {
    const now = new Date();
    now.setHours(0, 0, 0, 0);
    const all: Item[] = [
      ...exams.map((e) => ({ date: new Date(`${e.exam_date}T${e.start_time}:00`), type: "exam" as const, data: e })),
      ...adminEvents.map((e) => ({ date: new Date(e.start_time), type: "admin" as const, data: e })),
      ...personalEvents.map((e) => ({ date: new Date(e.start_time), type: "personal" as const, data: e })),
    ];
    return all.filter((i) => i.date >= now).sort((a, b) => a.date.getTime() - b.date.getTime());
  }, [exams, adminEvents, personalEvents]);

  if (items.length === 0) {
    return (
      <Card>
        <CardContent className="py-12 text-center text-muted-foreground">
          <ListTodo className="h-12 w-12 mx-auto mb-3 opacity-40" />
          <p className="font-medium">Không có sự kiện sắp tới</p>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card>
      <CardContent className="pt-6 space-y-2">
        {items.map((item, idx) => {
          const dateLabel = item.date.toLocaleDateString("vi-VN", { weekday: "short", day: "2-digit", month: "2-digit" });
          const timeLabel = item.date.toLocaleTimeString("vi-VN", { hour: "2-digit", minute: "2-digit" });
          if (item.type === "exam") {
            const e = item.data as ExamEntry;
            return (
              <div key={idx} className={`flex items-start gap-3 p-3 rounded border-l-4 ${e.exam_type === "CK" ? "border-l-red-600 bg-red-50/40" : "border-l-orange-500 bg-orange-50/40"}`}>
                <div className="text-center shrink-0 w-16">
                  <div className="text-xs text-muted-foreground">{dateLabel}</div>
                  <div className="font-semibold">{timeLabel}</div>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <Badge variant={e.exam_type === "CK" ? "destructive" : "secondary"}>{e.exam_type === "CK" ? "Cuối kỳ" : "Giữa kỳ"}</Badge>
                    <span className="font-semibold text-sm">{e.course_code} — {e.course_name}</span>
                  </div>
                  <p className="text-xs text-muted-foreground mt-0.5">📍 {e.room} · {e.duration_min} phút · Nhóm {e.group}</p>
                </div>
                <Button
                  variant="ghost" size="sm"
                  className="shrink-0 text-muted-foreground hover:text-destructive"
                  onClick={() => onDeleteExam({ course_code: e.course_code, exam_date: e.exam_date, exam_type: e.exam_type })}
                  title="Xóa lịch thi này"
                >
                  <Trash2 className="h-4 w-4" />
                </Button>
              </div>
            );
          }
          if (item.type === "admin") {
            const e = item.data as EventResponse;
            return (
              <div key={idx} className="flex items-start gap-3 p-3 rounded border-l-4 border-l-blue-500 bg-blue-50/40">
                <div className="text-center shrink-0 w-16">
                  <div className="text-xs text-muted-foreground">{dateLabel}</div>
                  <div className="font-semibold">{timeLabel}</div>
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <Badge>{e.event_type}</Badge>
                    {e.is_mandatory && <Badge variant="destructive">Bắt buộc</Badge>}
                    <span className="font-semibold text-sm">{e.title}</span>
                  </div>
                  {e.description && <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{e.description}</p>}
                </div>
              </div>
            );
          }
          const e = item.data as PersonalEvent;
          return (
            <div key={idx} className="flex items-start gap-3 p-3 rounded border-l-4 border-l-purple-500 bg-purple-50/40">
              <div className="text-center shrink-0 w-16">
                <div className="text-xs text-muted-foreground">{dateLabel}</div>
                <div className="font-semibold">{timeLabel}</div>
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <Pencil className="h-3.5 w-3.5 text-purple-600" />
                  <span className="font-semibold text-sm">{e.title}</span>
                </div>
                {e.description && <p className="text-xs text-muted-foreground mt-0.5 line-clamp-2">{e.description}</p>}
              </div>
              <Button variant="ghost" size="sm" onClick={() => onDeletePersonal(e.id)}>
                <Trash2 className="h-4 w-4 text-destructive" />
              </Button>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}

// ───────────────────────────────────────────────────────────────
// Modals
// ───────────────────────────────────────────────────────────────
function ImportTkbModal({ open, onClose, onDone }: { open: boolean; onClose: () => void; onDone: () => Promise<void> }) {
  const [text, setText] = useState("");
  const [merge, setMerge] = useState(true);
  const [busy, setBusy] = useState(false);

  const handleImport = async () => {
    if (!text.trim()) { toast.warning("Hãy paste TKB từ myBK vào ô bên dưới"); return; }
    setBusy(true);
    try {
      const r = await studentApi.importTimetable(text, merge);
      const action = merge ? "Gộp thêm" : "Import";
      toast.success(`${action} ${r.data.sessions_count} buổi học · Tạo ${r.data.enrollments_created} enrollment cho HK ${r.data.semester}`);
      setText("");
      onClose();
      await onDone();
    } catch (err: unknown) {
      const msg = (err && typeof err === "object" && "response" in err
        ? ((err as { response?: { data?: { detail?: string } } }).response?.data?.detail)
        : null) || "Import thất bại";
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(o: boolean) => { if (!o) onClose(); }}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><Sparkles className="h-5 w-5 text-primary" /> Import Thời Khóa Biểu từ myBK</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div className="bg-blue-50 border border-blue-200 rounded p-3 text-xs text-blue-900 space-y-1">
            <p className="font-semibold">📋 Hướng dẫn:</p>
            <ol className="list-decimal pl-4 space-y-0.5">
              <li>Đăng nhập <strong>mybk.hcmut.edu.vn</strong> → Sinh viên → <strong>Thời khóa biểu Học kỳ</strong></li>
              <li>Chọn học kỳ hiện tại, đảm bảo thấy đủ bảng (kéo dropdown &quot;Trình bày&quot; lên 100 dòng nếu cần)</li>
              <li>Bôi đen toàn bộ bảng (cả dòng header), Ctrl+C</li>
              <li>Paste vào ô bên dưới</li>
            </ol>
            <p className="text-blue-700">Hệ thống sẽ tạo các môn này thành enrollment cho HK hiện tại với trạng thái &quot;đang học&quot;.</p>
          </div>

          <label className="flex items-center gap-2 cursor-pointer select-none">
            <input
              type="checkbox"
              checked={merge}
              onChange={(e) => setMerge(e.target.checked)}
              className="w-4 h-4 accent-primary"
            />
            <span className="text-sm">
              <strong>Cập nhật TKB</strong>
              <span className="text-muted-foreground ml-1">
                {merge
                  ? "— giữ nguyên các môn cũ, thêm môn mới"
                  : "— xóa TKB cũ và thay bằng dữ liệu mới paste"}
              </span>
            </span>
          </label>

          <textarea
            className="w-full border rounded p-3 font-mono text-xs"
            rows={12}
            placeholder="Paste TKB ở đây..."
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <div className="flex gap-2 justify-end">
            <Button variant="outline" onClick={onClose} disabled={busy}>Hủy</Button>
            <Button onClick={handleImport} disabled={busy || !text.trim()}>
              {busy ? "Đang import..." : merge ? "Gộp TKB" : "Import TKB"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function ImportExamModal({ open, onClose, onDone }: { open: boolean; onClose: () => void; onDone: () => Promise<void> }) {
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);

  const handleImport = async () => {
    if (!text.trim()) { toast.warning("Hãy paste lịch thi từ myBK"); return; }
    setBusy(true);
    try {
      const r = await studentApi.importExamSchedule(text);
      toast.success(`Đã import ${r.data.exams_count} bài thi cho HK ${r.data.semester}`);
      setText("");
      onClose();
      await onDone();
    } catch (err: unknown) {
      const msg = (err && typeof err === "object" && "response" in err
        ? ((err as { response?: { data?: { detail?: string } } }).response?.data?.detail)
        : null) || "Import thất bại";
      toast.error(msg);
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(o: boolean) => { if (!o) onClose(); }}>
      <DialogContent className="max-w-2xl max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><Sparkles className="h-5 w-5 text-orange-500" /> Import Lịch Kiểm tra - Thi từ myBK</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div className="bg-orange-50 border border-orange-200 rounded p-3 text-xs text-orange-900 space-y-1">
            <p className="font-semibold">📋 Hướng dẫn:</p>
            <ol className="list-decimal pl-4 space-y-0.5">
              <li>Đăng nhập <strong>mybk.hcmut.edu.vn</strong> → Sinh viên → <strong>Lịch kiểm tra - Thi Học kỳ</strong></li>
              <li>Bôi đen toàn bảng, Ctrl+C</li>
              <li>Paste vào ô bên dưới</li>
            </ol>
            <p className="text-orange-700">Hệ thống tự phân biệt thi <strong>GK</strong> (giữa kỳ) và <strong>CK</strong> (cuối kỳ).</p>
          </div>
          <textarea
            className="w-full border rounded p-3 font-mono text-xs"
            rows={10}
            placeholder="Paste lịch thi ở đây..."
            value={text}
            onChange={(e) => setText(e.target.value)}
          />
          <div className="flex gap-2 justify-end">
            <Button variant="outline" onClick={onClose} disabled={busy}>Hủy</Button>
            <Button onClick={handleImport} disabled={busy || !text.trim()}>
              {busy ? "Đang import..." : "Import lịch thi"}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function AddPersonalEventModal({ open, onClose, onDone }: { open: boolean; onClose: () => void; onDone: () => Promise<void> }) {
  const [title, setTitle] = useState("");
  const [date, setDate] = useState("");
  const [time, setTime] = useState("");
  const [description, setDescription] = useState("");
  const [busy, setBusy] = useState(false);

  const reset = () => { setTitle(""); setDate(""); setTime(""); setDescription(""); };

  const handleSubmit = async () => {
    if (!title.trim()) { toast.warning("Nhập tên sự kiện"); return; }
    if (!date) { toast.warning("Chọn ngày"); return; }
    const startISO = new Date(`${date}T${time || "08:00"}:00`).toISOString();
    setBusy(true);
    try {
      await studentApi.createPersonalEvent({
        title: title.trim(),
        start_time: startISO,
        description: description.trim() || null,
        color: "purple",
      });
      toast.success("Đã thêm sự kiện");
      reset();
      onClose();
      await onDone();
    } catch {
      toast.error("Không thêm được sự kiện");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(o: boolean) => { if (!o) { reset(); onClose(); } }}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2"><Plus className="h-5 w-5 text-purple-600" /> Thêm sự kiện cá nhân</DialogTitle>
        </DialogHeader>
        <div className="space-y-3">
          <div>
            <label className="text-xs font-medium text-muted-foreground">Tên sự kiện *</label>
            <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="VD: Họp nhóm BTL" className="mt-1" />
          </div>
          <div className="grid grid-cols-2 gap-2">
            <div>
              <label className="text-xs font-medium text-muted-foreground">Ngày *</label>
              <Input type="date" value={date} onChange={(e) => setDate(e.target.value)} className="mt-1" />
            </div>
            <div>
              <label className="text-xs font-medium text-muted-foreground">Giờ</label>
              <Input type="time" value={time} onChange={(e) => setTime(e.target.value)} className="mt-1" />
            </div>
          </div>
          <div>
            <label className="text-xs font-medium text-muted-foreground">Ghi chú</label>
            <textarea
              className="w-full border rounded p-2 text-sm mt-1"
              rows={3}
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="Tùy chọn..."
            />
          </div>
          <div className="flex gap-2 justify-end">
            <Button variant="outline" onClick={() => { reset(); onClose(); }} disabled={busy}>Hủy</Button>
            <Button onClick={handleSubmit} disabled={busy}>{busy ? "Đang lưu..." : "Thêm"}</Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
