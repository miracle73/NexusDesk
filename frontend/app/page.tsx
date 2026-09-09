"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";

const API = process.env.NEXT_PUBLIC_API_URL || "/api/v1";
type Metrics = { total: number; open: number; resolved: number; escalated: number; resolution_rate: number; knowledge_gaps: string[] };
type Conversation = { id: string; customer_email?: string; status: string; escalation_reason?: string; updated_at: string };

export default function Home() {
  const [token, setToken] = useState("");
  const [company, setCompany] = useState("CiphezNexus Demo");
  const [email, setEmail] = useState("demo@cipheznexus.com");
  const [password, setPassword] = useState("DemoPass123!");
  const [register, setRegister] = useState(false);
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [filter, setFilter] = useState("");
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [notice, setNotice] = useState("");
  const headers = { Authorization: `Bearer ${token}` };

  const refresh = useCallback(async () => {
    const currentHeaders = { Authorization: `Bearer ${token}` };
    const [m, c] = await Promise.all([fetch(`${API}/conversations/metrics`, { headers: currentHeaders }), fetch(`${API}/conversations${filter ? `?status=${filter}` : ""}`, { headers: currentHeaders })]);
    if (m.ok) setMetrics(await m.json());
    if (c.ok) setConversations(await c.json());
  }, [filter, token]);

  useEffect(() => { const saved = localStorage.getItem("nexusdesk_token"); if (saved) queueMicrotask(() => setToken(saved)); }, []);
  // Data is intentionally refreshed when authentication or the status filter changes.
  // eslint-disable-next-line react-hooks/set-state-in-effect
  useEffect(() => { if (token) void refresh(); }, [token, refresh]);

  async function authenticate(event: FormEvent) {
    event.preventDefault(); setNotice("");
    const body = register ? { company_name: company, email, password } : { email, password };
    const response = await fetch(`${API}/auth/${register ? "register" : "login"}`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    const data = await response.json();
    if (!response.ok) return setNotice(data.detail || "Authentication failed");
    localStorage.setItem("nexusdesk_token", data.access_token); setToken(data.access_token);
  }

  async function upload(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); const input = event.currentTarget.elements.namedItem("file") as HTMLInputElement;
    if (!input.files?.[0]) return;
    const form = new FormData(); form.append("file", input.files[0]);
    const response = await fetch(`${API}/documents`, { method: "POST", headers, body: form });
    const data = await response.json(); setNotice(response.ok ? `${data.filename} added (${data.chunk_count} chunks)` : data.detail); input.value = "";
  }

  async function chat(event: FormEvent) {
    event.preventDefault(); setAnswer("Thinking…");
    const response = await fetch(`${API}/chat`, { method: "POST", headers: { ...headers, "Content-Type": "application/json" }, body: JSON.stringify({ message: question }) });
    const data = await response.json(); setAnswer(response.ok ? `${data.answer} · ${data.decision}` : data.detail); setQuestion(""); await refresh();
  }

  if (!token) return <main className="grid min-h-screen place-items-center p-6"><form onSubmit={authenticate} className="glass w-full max-w-md p-8"><Logo /><h1 className="mt-8 text-3xl font-semibold">{register ? "Create your workspace" : "Welcome back"}</h1><p className="mt-2 text-slate-400">AI support, grounded in your company knowledge.</p>{register && <input className="field mt-6" value={company} onChange={e => setCompany(e.target.value)} placeholder="Company name" required />}<input className="field mt-3" type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="Email" required /><input className="field mt-3" type="password" value={password} onChange={e => setPassword(e.target.value)} placeholder="Password" required /><button className="primary mt-5 w-full">{register ? "Create company" : "Sign in"}</button>{notice && <p className="mt-3 text-sm text-rose-300">{notice}</p>}<button type="button" onClick={() => setRegister(!register)} className="mt-5 w-full text-sm text-teal">{register ? "Already registered? Sign in" : "New company? Register"}</button></form></main>;

  return <main className="mx-auto min-h-screen max-w-7xl p-6 lg:p-10"><header className="flex items-center justify-between"><Logo /><button onClick={() => { localStorage.removeItem("nexusdesk_token"); setToken(""); }} className="text-sm text-slate-400">Sign out</button></header><section className="mt-10 grid gap-4 md:grid-cols-4">{[["Conversations", metrics?.total], ["Open", metrics?.open], ["Escalated", metrics?.escalated], ["Resolution rate", `${metrics?.resolution_rate || 0}%`]].map(([label, value]) => <div className="glass p-5" key={label}><p className="text-sm text-slate-400">{label}</p><p className="mt-2 text-3xl font-semibold">{value ?? 0}</p></div>)}</section><section className="mt-6 grid gap-6 lg:grid-cols-[1.4fr_.6fr]"><div className="glass p-6"><div className="flex items-center justify-between"><h2 className="text-xl font-semibold">Recent transcripts</h2><select className="field w-auto py-2" value={filter} onChange={e => setFilter(e.target.value)}><option value="">All status</option><option>open</option><option>resolved</option><option>escalated</option></select></div><div className="mt-5 space-y-3">{conversations.map(c => <div key={c.id} className="rounded-xl border border-white/10 p-4"><div className="flex justify-between"><span>{c.customer_email || "Anonymous customer"}</span><span className={`status ${c.status}`}>{c.status}</span></div>{c.escalation_reason && <p className="mt-2 text-sm text-amber-200">{c.escalation_reason}</p>}<p className="mt-2 text-xs text-slate-500">{new Date(c.updated_at).toLocaleString()}</p></div>)}{!conversations.length && <p className="py-10 text-center text-slate-500">No conversations yet.</p>}</div></div><div className="space-y-6"><form onSubmit={upload} className="glass p-6"><h2 className="text-xl font-semibold">Knowledge</h2><p className="mt-2 text-sm text-slate-400">Upload TXT, Markdown or PDF.</p><input name="file" type="file" accept=".txt,.md,.markdown,.pdf" className="mt-5 block w-full text-sm" required /><button className="primary mt-4 w-full">Add document</button>{notice && <p className="mt-3 text-sm text-teal">{notice}</p>}</form><div className="glass p-6"><h2 className="text-xl font-semibold">Knowledge gaps</h2><ul className="mt-3 space-y-2 text-sm text-slate-300">{metrics?.knowledge_gaps.map((gap, i) => <li key={i}>• {gap}</li>)}{!metrics?.knowledge_gaps.length && <li className="text-slate-500">No gaps detected.</li>}</ul></div></div></section><form onSubmit={chat} className="glass mt-6 p-6"><h2 className="text-xl font-semibold">Test your assistant</h2>{answer && <p className="mt-4 rounded-xl bg-white/5 p-4 text-sm leading-6">{answer}</p>}<div className="mt-4 flex gap-3"><input className="field" value={question} onChange={e => setQuestion(e.target.value)} placeholder="Ask a customer question…" required /><button className="primary">Send</button></div></form></main>;
}

function Logo() { return <div className="text-xl font-semibold"><span className="text-teal">Nexus</span><span className="text-gold">Desk</span></div>; }
