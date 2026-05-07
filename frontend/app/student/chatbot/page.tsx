"use client";

import {
  type FormEvent,
  type KeyboardEvent,
  type ReactNode,
  useCallback,
  useEffect,
  useRef,
  useState,
} from "react";
import { Bot, FileText, Loader2, RotateCcw, Send, UserRound } from "lucide-react";
import { API_BASE, chatbotApi, type ChatCitation, type ChatMessageResponse } from "@/lib/api";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { cn } from "@/lib/utils";

type UiMessage = {
  id: string;
  role: "user" | "assistant";
  content: string;
  citations: ChatCitation[];
};

export default function ChatbotPage() {
  const [messages, setMessages] = useState<UiMessage[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(true);
  const [sending, setSending] = useState(false);
  const [error, setError] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const justSubmittedRef = useRef(false);

  const loadInitialData = useCallback(async () => {
    try {
      setLoading(true);
      const [historyRes, suggestionRes] = await Promise.all([
        chatbotApi.history(),
        chatbotApi.suggestions(),
      ]);
      setMessages(historyRes.data.map(toUiMessage));
      setSuggestions(suggestionRes.data.suggestions);
    } catch {
      setError("Không tải được lịch sử tư vấn AI.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadInitialData();
  }, [loadInitialData]);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async (event?: FormEvent, preset?: string) => {
    event?.preventDefault();
    const text = (preset ?? question).trim();
    if (!text || sending) return;

    const assistantId = crypto.randomUUID();
    justSubmittedRef.current = true;
    setTimeout(() => { justSubmittedRef.current = false; }, 0);
    setQuestion("");
    if (textareaRef.current) textareaRef.current.value = "";
    setError("");
    setSending(true);
    setMessages((current) => [
      ...current,
      { id: crypto.randomUUID(), role: "user", content: text, citations: [] },
      { id: assistantId, role: "assistant", content: "", citations: [] },
    ]);

    try {
      await streamAnswer(text, assistantId);
    } catch {
      try {
        const response = await chatbotApi.ask(text);
        setMessages((current) =>
          current.map((message) =>
            message.id === assistantId
              ? {
                  ...message,
                  content: response.data.answer,
                  citations: response.data.citations,
                }
              : message
          )
        );
      } catch {
        setError("Chatbot chưa trả lời được. Kiểm tra backend hoặc cấu hình RAG.");
        setMessages((current) =>
          current.map((message) =>
            message.id === assistantId
              ? { ...message, content: "Mình chưa tạo được câu trả lời lúc này.", citations: [] }
              : message
          )
        );
      }
    } finally {
      setSending(false);
    }
  };

  const streamAnswer = async (text: string, assistantId: string) => {
    const token = localStorage.getItem("access_token");
    const response = await fetch(`${API_BASE}/chatbot/ask/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
      },
      body: JSON.stringify({ question: text }),
    });

    if (!response.ok || !response.body) {
      throw new Error("stream failed");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const events = buffer.split("\n\n");
      buffer = events.pop() ?? "";

      for (const event of events) {
        const line = event.split("\n").find((item) => item.startsWith("data: "));
        if (!line) continue;
        const payload = JSON.parse(line.slice(6));
        if (payload.type === "delta") {
          setMessages((current) =>
            current.map((message) =>
              message.id === assistantId
                ? { ...message, content: message.content + payload.content }
                : message
            )
          );
        }
        if (payload.type === "done") {
          setMessages((current) =>
            current.map((message) =>
              message.id === assistantId
                ? { ...message, citations: payload.citations ?? [] }
                : message
            )
          );
        }
      }
    }
  };

  const handleClear = async () => {
    await chatbotApi.clearHistory();
    setMessages([]);
  };

  const handleQuestionKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key !== "Enter" || event.shiftKey) return;
    event.preventDefault();
    void handleSubmit();
  };

  return (
    <div className="mx-auto flex h-[calc(100vh-3rem)] max-w-6xl flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-gray-900">Hỏi đáp và tư vấn học vụ</h1>
          <p className="text-sm text-gray-500">
            Chatbot dùng dữ liệu học vụ của bạn và tài liệu quy chế admin đã upload.
          </p>
        </div>
        <Button variant="outline" onClick={handleClear} disabled={sending || messages.length === 0}>
          <RotateCcw className="mr-2 h-4 w-4" />
          Xóa lịch sử
        </Button>
      </div>

      {error && (
        <div className="rounded-md border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
          {error}
        </div>
      )}

      <Card className="flex min-h-0 flex-1 flex-col rounded-lg shadow-sm">
        <CardHeader className="border-b p-4">
          <CardTitle className="flex items-center gap-2 text-base">
            <Bot className="h-5 w-5 text-primary" />
            Hỏi về cảnh báo học vụ, học lại, GPA và quy chế
          </CardTitle>
        </CardHeader>
        <CardContent className="flex min-h-0 flex-1 flex-col p-0">
          <div className="min-h-0 flex-1 space-y-4 overflow-y-auto p-4">
            {loading ? (
              <div className="flex h-full items-center justify-center text-sm text-gray-500">
                <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                Đang tải...
              </div>
            ) : messages.length === 0 ? (
              <div className="flex h-full flex-col items-center justify-center gap-4 text-center">
                <Bot className="h-10 w-10 text-primary" />
                <div>
                  <p className="font-medium text-gray-900">Bắt đầu một câu hỏi học vụ</p>
                  <p className="text-sm text-gray-500">
                    Nếu chưa có tài liệu quy chế, chatbot sẽ nói rõ là thiếu nguồn.
                  </p>
                </div>
                <div className="flex max-w-3xl flex-wrap justify-center gap-2">
                  {suggestions.map((item) => (
                    <button
                      key={item}
                      className="rounded-md border bg-white px-3 py-2 text-sm text-gray-700 hover:bg-gray-50"
                      onClick={() => void handleSubmit(undefined, item)}
                    >
                      {item}
                    </button>
                  ))}
                </div>
              </div>
            ) : (
              messages.map((message) => <MessageBubble key={message.id} message={message} />)
            )}
            <div ref={bottomRef} />
          </div>

          <form onSubmit={(event) => void handleSubmit(event)} className="border-t p-4">
            <div className="flex gap-2">
              <textarea
                ref={textareaRef}
                value={question}
                onChange={(event) => {
                    if (justSubmittedRef.current) { if (textareaRef.current) textareaRef.current.value = ""; return; }
                    setQuestion(event.target.value);
                }}
                onKeyDown={handleQuestionKeyDown}
                placeholder="Nhập câu hỏi của bạn..."
                className="min-h-11 flex-1 resize-none rounded-md border border-input bg-white px-3 py-2 text-sm outline-none focus:ring-2 focus:ring-primary/30"
                rows={2}
              />
              <Button type="submit" className="h-auto self-stretch px-4" disabled={sending || !question.trim()}>
                {sending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
              </Button>
            </div>
          </form>
        </CardContent>
      </Card>
    </div>
  );
}

function MessageBubble({ message }: { message: UiMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={cn("flex gap-3", isUser && "justify-end")}>
      {!isUser && (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-primary/10 text-primary">
          <Bot className="h-4 w-4" />
        </div>
      )}
      <div className={cn("max-w-[78%] space-y-2", isUser && "flex flex-col items-end")}>
        <div
          className={cn(
            "rounded-lg px-4 py-3 text-sm leading-6",
            isUser ? "bg-primary text-white" : "border bg-white text-gray-800"
          )}
        >
          {message.content ? (
            isUser ? (
              <span className="whitespace-pre-wrap">{message.content}</span>
            ) : (
              <MarkdownMessage content={message.content} />
            )
          ) : (
            "Đang suy nghĩ..."
          )}
        </div>
        {!isUser && message.citations.length > 0 && (
          <div className="space-y-2">
            {message.citations.map((citation) => (
              <div
                key={`${citation.document_id}-${citation.index}`}
                className="rounded-md border bg-gray-50 px-3 py-2 text-xs text-gray-600"
              >
                <div className="mb-1 flex items-center gap-2 font-medium text-gray-800">
                  <FileText className="h-3.5 w-3.5" />
                  [{citation.index}] {citation.filename}
                  {citation.page_number ? `, trang ${citation.page_number}` : ""}
                </div>
                <p className="line-clamp-3">{citation.snippet}</p>
              </div>
            ))}
          </div>
        )}
      </div>
      {isUser && (
        <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-md bg-gray-200 text-gray-700">
          <UserRound className="h-4 w-4" />
        </div>
      )}
    </div>
  );
}

function toUiMessage(message: ChatMessageResponse): UiMessage {
  return {
    id: message.id,
    role: message.role,
    content: message.content,
    citations: message.citations ?? [],
  };
}

function MarkdownMessage({ content }: { content: string }) {
  const blocks = toMarkdownBlocks(content);
  return (
    <div className="space-y-2">
      {blocks.map((block, index) => {
        if (block.type === "list") {
          return (
            <ul key={index} className="list-disc space-y-1 pl-5">
              {block.items.map((item, itemIndex) => (
                <li key={itemIndex}>{renderInlineMarkdown(item, `${index}-${itemIndex}`)}</li>
              ))}
            </ul>
          );
        }

        return (
          <p key={index} className="whitespace-pre-wrap">
            {renderInlineMarkdown(block.text, String(index))}
          </p>
        );
      })}
    </div>
  );
}

type MarkdownBlock =
  | { type: "paragraph"; text: string }
  | { type: "list"; items: string[] };

function toMarkdownBlocks(content: string): MarkdownBlock[] {
  const blocks: MarkdownBlock[] = [];
  const lines = content.split("\n");
  let paragraph: string[] = [];
  let listItems: string[] = [];

  const flushParagraph = () => {
    if (paragraph.length === 0) return;
    blocks.push({ type: "paragraph", text: paragraph.join("\n") });
    paragraph = [];
  };

  const flushList = () => {
    if (listItems.length === 0) return;
    blocks.push({ type: "list", items: listItems });
    listItems = [];
  };

  for (const line of lines) {
    const bullet = line.match(/^\s*(?:[-*]|\d+\.)\s+(.+)$/);
    if (bullet) {
      flushParagraph();
      listItems.push(bullet[1]);
      continue;
    }

    flushList();
    if (line.trim()) {
      paragraph.push(line);
    } else {
      flushParagraph();
    }
  }

  flushParagraph();
  flushList();
  return blocks;
}

function renderInlineMarkdown(text: string, keyPrefix: string): ReactNode[] {
  const nodes: ReactNode[] = [];
  const pattern = /\*\*(.+?)\*\*/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      nodes.push(text.slice(lastIndex, match.index));
    }
    nodes.push(
      <strong key={`${keyPrefix}-${match.index}`} className="font-semibold text-gray-950">
        {match[1]}
      </strong>
    );
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    nodes.push(text.slice(lastIndex));
  }
  return nodes;
}
