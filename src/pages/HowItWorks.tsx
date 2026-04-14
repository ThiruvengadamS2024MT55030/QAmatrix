import { Link } from "react-router-dom";
import { Shield, Database, Brain, FileSpreadsheet, BarChart3, Upload, ArrowRight, CheckCircle2, Server, Layout, Cpu, Layers, Code2, Terminal, ArrowDown, RefreshCw, AlertTriangle, Settings } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import Footer from "@/components/Footer";

// ─── Closed-Loop Workflow Data ─────────────────────────────────────────

const closedLoopSteps = [
  {
    id: 1,
    title: "Data Ingestion",
    subtitle: "Excel / CSV Upload",
    desc: "QA Matrix and defect reports (DVX, SCA, YARD) are uploaded. Auto-header detection parses columns, validates data types, and normalizes entries.",
    color: "border-red-400 dark:border-red-600",
    bg: "bg-red-50 dark:bg-red-950/30",
    accent: "text-red-600 dark:text-red-400",
    icon: Upload,
  },
  {
    id: 2,
    title: "Preprocessing",
    subtitle: "Cleaning & Separation",
    desc: "Raw data is cleaned, deduplicated, and separated by source. Defect codes and location codes are extracted and validated against known patterns.",
    color: "border-orange-400 dark:border-orange-600",
    bg: "bg-orange-50 dark:bg-orange-950/30",
    accent: "text-orange-600 dark:text-orange-400",
    icon: Settings,
  },
  {
    id: 3,
    title: "AI Semantic Matching",
    subtitle: "Google Gemini NLP",
    desc: "Defects are batched and sent to Google Gemini for semantic analysis. The AI evaluates descriptions, locations, and component types to pair each defect with the best-fit QA concern.",
    color: "border-purple-400 dark:border-purple-600",
    bg: "bg-purple-50 dark:bg-purple-950/30",
    accent: "text-purple-600 dark:text-purple-400",
    icon: Brain,
  },
  {
    id: 4,
    title: "Confidence Filtering",
    subtitle: "Threshold ≥ 0.3",
    desc: "Each match receives a confidence score (0–1). Matches below 0.3 are flagged as unmatched for manual review. Users can unpair, reassign, or create new concerns.",
    color: "border-violet-400 dark:border-violet-600",
    bg: "bg-violet-50 dark:bg-violet-950/30",
    accent: "text-violet-600 dark:text-violet-400",
    icon: AlertTriangle,
  },
  {
    id: 5,
    title: "Recurrence Aggregation",
    subtitle: "W-6 → W-1 Rolling Window",
    desc: "Matched defect quantities are aggregated into the W-1 (last week) bucket. The 6-week rolling window shifts forward each cycle, tracking recurrence trends over time.",
    color: "border-green-400 dark:border-green-600",
    bg: "bg-green-50 dark:bg-green-950/30",
    accent: "text-green-600 dark:text-green-400",
    icon: RefreshCw,
  },
  {
    id: 6,
    title: "Rating Calculation",
    subtitle: "MFG / Quality / Plant",
    desc: "Scores from Trim (T10–T100), Chassis (C10–C80), Final (F10–F100), and QControl checkpoints are summed. MFG, Quality, and Plant ratings auto-calculate.",
    color: "border-teal-400 dark:border-teal-600",
    bg: "bg-teal-50 dark:bg-teal-950/30",
    accent: "text-teal-600 dark:text-teal-400",
    icon: BarChart3,
  },
  {
    id: 7,
    title: "Status Automation",
    subtitle: "OK / NG Determination",
    desc: "Workstation: NG if recurrence exists. MFG: OK if MFG Rating ≥ Defect Rating. Plant: OK if Plant Rating ≥ Defect Rating. All statuses update in real-time.",
    color: "border-blue-400 dark:border-blue-600",
    bg: "bg-blue-50 dark:bg-blue-950/30",
    accent: "text-blue-600 dark:text-blue-400",
    icon: CheckCircle2,
  },
  {
    id: 8,
    title: "Dashboard & Export",
    subtitle: "Visualization & Feedback",
    desc: "Summary dashboards show NG/OK breakdowns, designation distribution, and rating analytics. Data exports to Excel/CSV. New defect uploads restart the cycle.",
    color: "border-indigo-400 dark:border-indigo-600",
    bg: "bg-indigo-50 dark:bg-indigo-950/30",
    accent: "text-indigo-600 dark:text-indigo-400",
    icon: FileSpreadsheet,
  },
];

