import axios from "axios";

export const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export const apiClient = axios.create({
  baseURL: API_BASE,
  timeout: 15000,
});

// Attach JWT token from localStorage on every request
apiClient.interceptors.request.use((config) => {
  if (typeof FormData !== "undefined" && config.data instanceof FormData) {
    const headers = config.headers as unknown as {
      delete?: (name: string) => void;
      set?: (name: string, value: unknown) => void;
      [key: string]: unknown;
    };
    headers.delete?.("Content-Type");
    headers.delete?.("content-type");
    delete headers["Content-Type"];
    delete headers["content-type"];
  }

  if (typeof window !== "undefined") {
    const token = localStorage.getItem("access_token");
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
  }
  return config;
});

// Auto-logout on 401, but skip auth endpoints (login/register return 401 for bad credentials)
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const isAuthEndpoint = error.config?.url?.startsWith("/auth/");
    if (error.response?.status === 401 && !isAuthEndpoint && typeof window !== "undefined") {
      localStorage.removeItem("access_token");
      localStorage.removeItem("user");
      window.location.href = "/auth/login";
    }
    return Promise.reject(error);
  }
);

// ─── Auth ────────────────────────────────────────────────────

export interface RegisterPayload {
  email: string;
  password: string;
  mssv: string;
  full_name: string;
  faculty: string;
  major: string;
  cohort: number;
}

export interface LoginPayload {
  email: string;
  password: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
}

export interface UserResponse {
  id: string;
  email: string;
  role: "student" | "admin";
  is_active: boolean;
  created_at: string;
}

export const authApi = {
  register: (payload: RegisterPayload) =>
    apiClient.post<TokenResponse>("/auth/register", payload),

  login: (payload: LoginPayload) =>
    apiClient.post<TokenResponse>("/auth/login", payload),

  me: () => apiClient.get<UserResponse>("/auth/me"),
};

// ─── Student ─────────────────────────────────────────────────

export interface StudentProfile {
  id: string;
  mssv: string;
  full_name: string;
  faculty: string;
  major: string;
  cohort: number;
  gpa_cumulative: number;
  credits_earned: number;
  warning_level: number;
  created_at: string;
}

export interface DashboardData {
  student: StudentProfile;
  current_semester: string | null;
  credits_in_progress: number;
  failed_courses_total: number;
  unresolved_failed_courses?: number;
  semesters_count: number;
}

export interface EnrollmentResponse {
  id: string;
  student_id: string;
  course_id: string;
  semester: string;
  midterm_score: number | null;
  lab_score: number | null;
  other_score: number | null;
  final_score: number | null;
  midterm_weight: number;
  lab_weight: number;
  other_weight: number;
  final_weight: number;
  total_score: number | null;
  grade_letter: string | null;
  status: "enrolled" | "passed" | "failed" | "withdrawn" | "exempt";
  attendance_rate: number | null;
  is_finalized: boolean;
  source: string;
  created_at: string;
  updated_at: string;
  course: CourseResponse;
}

export interface CourseResponse {
  id: string;
  course_code: string;
  name: string;
  credits: number;
  faculty: string;
  created_at: string;
}

export interface GpaPoint {
  semester: string;
  gpa: number;
}

export interface GpaData {
  gpa_cumulative: number;
  credits_earned: number;
  warning_level: number;
  gpa_trend: number;
  semester_gpas: GpaPoint[];
}

export interface GpaHistoryEntry {
  semester: string;
  semester_gpa: number;
  credits_taken: number;
  courses_count: number;
}

export interface GradeUpdate {
  midterm_score?: number | null;
  lab_score?: number | null;
  other_score?: number | null;
  final_score?: number | null;
  attendance_rate?: number | null;
  midterm_weight?: number | null;
  lab_weight?: number | null;
  other_weight?: number | null;
  final_weight?: number | null;
}

export interface EnrollmentCreate {
  course_id: string;
  semester: string;
  midterm_weight?: number;
  lab_weight?: number;
  other_weight?: number;
  final_weight?: number;
}

export interface GradeUpdateOutcome {
  enrollment: EnrollmentResponse;
  warning_created: boolean;
  warning_level: number | null;
  warning_reason: string | null;
  ai_early_warning: boolean;
}

export interface ImportResult {
  message: string;
  semesters: string[];
  created: number;
  updated: number;
  skipped: number;
  total_courses: number;
}

