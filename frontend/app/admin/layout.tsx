"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import AdminSidebar from "@/components/layout/AdminSidebar";
import { useAuthStore } from "@/lib/auth";

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const { user, token } = useAuthStore();
  const [hydrated, setHydrated] = useState(false);

  useEffect(() => {
    setHydrated(true);
  }, []);

  useEffect(() => {
    if (!hydrated) return;
    if (!token) {
      router.replace("/auth/login");
      return;
    }
    if (user && user.role !== "admin") {
      router.replace("/student/dashboard");
    }
  }, [hydrated, token, user, router]);

  if (!hydrated || !token || (user && user.role !== "admin")) {
    return (
      <div className="flex items-center justify-center h-screen">
        <div className="text-muted-foreground animate-pulse">Đang xác thực...</div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen">
      <AdminSidebar />
      <main className="flex-1 bg-gray-50 p-6 overflow-auto">{children}</main>
    </div>
  );
}
