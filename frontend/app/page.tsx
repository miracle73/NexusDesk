"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "/api/v1";
type Metrics = {
  total: number;
  open: number;
  resolved: number;
  escalated: number;
  resolution_rate: number;
  knowledge_gaps: string[];
};
type Conversation = {
  id: string;
  customer_email?: string;
  status: string;
  escalation_reason?: string;
  updated_at: string;
};

export default function Home() {
  const [token, setToken] = useState("");
  const [authReady, setAuthReady] = useState(false);
  const [company, setCompany] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [register, setRegister] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [filter, setFilter] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [notice, setNotice] = useState("");
  const [knowledgeNotice, setKnowledgeNotice] = useState("");
  const headers = { Authorization: `Bearer ${token}` };

  const refresh = useCallback(async () => {
    const currentHeaders = { Authorization: `Bearer ${token}` };
    const [m, c] = await Promise.all([
      fetch(`${API}/conversations/metrics`, { headers: currentHeaders }),
      fetch(`${API}/conversations${filter ? `?status=${filter}` : ""}`, {
        headers: currentHeaders,
      }),
    ]);
    if (m.status === 401 || c.status === 401) {
      localStorage.removeItem("nexusdesk_token");
      setToken("");
      setNotice("Your session expired. Please sign in again.");
      return;
    }
    if (m.ok) setMetrics(await m.json());
    if (c.ok) setConversations(await c.json());
  }, [filter, token]);

  useEffect(() => {
    const saved = localStorage.getItem("nexusdesk_token");
    queueMicrotask(() => {
      if (saved) setToken(saved);
      setAuthReady(true);
    });
  }, []);
  // Data is intentionally refreshed when authentication or the status filter changes.
  useEffect(() => {
    // The async refresh synchronizes dashboard state with the authenticated API.
    // eslint-disable-next-line react-hooks/set-state-in-effect
    if (token) void refresh();
  }, [token, refresh]);

  async function authenticate(event: FormEvent) {
    event.preventDefault();
    if (register && password.length < 8)
      return setNotice("Use at least 8 characters for your password.");
    setSubmitting(true);
    setNotice("");
    const body = register
      ? { company_name: company, email, password }
      : { email, password };
    try {
      const response = await fetch(
        `${API}/auth/${register ? "register" : "login"}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
      );
      const data = await response.json();
      if (!response.ok)
        return setNotice(
          typeof data.detail === "string"
            ? data.detail
            : "Please check your details and try again.",
        );
      localStorage.setItem("nexusdesk_token", data.access_token);
      setNotice("");
      setPassword("");
      setToken(data.access_token);
    } catch {
      setNotice("We couldn't connect to NexusDesk. Please try again.");
    } finally {
      setSubmitting(false);
    }
  }

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const input = event.currentTarget.elements.namedItem(
      "file",
    ) as HTMLInputElement;
    if (!input.files?.[0]) return;
    const form = new FormData();
    form.append("file", input.files[0]);
    const response = await fetch(`${API}/documents`, {
      method: "POST",
      headers,
      body: form,
    });
    const data = await response.json();
    setKnowledgeNotice(
      response.ok
        ? `${data.filename} added (${data.chunk_count} chunks)`
        : data.detail,
    );
    input.value = "";
  }

  async function chat(event: FormEvent) {
    event.preventDefault();
    setAnswer("Thinking…");
    const response = await fetch(`${API}/chat`, {
      method: "POST",
      headers: { ...headers, "Content-Type": "application/json" },
      body: JSON.stringify({ message: question }),
    });
    const data = await response.json();
    setAnswer(response.ok ? `${data.answer} · ${data.decision}` : data.detail);
    setQuestion("");
    await refresh();
  }

  if (!authReady)
    return (
      <main className="grid min-h-screen place-items-center">
        <p className="text-slate-400">Loading NexusDesk…</p>
      </main>
    );

  if (!token)
    return (
      <main className="grid min-h-screen place-items-center p-6">
        <section className="w-full max-w-md">
          <form onSubmit={authenticate} className="glass p-8">
            <Logo />
            <h1 className="mt-8 text-3xl font-semibold">
              {register ? "Create your workspace" : "Welcome back"}
            </h1>
            <p className="mt-2 text-slate-400">
              {register
                ? "Set up your secure company support workspace."
                : "Sign in to manage your support operations."}
            </p>
            {register && (
              <label className="mt-6 block text-sm text-slate-300">
                Company name
                <input
                  className="field mt-2"
                  value={company}
                  onChange={(e) => setCompany(e.target.value)}
                  autoComplete="organization"
                  placeholder="Acme Ltd"
                  minLength={2}
                  required
                />
              </label>
            )}
            <label
              className={`${register ? "mt-4" : "mt-6"} block text-sm text-slate-300`}
            >
              Work email
              <input
                className="field mt-2"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                autoComplete="email"
                placeholder="you@company.com"
                required
              />
            </label>
            <label className="mt-4 block text-sm text-slate-300">
              Password
              <div className="relative">
                <input
                  className="field mt-2 pr-16"
                  type={showPassword ? "text" : "password"}
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete={register ? "new-password" : "current-password"}
                  placeholder={
                    register ? "At least 8 characters" : "Your password"
                  }
                  minLength={register ? 8 : undefined}
                  required
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-4 top-5 text-xs text-slate-400"
                >
                  {showPassword ? "Hide" : "Show"}
                </button>
              </div>
            </label>
            {notice && (
              <p
                role="alert"
                className="mt-4 rounded-lg border border-rose-400/20 bg-rose-400/10 p-3 text-sm text-rose-200"
              >
                {notice}
              </p>
            )}
            <button
              disabled={submitting}
              className="primary mt-5 w-full disabled:cursor-not-allowed disabled:opacity-60"
            >
              {submitting
                ? "Please wait…"
                : register
                  ? "Create workspace"
                  : "Sign in"}
            </button>
            <button
              type="button"
              onClick={() => {
                setRegister(!register);
                setNotice("");
                setPassword("");
              }}
              className="mt-5 w-full text-sm text-teal"
            >
              {register
                ? "Already have an account? Sign in"
                : "New to NexusDesk? Create an account"}
            </button>
          </form>
          <p className="mt-4 text-center text-xs text-slate-500">
            Your workspace and knowledge remain private to your company.
          </p>
        </section>
      </main>
    );

  return (
    <main className="mx-auto min-h-screen max-w-7xl p-6 lg:p-10">
      <header className="flex items-center justify-between">
        <Logo />
          <button
            onClick={() => {
              localStorage.removeItem("nexusdesk_token");
              setToken("");
              setMetrics(null);
              setConversations([]);
              setNotice("");
            }}
          className="text-sm text-slate-400"
        >
          Sign out
        </button>
      </header>
      <section className="mt-10 grid gap-4 md:grid-cols-4">
        {[
          ["Conversations", metrics?.total],
          ["Open", metrics?.open],
          ["Escalated", metrics?.escalated],
          ["Resolution rate", `${metrics?.resolution_rate || 0}%`],
        ].map(([label, value]) => (
          <div className="glass p-5" key={label}>
            <p className="text-sm text-slate-400">{label}</p>
            <p className="mt-2 text-3xl font-semibold">{value ?? 0}</p>
          </div>
        ))}
      </section>
      <section className="mt-6 grid gap-6 lg:grid-cols-[1.4fr_.6fr]">
        <div className="glass p-6">
          <div className="flex items-center justify-between">
            <h2 className="text-xl font-semibold">Recent transcripts</h2>
            <select
              className="field w-auto py-2"
              value={filter}
              onChange={(e) => setFilter(e.target.value)}
            >
              <option value="">All status</option>
              <option>open</option>
              <option>resolved</option>
              <option>escalated</option>
            </select>
          </div>
          <div className="mt-5 space-y-3">
            {conversations.map((c) => (
              <div key={c.id} className="rounded-xl border border-white/10 p-4">
                <div className="flex justify-between">
                  <span>{c.customer_email || "Anonymous customer"}</span>
                  <span className={`status ${c.status}`}>{c.status}</span>
                </div>
                {c.escalation_reason && (
                  <p className="mt-2 text-sm text-amber-200">
                    {c.escalation_reason}
                  </p>
                )}
                <p className="mt-2 text-xs text-slate-500">
                  {new Date(c.updated_at).toLocaleString()}
                </p>
              </div>
            ))}
            {!conversations.length && (
              <p className="py-10 text-center text-slate-500">
                No conversations yet.
              </p>
            )}
          </div>
        </div>
        <div className="space-y-6">
          <form onSubmit={upload} className="glass p-6">
            <h2 className="text-xl font-semibold">Knowledge</h2>
            <p className="mt-2 text-sm text-slate-400">
              Upload TXT, Markdown or PDF.
            </p>
            <input
              name="file"
              type="file"
              accept=".txt,.md,.markdown,.pdf"
              className="mt-5 block w-full text-sm"
              required
            />
            <button className="primary mt-4 w-full">Add document</button>
            {knowledgeNotice && (
              <p className="mt-3 text-sm text-teal">{knowledgeNotice}</p>
            )}
          </form>
          <div className="glass p-6">
            <h2 className="text-xl font-semibold">Knowledge gaps</h2>
            <ul className="mt-3 space-y-2 text-sm text-slate-300">
              {metrics?.knowledge_gaps.map((gap, i) => (
                <li key={i}>• {gap}</li>
              ))}
              {!metrics?.knowledge_gaps.length && (
                <li className="text-slate-500">No gaps detected.</li>
              )}
            </ul>
          </div>
        </div>
      </section>
      <form onSubmit={chat} className="glass mt-6 p-6">
        <h2 className="text-xl font-semibold">Test your assistant</h2>
        {answer && (
          <p className="mt-4 rounded-xl bg-white/5 p-4 text-sm leading-6">
            {answer}
          </p>
        )}
        <div className="mt-4 flex gap-3">
          <input
            className="field"
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Ask a customer question…"
            required
          />
          <button className="primary">Send</button>
        </div>
      </form>
    </main>
  );
}

function Logo() {
  return (
    <div className="text-xl font-semibold">
      <span className="text-teal">Nexus</span>
      <span className="text-gold">Desk</span>
    </div>
  );
}
