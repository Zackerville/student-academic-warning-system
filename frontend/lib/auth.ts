import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { UserResponse } from "./api";

interface AuthState {
  user: UserResponse | null;
  token: string | null;
  setAuth: (token: string, user: UserResponse) => void;
  clearAuth: () => void;
  isAuthenticated: () => boolean;
}

function setCookie(name: string, value: string, days = 1) {
  const expires = new Date(Date.now() + days * 864e5).toUTCString();
  document.cookie = `${name}=${value}; expires=${expires}; path=/; SameSite=Lax`;
}

function deleteCookie(name: string) {
  document.cookie = `${name}=; expires=Thu, 01 Jan 1970 00:00:00 GMT; path=/`;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set, get) => ({
      user: null,
      token: null,

      setAuth: (token, user) => {
        localStorage.setItem("access_token", token);
        setCookie("access_token", token);
        set({ token, user });
      },

      clearAuth: () => {
        localStorage.removeItem("access_token");
        deleteCookie("access_token");
        set({ token: null, user: null });
      },

      isAuthenticated: () => get().token !== null,
    }),
    {
      name: "auth-storage",
      partialize: (state) => ({ user: state.user, token: state.token }),
    }
  )
);