export const studentApi = {
  me: () => apiClient.get<StudentProfile>("/students/me"),

  dashboard: () => apiClient.get<DashboardData>("/students/me/dashboard"),

  enrollments: (semester?: string) =>
    apiClient.get<EnrollmentResponse[]>("/students/me/enrollments", {
      params: semester ? { semester } : undefined,
    }),

  createEnrollment: (payload: EnrollmentCreate) =>
    apiClient.post<EnrollmentResponse>("/students/me/enrollments", payload),

  updateGrades: (enrollmentId: string, payload: GradeUpdate) =>
    apiClient.put<GradeUpdateOutcome>(
      `/students/me/enrollments/${enrollmentId}/grades`,
      payload
    ),

  deleteEnrollment: (enrollmentId: string) =>
    apiClient.delete(`/students/me/enrollments/${enrollmentId}`),

  deleteAllEnrollments: () =>
    apiClient.delete<{ message: string; deleted: number }>(
      "/students/me/enrollments"
    ),

  gpa: () => apiClient.get<GpaData>("/students/me/gpa"),

  gpaHistory: () => apiClient.get<GpaHistoryEntry[]>("/students/me/gpa/history"),

  importMyBK: (rawText: string) =>
    apiClient.post<ImportResult>("/students/me/grades/import-mybk", rawText, {
      headers: { "Content-Type": "text/plain" },
    }),
};

// ─── Predictions ─────────────────────────────────────────────

export interface RiskFactor {
  feature: string;
  label: string;
  impact: number;          // 0-1 normalized
  impact_str: string;      // "+75%" / "-12%"
  direction: "+" | "−";
  shap_value: number;
  raw_value: number;
}

export interface PredictedCourse {
  course_id: string;
  course_code: string;
  course_name: string;
  credits: number;
  pass_probability: number;
}

export interface PredictionResponse {
  id: string;
  semester: string;
  risk_score: number;
  risk_level: "low" | "medium" | "high" | "critical";
  risk_factors: RiskFactor[];
  predicted_courses: PredictedCourse[];
  created_at: string | null;
}

export interface PredictionHistoryEntry {
  created_at: string | null;
  semester: string;
  risk_score: number;
  risk_level: "low" | "medium" | "high" | "critical";
}

export interface SimulateItem {
  enrollment_id: string;
  hypothetical_score: number;
}

export interface SimulateResult {
  original_risk_score: number | null;
  original_risk_level: "low" | "medium" | "high" | "critical" | null;
  simulated_risk_score: number;
  simulated_risk_level: "low" | "medium" | "high" | "critical";
  delta_risk_score: number;
}

export const predictionsApi = {
  me: () => apiClient.get<PredictionResponse>("/predictions/me"),
  history: (limit = 30) =>
    apiClient.get<PredictionHistoryEntry[]>("/predictions/me/history", {
      params: { limit },
    }),
  refresh: () => apiClient.post<PredictionResponse>("/predictions/me/refresh"),
  simulate: (items: SimulateItem[]) =>
    apiClient.post<SimulateResult>("/predictions/me/simulate", items),
};

export const coursesApi = {
  list: (search?: string) =>
    apiClient.get<CourseResponse[]>("/courses", {
      params: search ? { search } : undefined,
    }),

  get: (id: string) => apiClient.get<CourseResponse>(`/courses/${id}`),

  create: (payload: Omit<CourseResponse, "id" | "created_at">) =>
    apiClient.post<CourseResponse>("/courses", payload),
};

// ─── Chatbot / RAG ──────────────────────────────────────────

export interface ChatCitation {
  index: number;
  document_id: string;
  source_file: string;
  filename: string;
  chunk_index: number;
  page_number: number | null;
  snippet: string;
  score: number;
  match_type?: "vector" | "keyword" | "merged";
}

export interface ChatResponse {
  answer: string;
  citations: ChatCitation[];
  provider: string;
  used_personal_context: boolean;
}

export interface ChatMessageResponse {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: ChatCitation[];
  created_at: string;
}

export const chatbotApi = {
  ask: (question: string) =>
    apiClient.post<ChatResponse>("/chatbot/ask", { question }),

  history: () => apiClient.get<ChatMessageResponse[]>("/chatbot/history"),

  clearHistory: () => apiClient.delete<{ deleted: number }>("/chatbot/history"),

  suggestions: () => apiClient.get<{ suggestions: string[] }>("/chatbot/suggestions"),
};

// ─── Admin Documents ────────────────────────────────────────

