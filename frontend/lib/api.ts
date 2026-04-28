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