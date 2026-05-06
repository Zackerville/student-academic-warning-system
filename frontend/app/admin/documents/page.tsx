"use client";

import { ChangeEvent, useCallback, useEffect, useState } from "react";
import { FileUp, Loader2, RefreshCw, ShieldAlert, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  documentsApi,
  type DocumentBatchUploadResponse,
  type DocumentGroupResponse,
} from "@/lib/api";

export default function AdminDocumentsPage() {
  const [documents, setDocuments] = useState<DocumentGroupResponse[]>([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState("");
  const [uploadSummary, setUploadSummary] = useState<DocumentBatchUploadResponse | null>(null);

  const loadDocuments = useCallback(async () => {
    try {
      setLoading(true);
      setError("");
      const response = await documentsApi.list();
      setDocuments(response.data);
    } catch {
      setError("Không tải được danh sách tài liệu. Tài khoản hiện tại cần quyền admin.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadDocuments();
  }, [loadDocuments]);

  const handleFiles = async (event: ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files ?? []);
    if (files.length === 0) return;
    try {
      setUploading(true);
      setError("");
      setUploadSummary(null);
      const response = await documentsApi.uploadBatch(files);
      setUploadSummary(response.data);
      await loadDocuments();
    } catch (err: unknown) {
      setError(formatApiError(err, "Upload batch thất bại. Hãy kiểm tra định dạng file và backend."));
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  };

  const toggleDocument = async (document: DocumentGroupResponse) => {
    await documentsApi.toggle(document.source_file, !document.is_active);
    await loadDocuments();
  };

  const deleteDocument = async (document: DocumentGroupResponse) => {
    if (!confirm(`Xóa tài liệu ${document.filename}?`)) return;
    await documentsApi.delete(document.source_file);
    await loadDocuments();
  };

  return (
    <main className="min-h-screen bg-gray-50 p-6">
      <div className="mx-auto max-w-6xl space-y-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h1 className="text-2xl font-semibold text-gray-900">Quản lý tài liệu RAG</h1>
            <p className="text-sm text-gray-500">
              Upload nhiều PDF, DOCX, TXT, MD hoặc một file ZIP chứa tài liệu quy chế.
            </p>
          </div>
          <div className="flex gap-2">
            <Button variant="outline" onClick={() => void loadDocuments()}>
              <RefreshCw className="mr-2 h-4 w-4" />
              Tải lại
            </Button>
            <label className="inline-flex h-9 cursor-pointer items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-medium text-white hover:bg-primary/90">
              {uploading ? (
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
              ) : (
                <FileUp className="mr-2 h-4 w-4" />
              )}
              {uploading ? "Đang nạp..." : "Upload batch"}
              <input
                type="file"
                accept=".pdf,.docx,.txt,.md,.zip"
                className="hidden"
                multiple
                onChange={(event) => void handleFiles(event)}
                disabled={uploading}
              />
            </label>
          </div>
        </div>

        {error && (
          <div className="flex items-center gap-2 rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
            <ShieldAlert className="h-4 w-4" />
            {error}
          </div>
        )}

        {uploadSummary && (
          <div className="rounded-md border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-800">
            <p className="font-medium">
              Đã nạp {uploadSummary.uploaded} file, lỗi {uploadSummary.failed} file,
              tổng {uploadSummary.total_chunks} chunks.
            </p>
            {uploadSummary.results.some((item) => item.status === "failed") && (
              <div className="mt-2 max-h-40 overflow-y-auto space-y-1 text-xs text-red-700">
                {uploadSummary.results
                  .filter((item) => item.status === "failed")
                  .map((item) => (
                    <p key={item.filename}>
                      {item.filename}: {item.error}
                    </p>
                  ))}
              </div>
            )}
          </div>
        )}

        <Card className="rounded-lg shadow-sm">
          <CardHeader className="border-b p-4">
            <CardTitle className="text-base">Tài liệu đã nạp</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {loading ? (
              <div className="flex items-center justify-center py-16 text-sm text-gray-500">
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Đang tải...
              </div>
            ) : documents.length === 0 ? (
              <div className="py-16 text-center text-sm text-gray-500">
                Chưa có tài liệu nào. Upload tài liệu quy chế để bắt đầu test chatbot.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left text-sm">
                  <thead className="bg-gray-100 text-xs uppercase text-gray-500">
                    <tr>
                      <th className="px-4 py-3">File</th>
                      <th className="px-4 py-3">Chunks</th>
                      <th className="px-4 py-3">Trang</th>
                      <th className="px-4 py-3">Trạng thái</th>
                      <th className="px-4 py-3">Upload</th>
                      <th className="px-4 py-3 text-right">Thao tác</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y bg-white">
                    {documents.map((document) => (
                      <tr key={document.source_file}>
                        <td className="max-w-md px-4 py-3 font-medium text-gray-900">
                          <span className="block truncate">{document.filename}</span>
                        </td>
                        <td className="px-4 py-3 text-gray-600">{document.chunks_count}</td>
                        <td className="px-4 py-3 text-gray-600">{document.pages_count || "-"}</td>
                        <td className="px-4 py-3">
                          <button
                            onClick={() => void toggleDocument(document)}
                            className={
                              document.is_active
                                ? "rounded-md bg-green-50 px-2 py-1 text-xs font-medium text-green-700"
                                : "rounded-md bg-gray-100 px-2 py-1 text-xs font-medium text-gray-600"
                            }
                          >
                            {document.is_active ? "Đang dùng" : "Tạm tắt"}
                          </button>
                        </td>
                        <td className="px-4 py-3 text-gray-600">
                          {new Date(document.uploaded_at).toLocaleString("vi-VN")}
                        </td>
                        <td className="px-4 py-3 text-right">
                          <Button
                            variant="ghost"
                            size="icon"
                            onClick={() => void deleteDocument(document)}
                          >
                            <Trash2 className="h-4 w-4 text-red-600" />
                          </Button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </main>
  );
}

function formatApiError(err: unknown, fallback: string): string {
  const detail = (err as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail;
  if (!detail) return fallback;
  if (typeof detail === "string") return detail;
  if (Array.isArray(detail)) {
    return detail
      .map((item) => {
        if (typeof item === "string") return item;
        if (item && typeof item === "object" && "msg" in item) {
          const loc = "loc" in item && Array.isArray(item.loc) ? item.loc.join(".") : "";
          const msg = String(item.msg);
          return loc ? `${loc}: ${msg}` : msg;
        }
        return JSON.stringify(item);
      })
      .join("; ");
  }
  if (typeof detail === "object") return JSON.stringify(detail);
  return fallback;
}