export interface DocumentGroupResponse {
  source_file: string;
  filename: string;
  chunks_count: number;
  is_active: boolean;
  uploaded_at: string;
  uploaded_by: string | null;
  pages_count: number;
}

export interface DocumentBatchUploadItem {
  filename: string;
  status: "uploaded" | "failed";
  chunks_count: number;
  error: string | null;
}

export interface DocumentBatchUploadResponse {
  uploaded: number;
  failed: number;
  total_chunks: number;
  results: DocumentBatchUploadItem[];
}

export const documentsApi = {
  list: () => apiClient.get<DocumentGroupResponse[]>("/documents"),

  upload: (file: File) => {
    const form = new FormData();
    form.append("file", file);
    return apiClient.post("/documents/upload", form, {
      timeout: 600000,
    });
  },

  uploadBatch: (files: File[]) => {
    const form = new FormData();
    files.forEach((file) => form.append("files", file));
    return apiClient.post<DocumentBatchUploadResponse>("/documents/upload-batch", form, {
      timeout: 600000,
    });
  },

  toggle: (sourceFile: string, isActive: boolean) =>
    apiClient.patch(`/documents/${encodeURIComponent(sourceFile)}`, {
      is_active: isActive,
    }),

  delete: (sourceFile: string) =>
    apiClient.delete(`/documents/${encodeURIComponent(sourceFile)}`),
};

// ─── M6: Warnings ───────────────────────────────────────────

export type WarningCreatedBy = "system" | "admin";

export interface WarningResponse {
  id: string;
  student_id: string;
  level: number;
  semester: string;
  reason: string;
  gpa_at_warning: number;
  ai_risk_score: number | null;
  is_resolved: boolean;
  sent_at: string | null;
  created_by: WarningCreatedBy;
  created_at: string;
}

export const warningsApi = {
  list: () => apiClient.get<WarningResponse[]>("/warnings/me"),
  get: (id: string) => apiClient.get<WarningResponse>(`/warnings/me/${id}`),
  resolve: (id: string, isResolved: boolean) =>
    apiClient.patch<WarningResponse>(`/warnings/me/${id}/resolve`, {
      is_resolved: isResolved,
    }),
};

// ─── M6: Notifications ──────────────────────────────────────

export type NotificationType = "warning" | "reminder" | "event" | "system";

export interface NotificationResponse {
  id: string;
  student_id: string;
  type: NotificationType;
  title: string;
  content: string;
  is_read: boolean;
  sent_at: string;
  email_sent_at: string | null;
  created_at: string;
}

export interface UnreadCountResponse {
  unread: number;
}

export interface NotificationPreferenceResponse {
  email_notifications_enabled: boolean;
}

export const notificationsApi = {
  list: (onlyUnread = false, limit = 50) =>
    apiClient.get<NotificationResponse[]>("/notifications/me", {
      params: { only_unread: onlyUnread, limit },
    }),
  unreadCount: () =>
    apiClient.get<UnreadCountResponse>("/notifications/me/unread-count"),
  markRead: (id: string) =>
    apiClient.put(`/notifications/me/${id}/read`),
  markAllRead: () =>
    apiClient.put<{ data: { marked: number }; message: string }>(
      "/notifications/me/read-all"
    ),
  getPreferences: () =>
    apiClient.get<NotificationPreferenceResponse>("/notifications/me/preferences"),
  updatePreferences: (enabled: boolean) =>
    apiClient.put<NotificationPreferenceResponse>(
      "/notifications/me/preferences",
      { email_notifications_enabled: enabled }
    ),
};

// ─── M6: Study Plan ─────────────────────────────────────────

export interface CreditLoadRecommendation {
  min_credits: number;
  recommended_credits: number;
  max_credits: number;
  rationale: string;
  based_on_gpa: number;
  warning_level: number;
}

export interface RetakeCourseItem {
  course_id: string;
  course_code: string;
  course_name: string;
  credits: number;
  last_grade_letter: string | null;
  last_total_score: number | null;
  last_semester: string;
  reason: string;
  priority: number;
}

export interface SuggestedCourseItem {
  course_id: string;
  course_code: string;
  course_name: string;
  credits: number;
  rationale: string;
}

export interface StudyPlanResponse {
  credit_load: CreditLoadRecommendation;
  retake_courses: RetakeCourseItem[];
  suggested_courses: SuggestedCourseItem[];
  total_unresolved_failed: number;
  total_credits_earned: number;
  gpa_cumulative: number;
}

