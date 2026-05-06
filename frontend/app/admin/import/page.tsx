"use client";

import { useEffect, useRef, useState } from "react";
import { Users, FileText, Download, CheckCircle2, AlertCircle, Upload } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { adminApi, type AdminImportHistoryItem, type AdminImportResult } from "@/lib/api";
import { useT } from "@/lib/i18n";

type ImportType = "students" | "grades";

export default function AdminImportPage() {
  const t = useT();
  const [history, setHistory] = useState<AdminImportHistoryItem[]>([]);
  const [lastResult, setLastResult] = useState<AdminImportResult | null>(null);
  const [loading, setLoading] = useState(true);

  const reloadHistory = async () => {
    try {
      const r = await adminApi.importHistory();
      setHistory(r.data);
    } catch {
      // ignore — history non-critical
    }
  };

  useEffect(() => {
    reloadHistory().finally(() => setLoading(false));
  }, []);

  const handleResult = async (result: AdminImportResult) => {
    setLastResult(result);
    await reloadHistory();
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-primary">{t("adminImport.title")}</h1>
        <p className="text-muted-foreground text-sm mt-0.5">{t("adminImport.subtitle")}</p>
      </div>

      {/* Upload boxes */}
      <div className="grid gap-4 md:grid-cols-2">
        <UploadBox
          type="students"
          icon={Users}
          title={t("adminImport.studentsTitle")}
          description={t("adminImport.studentsDesc")}
          onResult={handleResult}
        />
        <UploadBox
          type="grades"
          icon={FileText}
          title={t("adminImport.gradesTitle")}
          description={t("adminImport.gradesDesc")}
          onResult={handleResult}
        />
      </div>

      {/* Last result */}
      {lastResult && <ImportResultCard result={lastResult} onClose={() => setLastResult(null)} />}

      {/* History */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">{t("adminImport.history")}</CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-muted-foreground py-4 text-center">{t("common.loading")}</p>
          ) : history.length === 0 ? (
            <p className="text-sm text-muted-foreground py-6 text-center">{t("adminImport.historyEmpty")}</p>
          ) : (
            <div className="divide-y">
              {history.map((h) => (
                <div key={h.id} className="flex items-center justify-between gap-3 py-3 flex-wrap">
                  <div className="flex items-center gap-3 min-w-0">
                    {h.success ? (
                      <CheckCircle2 className="h-4 w-4 text-green-600 shrink-0" />
                    ) : (
                      <AlertCircle className="h-4 w-4 text-destructive shrink-0" />
                    )}
                    <div className="min-w-0">
                      <p className="text-sm font-medium truncate">{h.filename}</p>
                      <p className="text-xs text-muted-foreground">
                        {new Date(h.uploaded_at).toLocaleString("vi-VN")} ·{" "}
                        {h.total_rows} dòng · {t(h.type === "students" ? "adminNav.students" : "adminImport.gradesTitle")}
                        {h.uploaded_by_email && ` · ${h.uploaded_by_email}`}
                      </p>
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0 text-xs text-muted-foreground">
                    <Badge variant={h.success ? "default" : "destructive"}>
                      {h.success ? t("adminImport.success") : t("adminImport.failed")}
                    </Badge>
                    <span>+{h.created} / ✎{h.updated} / ⚠{h.error_count}</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

function UploadBox({
  type, icon: Icon, title, description, onResult,
}: {
  type: ImportType;
  icon: React.ElementType;
  title: string;
  description: string;
  onResult: (r: AdminImportResult) => void;
}) {
  const t = useT();
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const handleSelect = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setErr(null);
    try {
      const fn = type === "students" ? adminApi.importStudents : adminApi.importGrades;
      const r = await fn(file);
      onResult(r.data);
    } catch (e: unknown) {
      const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail;
      setErr(detail || "Upload thất bại");
    } finally {
      setBusy(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  const downloadTemplate = () => {
    window.open(adminApi.templateUrl(type), "_blank");
  };

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <Icon className="h-5 w-5 text-primary" />
          {title}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        <p className="text-sm text-muted-foreground">{description}</p>
        <input
          ref={inputRef}
          type="file"
          accept=".xlsx,.xls"
          onChange={handleSelect}
          className="hidden"
        />
        <div className="flex gap-2">
          <Button onClick={() => inputRef.current?.click()} disabled={busy} className="flex-1">
            <Upload className="h-4 w-4 mr-1.5" />
            {busy ? t("adminImport.uploading") : t("adminImport.chooseFile")}
          </Button>
          <Button variant="outline" onClick={downloadTemplate}>
            <Download className="h-4 w-4 mr-1.5" />
            {t("adminImport.downloadTemplate")}
          </Button>
        </div>
        {err && <p className="text-sm text-destructive">{err}</p>}
      </CardContent>
    </Card>
  );
}

function ImportResultCard({ result, onClose }: { result: AdminImportResult; onClose: () => void }) {
  const t = useT();
  const [showErrors, setShowErrors] = useState(true);

  return (
    <Card className={result.success ? "border-green-300" : "border-orange-300"}>
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <CardTitle className="text-base flex items-center gap-2">
            {result.success ? (
              <CheckCircle2 className="h-5 w-5 text-green-600" />
            ) : (
              <AlertCircle className="h-5 w-5 text-orange-600" />
            )}
            {result.filename}
          </CardTitle>
          <Button size="sm" variant="ghost" onClick={onClose}>✕</Button>
        </div>
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="grid grid-cols-4 gap-3 text-center">
          <div>
            <p className="text-xs text-muted-foreground">{t("adminImport.totalRows")}</p>
            <p className="text-2xl font-bold">{result.total_rows}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">{t("adminImport.created")}</p>
            <p className="text-2xl font-bold text-green-600">+{result.created}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">{t("adminImport.updated")}</p>
            <p className="text-2xl font-bold text-blue-600">{result.updated}</p>
          </div>
          <div>
            <p className="text-xs text-muted-foreground">{t("adminImport.errors")}</p>
            <p className={`text-2xl font-bold ${result.errors.length > 0 ? "text-destructive" : "text-muted-foreground"}`}>
              {result.errors.length}
            </p>
          </div>
        </div>

        {result.errors.length > 0 && (
          <div>
            <button
              type="button"
              className="text-xs font-medium text-primary"
              onClick={() => setShowErrors((s) => !s)}
            >
              {showErrors ? "▼" : "▶"} {t("adminImport.errorList")}
            </button>
            {showErrors && (
              <div className="mt-2 max-h-64 overflow-y-auto rounded-md border bg-muted/30 text-xs">
                <table className="w-full">
                  <thead className="bg-muted/50 sticky top-0">
                    <tr>
                      <th className="px-3 py-2 text-left font-medium">Dòng</th>
                      <th className="px-3 py-2 text-left font-medium">Cột</th>
                      <th className="px-3 py-2 text-left font-medium">Lý do</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {result.errors.map((e, i) => (
                      <tr key={i}>
                        <td className="px-3 py-1.5 font-mono">{e.row}</td>
                        <td className="px-3 py-1.5 font-mono">{e.column ?? "—"}</td>
                        <td className="px-3 py-1.5">{e.reason}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
