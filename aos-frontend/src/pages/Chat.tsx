import { useEffect, useRef, useState } from "react";
import { Send, Bot, User as UserIcon, Wrench } from "lucide-react";
import { ConversationAPI, type AgentRunResult } from "@/lib/api";
import { Button } from "@/components/ui/Button";
import { Input } from "@/components/ui/Input";
import { cn } from "@/lib/utils";

type Msg = {
  role: "user" | "assistant" | "system";
  content: string;
  meta?: AgentRunResult | null;
};

export function ChatPage() {
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    (async () => {
      const { data } = await ConversationAPI.createSession("web");
      setSessionId(data.session_id ?? data.id);
      setMessages([
        {
          role: "assistant",
          content:
            "Hi — I'm AOS. Ask me anything about finance, procurement, sales, inventory or HR. Try: \"show me trial balance\" or \"create PO for Acme 100 bearings at ₹500\".",
        },
      ]);
    })();
  }, []);

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: "smooth" });
  }, [messages]);

  async function send() {
    if (!input.trim() || !sessionId || loading) return;
    const userMsg = input.trim();
    setInput("");
    setMessages((m) => [...m, { role: "user", content: userMsg }]);
    setLoading(true);
    try {
      const { data } = await ConversationAPI.sendMessage(sessionId, userMsg);
      setMessages((m) => [...m, { role: "assistant", content: data.text, meta: data }]);
    } catch (e: any) {
      setMessages((m) => [
        ...m,
        { role: "system", content: `Error: ${e?.response?.data?.detail ?? e.message}` },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex h-full flex-col">
      <div ref={scrollRef} className="flex-1 overflow-auto space-y-4 pb-4">
        {messages.map((m, i) => (
          <Bubble key={i} msg={m} />
        ))}
        {loading && <div className="text-sm text-muted-foreground pl-12">thinking…</div>}
      </div>

      <div className="flex gap-2 border-t pt-4">
        <Input
          placeholder="Ask AOS anything…"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && send()}
          disabled={loading || !sessionId}
        />
        <Button onClick={send} disabled={loading || !sessionId || !input.trim()}>
          <Send className="h-4 w-4" />
        </Button>
      </div>
    </div>
  );
}

function Bubble({ msg }: { msg: Msg }) {
  const isUser = msg.role === "user";
  const Icon = isUser ? UserIcon : Bot;
  return (
    <div className={cn("flex gap-3", isUser && "flex-row-reverse")}>
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-accent">
        <Icon className="h-4 w-4" />
      </div>
      <div className={cn("max-w-2xl space-y-2", isUser && "text-right")}>
        <div
          className={cn(
            "inline-block rounded-lg px-4 py-2 text-sm whitespace-pre-wrap",
            isUser ? "bg-primary text-primary-foreground" : "bg-card border",
          )}
        >
          {msg.content}
        </div>
        {msg.meta?.tool_calls && msg.meta.tool_calls.length > 0 && (
          <div className="space-y-1 text-xs text-muted-foreground">
            {msg.meta.tool_calls.map((tc, i) => (
              <div key={i} className="flex items-center gap-2">
                <Wrench className="h-3 w-3" />
                <span className="font-mono">{tc.tool}</span>
                <span className="opacity-70">(conf {(tc.confidence * 100).toFixed(0)}%)</span>
              </div>
            ))}
          </div>
        )}
        {msg.meta?.requires_approval && (
          <div className="inline-block rounded bg-yellow-100 px-2 py-1 text-xs text-yellow-900">
            Pending approval · {msg.meta.approval_request_id}
          </div>
        )}
      </div>
    </div>
  );
}