export const studyPlanApi = {
  me: () => apiClient.get<StudyPlanResponse>("/study-plan/me"),
  creditLoad: () =>
    apiClient.get<CreditLoadRecommendation>("/study-plan/me/credit-load"),
};

// ─── M6: Events ─────────────────────────────────────────────

export type EventType = "exam" | "submission" | "activity" | "evaluation";
export type TargetAudience = "all" | "faculty_specific" | "cohort_specific";

export interface EventResponse {
  id: string;
  title: string;
  description: string | null;
  event_type: EventType;
  target_audience: TargetAudience;
  target_value: string | null;
  start_time: string;
  end_time: string | null;
  is_mandatory: boolean;
  created_by: string | null;
  created_at: string;
}

export const eventsApi = {
  myEvents: (limit = 50) =>
    apiClient.get<EventResponse[]>("/events/me", { params: { limit } }),
  myUpcoming: (limit = 20) =>
    apiClient.get<EventResponse[]>("/events/me/upcoming", { params: { limit } }),
};

// ─── M7: Admin ──────────────────────────────────────────────

export interface AdminWarningLevelBucket { level: number; count: number }
export interface AdminRiskBucket {
  bucket: "low" | "medium" | "high" | "critical";
  count: number;
  label_vi: string;
}
export interface AdminFacultyBucket {
  faculty: string;
  warning_count: number;
  total_students: number;
  pct: number;
}
export interface AdminTopRiskStudent {
  student_id: string;
  mssv: string;
  full_name: string;
  faculty: string;
  gpa_cumulative: number;
  warning_level: number;
  risk_score: number | null;
  risk_level: string | null;
}
export interface AdminDashboardStats {
  total_students: number;
  total_warned: number;
  total_high_risk: number;
  total_critical: number;
  by_warning_level: AdminWarningLevelBucket[];
  by_risk_level: AdminRiskBucket[];
  by_faculty: AdminFacultyBucket[];
  top_risk: AdminTopRiskStudent[];
  generated_at: string;
}

export interface AdminStudentListItem {
  student_id: string;
  mssv: string;
  full_name: string;
  faculty: string;
  major: string;
  cohort: number;
  email: string;
  gpa_cumulative: number;
  credits_earned: number;
  warning_level: number;
  risk_score: number | null;
  risk_level: string | null;
}
export interface AdminStudentListResponse {
  items: AdminStudentListItem[];
  total: number;
  page: number;
  size: number;
}

export interface AdminGpaHistoryPoint {
  semester: string;
  semester_gpa: number;
  credits_taken: number;
  courses_count: number;
}
export interface AdminWarningSummary {
  id: string;
  level: number;
  semester: string;
  reason: string;
  gpa_at_warning: number;
  is_resolved: boolean;
  sent_at: string | null;
  created_by: string;
}
export interface AdminStudentDetail {
  student_id: string;
  mssv: string;
  full_name: string;
  faculty: string;
  major: string;
  cohort: number;
  email: string;
  is_active: boolean;
  gpa_cumulative: number;
  credits_earned: number;
  warning_level: number;
  failed_courses_total: number;
  gpa_history: AdminGpaHistoryPoint[];
  risk_score: number | null;
  risk_level: string | null;
  risk_factors: Array<Record<string, unknown>>;
  warnings: AdminWarningSummary[];
}

export interface PendingWarningItem {
  student_id: string;
  mssv: string;
  full_name: string;
  faculty: string;
  semester: string;
  suggested_level: number;
  risk_score: number;
  risk_level: string;
  reason: string;
  gpa_cumulative: number;
}
export interface PendingWarningsResponse {
  items: PendingWarningItem[];
  total: number;
  threshold: number;
  last_batch_at: string | null;
}

export interface AdminImportError {
  row: number;
  column: string | null;
  reason: string;
  raw: Record<string, unknown> | null;
}
export interface AdminImportResult {
  type: "students" | "grades";
  filename: string;
  total_rows: number;
  created: number;
  updated: number;
  skipped: number;
  errors: AdminImportError[];
  success: boolean;
}
export interface AdminImportHistoryItem {
  id: string;
  type: "students" | "grades";
  filename: string;
  total_rows: number;
  created: number;
  updated: number;
  error_count: number;
  success: boolean;
  uploaded_at: string;
  uploaded_by_email: string | null;
}