const techStack = [
  { name: "React 18", desc: "Component-based UI", icon: Layout, category: "Frontend" },
  { name: "TypeScript", desc: "Type-safe code", icon: Cpu, category: "Frontend" },
  { name: "Tailwind CSS", desc: "Utility styling", icon: Layers, category: "Frontend" },
  { name: "Recharts", desc: "Data visualization", icon: BarChart3, category: "Frontend" },
  { name: "PostgreSQL", desc: "Relational DB", icon: Database, category: "Backend" },
  { name: "Edge Functions", desc: "Serverless logic", icon: Server, category: "Backend" },
  { name: "Google Gemini", desc: "AI/NLP matching", icon: Brain, category: "AI/NLP" },
  { name: "XLSX Parser", desc: "Excel I/O", icon: FileSpreadsheet, category: "Data" },
  { name: "Python / Pandas", desc: "Offline pipeline", icon: Terminal, category: "Scripts" },
];

const pythonModules = [
  {
    file: "defect_processor.py",
    title: "Data Ingestion & Validation",
    desc: "Parses raw defect files, auto-detects headers, normalizes columns, validates data quality, and deduplicates entries.",
    functions: ["load_defect_file()", "preprocess_defects()", "validate_defects()", "deduplicate_defects()"],
  },
  {
    file: "recurrence_aggregator.py",
    title: "Recurrence Aggregation",
    desc: "Manages the 6-week rolling window, shifts weekly buckets, aggregates defect counts into W-1, and detects trends.",
    functions: ["shift_weekly_window()", "aggregate_defect_counts()", "weekly_trend_analysis()"],
  },
  {
    file: "severity_scorer.py",
    title: "Severity & Controllability",
    desc: "Implements 1-3-5 defect rating and calculates controllability across Trim, Chassis, and Final assembly areas.",
    functions: ["calculate_mfg_rating()", "calculate_quality_rating()", "calculate_plant_rating()"],
  },
  {
    file: "rating_calculator.py",
    title: "MFG / Plant Ratings",
    desc: "Computes all three ratings from JSONB score data. Mirrors the frontend recalculateStatuses() function exactly.",
    functions: ["recalculate_entry()", "batch_recalculate()", "generate_rating_report()"],
  },
  {
    file: "status_automator.py",
    title: "OK/NG Automation",
    desc: "Vectorized status computation. Detects transitions, generates diff reports, and applies repeat updates.",
    functions: ["compute_statuses_vectorized()", "detect_status_changes()", "generate_ng_summary()"],
  },
  {
    file: "ai_defect_matcher.py",
    title: "AI Defect Matching",
    desc: "Semantic matching via fuzzy NLP (Jaccard, Dice, synonym expansion) and Google Gemini AI with batch fallback.",
    functions: ["fuzzy_match_single()", "ai_match_batch()", "aggregate_matches()"],
  },
];

