import axios from "axios";

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

export const apiClient = axios.create({
  baseURL: API_BASE,
  headers: { "Content-Type": "application/json" },
  timeout: 15000,
});

// Attach JWT token from localStorage on every request
apiClient.interceptors.request.use((config) => {
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
      window.location.href = "/login";
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
    apiClient.put<EnrollmentResponse>(
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

export const predictionsApi = {
  me: () => apiClient.get<PredictionResponse>("/predictions/me"),
  history: (limit = 30) =>
    apiClient.get<PredictionHistoryEntry[]>("/predictions/me/history", {
      params: { limit },
    }),
  refresh: () => apiClient.post<PredictionResponse>("/predictions/me/refresh"),
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