export interface AdminSemesterWarningCount { semester: string; count: number }
export interface AdminGpaDistributionBucket { bucket: string; count: number }
export interface AdminRiskDistributionBucket {
  bucket: string;
  label_vi: string;
  count: number;
  pct: number;
}
export interface AdminWarningLevelReportBucket {
  level: number;
  label: string;
  count: number;
  pct: number;
}
export interface AdminPassFailBucket {
  status: string;
  label: string;
  count: number;
  pct: number;
}
export interface AdminStatistics {
  gpa_average: number;
  warning_rate_pct: number;
  improvement_rate_pct: number | null;
  pass_rate_pct: number | null;
  total_students: number;
  total_warned: number;
  total_high_risk: number;
  total_critical: number;
  by_semester: AdminSemesterWarningCount[];
  gpa_distribution: AdminGpaDistributionBucket[];
  by_warning_level: AdminWarningLevelReportBucket[];
  risk_distribution: AdminRiskDistributionBucket[];
  by_faculty: AdminFacultyBucket[];
  latest_pass_fail: AdminPassFailBucket[];
  semester_now: string | null;
}

export interface AdminThresholdConfig {
  ai_early_warning_threshold: number;
  gpa_safe: number;
  gpa_warning_l1: number;
  gpa_warning_l2: number;
  gpa_dismissal: number;
  semester_gpa_l1: number;
}

export const adminApi = {
  dashboard: () => apiClient.get<AdminDashboardStats>("/admin/dashboard"),

  listStudents: (params: {
    q?: string; faculty?: string; cohort?: number;
    warning_level?: number; high_risk?: boolean;
    page?: number; size?: number;
  }) => apiClient.get<AdminStudentListResponse>("/admin/students", { params }),

  studentDetail: (id: string) =>
    apiClient.get<AdminStudentDetail>(`/admin/students/${id}`),

  pendingWarnings: (semester?: string) =>
    apiClient.get<PendingWarningsResponse>("/admin/warnings/pending", {
      params: semester ? { semester } : undefined,
    }),

  approveWarning: (payload: {
    student_id: string; semester: string; level: number; reason?: string
  }) => apiClient.post<AdminWarningSummary>("/admin/warnings/approve", payload),

  manualWarning: (payload: {
    student_id: string; level: number; semester: string; reason: string
  }) => apiClient.post<AdminWarningSummary>("/admin/warnings/manual", payload),

  runBatchWarnings: (semester?: string) =>
    apiClient.post<{ data: { created: number; skipped: number }; message: string }>(
      "/admin/warnings/batch",
      undefined,
      { params: semester ? { semester } : undefined }
    ),

  runBatchPredictions: () =>
    apiClient.post<{ data: { count: number }; message: string }>(
      "/predictions/batch-run"
    ),

  importStudents: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return apiClient.post<AdminImportResult>("/admin/import/students", fd, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  importGrades: (file: File) => {
    const fd = new FormData();
    fd.append("file", file);
    return apiClient.post<AdminImportResult>("/admin/import/grades", fd, {
      headers: { "Content-Type": "multipart/form-data" },
    });
  },
  templateUrl: (type: "students" | "grades") =>
    `${apiClient.defaults.baseURL}/admin/import/templates/${type}`,
  importHistory: () =>
    apiClient.get<AdminImportHistoryItem[]>("/admin/import/history"),

  statistics: () => apiClient.get<AdminStatistics>("/admin/statistics"),
  exportReport: (reportType: "warnings" | "gpa" | "ai", format: "pdf" | "xlsx") =>
    apiClient.get<Blob>("/admin/reports/export", {
      params: { report_type: reportType, format },
      responseType: "blob",
    }),
  threshold: () => apiClient.get<AdminThresholdConfig>("/admin/threshold"),
  updateThreshold: (value: number) =>
    apiClient.patch<AdminThresholdConfig>("/admin/threshold", { ai_early_warning_threshold: value }),
};

// ─── M7: Admin events (CRUD) ────────────────────────────────

export interface AdminEventCreate {
  title: string;
  description: string | null;
  event_type: EventType;
  target_audience: TargetAudience;
  target_value: string | null;
  start_time: string;
  end_time: string | null;
  is_mandatory: boolean;
}

export const adminEventsApi = {
  list: () => apiClient.get<EventResponse[]>("/events"),
  create: (payload: AdminEventCreate) =>
    apiClient.post<EventResponse>("/events", payload),
  update: (id: string, payload: Partial<AdminEventCreate>) =>
    apiClient.put<EventResponse>(`/events/${id}`, payload),
  remove: (id: string) => apiClient.delete(`/events/${id}`),
};
