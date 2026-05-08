"use client";

import { useEffect } from "react";
import { AlertTriangle, RefreshCcw } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error("[GlobalError]", error);
  }, [error]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-6 bg-gray-50 px-4 text-center">
      <div className="flex h-14 w-14 items-center justify-center rounded-full bg-red-100">
        <AlertTriangle className="h-7 w-7 text-red-600" />
      </div>
      <div className="space-y-2">
        <h1 className="text-xl font-semibold text-gray-900">Đã xảy ra lỗi</h1>
        <p className="text-sm text-gray-500">
          Hệ thống gặp sự cố không mong đợi. Vui lòng thử lại.
        </p>
        {error.digest && (
          <p className="text-xs text-gray-400">Mã lỗi: {error.digest}</p>
        )}
      </div>
      <Button onClick={reset}>
        <RefreshCcw className="mr-2 h-4 w-4" />
        Thử lại
      </Button>
    </div>
  );
}
