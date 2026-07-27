const features = [
  "Tenant-aware knowledge",
  "RAG-powered answers",
  "Human escalation",
  "Support analytics",
];

export default function Home() {
  return (
    <main className="mx-auto flex min-h-screen max-w-6xl flex-col px-6 py-10">
      <nav className="flex items-center justify-between">
        <div className="text-xl font-semibold tracking-tight">
          <span className="text-teal">Nexus</span>
          <span className="text-gold">Desk</span>
        </div>
        <span className="rounded-full border border-white/10 px-3 py-1 text-xs text-slate-300">
          MVP scaffold
        </span>
      </nav>

      <section className="grid flex-1 items-center gap-12 py-20 lg:grid-cols-[1.2fr_0.8fr]">
        <div>
          <p className="mb-4 text-sm font-semibold uppercase tracking-[0.2em] text-teal">
            AI customer support
          </p>
          <h1 className="max-w-3xl text-5xl font-bold leading-tight tracking-tight sm:text-6xl">
            Helpful answers. Human backup. One intelligent desk.
          </h1>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-300">
            NexusDesk learns from your company knowledge, answers customer
            questions, and escalates uncertain requests to your team.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            {features.map((feature) => (
              <span
                key={feature}
                className="rounded-full border border-white/10 bg-white/5 px-4 py-2 text-sm text-slate-200"
              >
                {feature}
              </span>
            ))}
          </div>
        </div>

        <div className="rounded-3xl border border-white/10 bg-white/[0.06] p-6 shadow-2xl backdrop-blur">
          <div className="mb-6 flex items-center gap-3 border-b border-white/10 pb-4">
            <span className="h-3 w-3 rounded-full bg-teal shadow-[0_0_16px_#16d9c5]" />
            <p className="font-medium">NexusDesk Assistant</p>
          </div>
          <div className="space-y-4 text-sm">
            <div className="ml-auto max-w-[85%] rounded-2xl rounded-br-md bg-teal px-4 py-3 text-ink">
              How do I reset my password?
            </div>
            <div className="max-w-[90%] rounded-2xl rounded-bl-md bg-white/10 px-4 py-3 leading-6 text-slate-200">
              Open account settings, select Security, then choose Reset
              password. I can guide you through it.
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
