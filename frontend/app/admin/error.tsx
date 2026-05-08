"use client";

import { useEffect } from "react";
import { AlertTriangle, RefreshCcw, LayoutDashboard } from "lucide-react";
import Link from "next/link";
import { Button } from "@/components/ui/button";

export default function AdminError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[AdminError]", error);
  }, [error]);

  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-6 px-4 py-20 text-center">
      <div className="flex h-12 w-12 items-center justify-center rounded-full bg-red-100">
        <AlertTriangle className="h-6 w-6 text-red-600" />
      </div>
      <div className="space-y-1">
        <h2 className="text-lg font-semibold text-gray-900">Lỗi Admin Panel</h2>
        <p className="text-sm text-gray-500">
          Trang admin gặp sự cố. Kiểm tra quyền truy cập hoặc thử lại.
        </p>
      </div>
      <div className="flex gap-3">
        <Button variant="outline" onClick={reset}>
          <RefreshCcw className="mr-2 h-4 w-4" />
          Thử lại
        </Button>
        <Link
          href="/admin/dashboard"
          className="inline-flex items-center justify-center rounded-md text-sm font-medium hover:bg-accent hover:text-accent-foreground h-9 px-4 py-2 transition-colors"
        >
          <LayoutDashboard className="mr-2 h-4 w-4" />
          Về Admin Dashboard
        </Link>
      </div>
    </div>
  );
}