const HowItWorks = () => {
  return (
    <div className="min-h-screen bg-background flex flex-col">
      {/* Header */}
      <header className="border-b border-border bg-card/80 backdrop-blur-sm sticky top-0 z-20">
        <div className="max-w-[1200px] mx-auto px-4 py-3 flex items-center gap-3">
          <Link to="/" className="p-2 rounded-lg bg-primary/10">
            <Shield className="w-5 h-5 text-primary" />
          </Link>
          <div>
            <h1 className="text-lg font-bold tracking-tight">How It Works</h1>
            <p className="text-[11px] text-muted-foreground">QA Matrix — Closed-Loop Workflow</p>
          </div>
          <Link to="/" className="ml-auto text-xs font-semibold text-primary hover:underline">
            ← Back to Matrix
          </Link>
        </div>
      </header>

      <main className="max-w-[1200px] mx-auto px-4 py-10 space-y-16 flex-1">
        {/* Hero */}
        <section className="text-center space-y-4">
          <h2 className="text-3xl font-extrabold tracking-tight">
            Closed-Loop <span className="text-primary">Quality Workflow</span>
          </h2>
          <p className="text-muted-foreground max-w-2xl mx-auto text-sm leading-relaxed">
            A continuous improvement cycle where defect data feeds into AI-powered matching, 
            auto-calculates ratings and statuses, and loops back for the next inspection period.
          </p>
        </section>

        {/* ═══ CLOSED-LOOP DIAGRAM ═══ */}
        <section className="space-y-6">
          <h3 className="text-xl font-bold tracking-tight">Application Workflow</h3>
          <Card className="overflow-hidden">
            <CardContent className="pt-8 pb-8 px-6">
              {/* Circular / loop layout */}
              <div className="relative">
                {/* Steps in a connected chain */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                  {closedLoopSteps.map((step, i) => (
                    <div key={step.id} className="relative group">
                      <div className={`${step.bg} ${step.color} border-2 rounded-xl p-4 h-full transition-all hover:shadow-md`}>
                        <div className="flex items-center gap-2 mb-2">
                          <div className={`w-6 h-6 rounded-full bg-card flex items-center justify-center border ${step.color}`}>
                            <span className={`text-[10px] font-black ${step.accent}`}>{step.id}</span>
                          </div>
                          <step.icon className={`w-4 h-4 ${step.accent}`} />
                        </div>
                        <h4 className="text-xs font-bold text-foreground">{step.title}</h4>
                        <p className={`text-[10px] font-semibold ${step.accent} mb-1.5`}>{step.subtitle}</p>
                        <p className="text-[10px] text-muted-foreground leading-relaxed">{step.desc}</p>
                      </div>
                      {/* Arrow to next */}
                      {i < closedLoopSteps.length - 1 && i % 4 !== 3 && (
                        <div className="hidden lg:block absolute top-1/2 -right-3 -translate-y-1/2 z-10">
                          <ArrowRight className="w-4 h-4 text-muted-foreground" />
                        </div>
                      )}
                      {/* Down arrow between rows */}
                      {i === 3 && (
                        <div className="hidden lg:block absolute -bottom-3 left-1/2 -translate-x-1/2 z-10">
                          <ArrowDown className="w-4 h-4 text-muted-foreground" />
                        </div>
                      )}
                    </div>
                  ))}
                </div>

                {/* Feedback loop arrow */}
                <div className="mt-6 pt-4 border-t-2 border-dashed border-primary/30 flex items-center justify-center gap-3">
                  <RefreshCw className="w-5 h-5 text-primary animate-spin" style={{ animationDuration: '4s' }} />
                  <div className="text-center">
                    <p className="text-xs font-bold text-primary">Continuous Feedback Loop</p>
                    <p className="text-[10px] text-muted-foreground">
                      Export triggers new data collection → Next week's defect uploads restart the cycle → 
                      W-1 shifts to W-2, new W-1 receives fresh data
                    </p>
                  </div>
                  <RefreshCw className="w-5 h-5 text-primary animate-spin" style={{ animationDuration: '4s', animationDirection: 'reverse' }} />
                </div>
              </div>
            </CardContent>
          </Card>
        </section>

        {/* Status Calculation Logic */}
        <section className="space-y-6">
          <h3 className="text-xl font-bold tracking-tight">Status Calculation Rules</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card className="border-l-4 border-l-primary">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">MFG Rating</CardTitle>
              </CardHeader>
              <CardContent className="text-xs text-muted-foreground space-y-2">
                <p><code className="bg-muted px-1.5 py-0.5 rounded font-mono text-foreground/70">sum(Trim) + sum(Chassis) + sum(Final)</code></p>
                <p className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-green-500" /> OK if MFG Rating ≥ Defect Rating</p>
                <p className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-destructive" /> NG otherwise</p>
              </CardContent>
            </Card>
            <Card className="border-l-4 border-l-primary">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Workstation Status</CardTitle>
              </CardHeader>
              <CardContent className="text-xs text-muted-foreground space-y-2">
                <p><code className="bg-muted px-1.5 py-0.5 rounded font-mono text-foreground/70">weeklyRecurrence.some(w → w &gt; 0)</code></p>
                <p className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-destructive" /> NG if any recurrence exists</p>
                <p className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-green-500" /> OK if no recurrence + MFG OK</p>
              </CardContent>
            </Card>
            <Card className="border-l-4 border-l-primary">
              <CardHeader className="pb-2">
                <CardTitle className="text-sm">Plant Status</CardTitle>
              </CardHeader>
              <CardContent className="text-xs text-muted-foreground space-y-2">
                <p><code className="bg-muted px-1.5 py-0.5 rounded font-mono text-foreground/70">ResidualTorque + QControl + QDetail</code></p>
                <p className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-green-500" /> OK if Plant Rating ≥ Defect Rating</p>
                <p className="flex items-center gap-1.5"><span className="w-2 h-2 rounded-full bg-destructive" /> NG otherwise</p>
              </CardContent>
            </Card>
          </div>
        </section>

        {/* ═══ PYTHON MODULES ═══ */}
        <section className="space-y-6">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-lg bg-primary/10">
              <Code2 className="w-5 h-5 text-primary" />
            </div>
            <div>
              <h3 className="text-xl font-bold tracking-tight">Python Processing Modules</h3>
              <p className="text-xs text-muted-foreground">Standalone scripts mirroring the application's closed-loop logic</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {pythonModules.map((mod, i) => (
              <Card key={i} className="hover:border-primary/30 transition-colors">
                <CardHeader className="pb-2">
                  <CardTitle className="text-sm flex items-center gap-2">
                    <Terminal className="w-4 h-4 text-primary" />
                    {mod.title}
                  </CardTitle>
                  <p className="text-[10px] font-mono text-muted-foreground">{mod.file}</p>
                </CardHeader>
                <CardContent className="space-y-3">
                  <p className="text-xs text-muted-foreground leading-relaxed">{mod.desc}</p>
                  <div className="flex flex-wrap gap-1">
                    {mod.functions.map((fn, j) => (
                      <span key={j} className="text-[9px] font-mono bg-primary/10 text-primary px-1.5 py-0.5 rounded">
                        {fn}
                      </span>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        {/* Tech Stack */}
        <section className="space-y-6">
          <h3 className="text-xl font-bold tracking-tight">Technology Stack</h3>
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-3">
            {techStack.map((t, i) => (
              <Card key={i} className="hover:border-primary/40 transition-colors">
                <CardContent className="pt-4 pb-4 flex items-start gap-3">
                  <div className="p-2 rounded-md bg-primary/10">
                    <t.icon className="w-4 h-4 text-primary" />
                  </div>
                  <div>
                    <p className="text-xs font-bold">{t.name}</p>
                    <p className="text-[10px] text-muted-foreground">{t.desc}</p>
                    <span className="text-[9px] font-mono text-primary/60 uppercase">{t.category}</span>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        </section>

        {/* Architecture */}
        <section className="space-y-6">
          <h3 className="text-xl font-bold tracking-tight">System Architecture</h3>
          <Card>
            <CardContent className="pt-6 pb-6">
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 text-center">
                <div className="space-y-3">
                  <div className="p-3 rounded-xl bg-primary/10 inline-block">
                    <Layout className="w-6 h-6 text-primary" />
                  </div>
                  <h4 className="text-sm font-bold">Frontend</h4>
                  <p className="text-xs text-muted-foreground">React SPA with QA Matrix Table, Repeats Tab, Defect Upload, and Dashboard views. State managed via hooks and TanStack Query.</p>
                </div>
                <div className="space-y-3">
                  <div className="p-3 rounded-xl bg-primary/10 inline-block">
                    <Server className="w-6 h-6 text-primary" />
                  </div>
                  <h4 className="text-sm font-bold">Backend</h4>
                  <p className="text-xs text-muted-foreground">PostgreSQL with 3 tables (qa_matrix_entries, defect_data, final_defect). Edge Functions handle AI matching and defect management.</p>
                </div>
                <div className="space-y-3">
                  <div className="p-3 rounded-xl bg-primary/10 inline-block">
                    <Brain className="w-6 h-6 text-primary" />
                  </div>
                  <h4 className="text-sm font-bold">AI/NLP Layer</h4>
                  <p className="text-xs text-muted-foreground">Google Gemini via Edge Functions for semantic defect matching. Tool-calling extracts structured output with confidence scoring.</p>
                </div>
              </div>
            </CardContent>
          </Card>
        </section>

        {/* Backend Functions */}
        <section className="space-y-6">
          <h3 className="text-xl font-bold tracking-tight">Backend Functions</h3>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm flex items-center gap-2"><Brain className="w-4 h-4" /> match-defects</CardTitle></CardHeader>
              <CardContent className="text-xs text-muted-foreground">Sends batched defects + concerns to Google Gemini. Returns semantic matches with confidence scores via tool-calling.</CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm flex items-center gap-2"><Database className="w-4 h-4" /> delete-defects</CardTitle></CardHeader>
              <CardContent className="text-xs text-muted-foreground">Password-protected bulk deletion of defect data by source (DVX/SCA/YARD/ALL/FINAL).</CardContent>
            </Card>
            <Card>
              <CardHeader className="pb-2"><CardTitle className="text-sm flex items-center gap-2"><FileSpreadsheet className="w-4 h-4" /> fetch-spreadsheet</CardTitle></CardHeader>
              <CardContent className="text-xs text-muted-foreground">Imports QA matrix data from external spreadsheet sources into the system.</CardContent>
            </Card>
          </div>
        </section>
      </main>

      <Footer />
    </div>
  );
};

export default HowItWorks;
