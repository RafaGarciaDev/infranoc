"use client";
import React, { useRef, useState } from "react";
import Shell from "@/components/Shell";
import { askAiStream } from "@/lib/api";

type Msg = { role: "user" | "assistant"; content: string };

const SUGESTOES = [
  "Quantos servidores temos no site PSA?",
  "Quais alertas estao ativos agora?",
  "O que fazer quando a camara fria passa do limite de temperatura?",
  "Como executar o failover do link de rede?",
];

export default function IaPage() {
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  async function enviar(pergunta: string) {
    const q = pergunta.trim();
    if (!q || busy) return;
    setError(null);
    setBusy(true);
    setInput("");
    const history: Msg[] = [];
    setMsgs((cur) => [...cur, { role: "user", content: q }, { role: "assistant", content: "" }]);
    try {
      await askAiStream(q, history, (chunk) => {
        setMsgs((cur) => {
          const next = [...cur];
          const last = next[next.length - 1];
          next[next.length - 1] = { ...last, content: last.content + chunk };
          return next;
        });
        endRef.current?.scrollIntoView({ behavior: "smooth" });
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Erro inesperado.");
      setMsgs((cur) => (cur[cur.length - 1]?.content === "" ? cur.slice(0, -1) : cur));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Shell title="Assistente de IA">
      <div className="ia-chat">
        {msgs.length === 0 && (
          <div className="ia-sugestoes">
            <p>Pergunte sobre ativos, alertas ou procedimentos (runbooks):</p>
            {SUGESTOES.map((s) => (
              <button key={s} className="ia-sugestao" onClick={() => enviar(s)} disabled={busy}>
                {s}
              </button>
            ))}
          </div>
        )}
        <div className="ia-mensagens">
          {msgs.map((m, i) => (
            <div key={i} className={m.role === "user" ? "ia-msg ia-msg-user" : "ia-msg ia-msg-bot"}>
              {m.content || (busy && i === msgs.length - 1 ? "pensando... (pode levar alguns minutos)" : "")}
            </div>
          ))}
          <div ref={endRef} />
        </div>
        {error && <div className="ia-erro">{error}</div>}
        <form
          className="ia-form"
          onSubmit={(e) => {
            e.preventDefault();
            enviar(input);
          }}
        >
          <input
            className="field-input ia-input"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Digite sua pergunta..."
            disabled={busy}
          />
          <button className="btn btn-primary" type="submit" disabled={busy || !input.trim()}>
            {busy ? "aguarde..." : "enviar"}
          </button>
        </form>
      </div>
    </Shell>
  );
}
