import { useCallback, useEffect, useState } from "react"
import {
  Activity,
  AlertTriangle,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  RefreshCw,
  Server,
  XCircle,
} from "lucide-react"
import Navbar from "../components/Navbar"
import Footer from "../components/Footer"
import { getMonitorDashboard, getObservabilityTraces, getTraceDetail } from "../lib/api"

// ── helpers ──────────────────────────────────────────────────────────────────

function fmt(ts) {
  if (!ts) return "—"
  try {
    return new Date(ts).toLocaleString()
  } catch {
    return ts
  }
}

function shortId(id) {
  return id ? id.slice(0, 8) + "…" : "—"
}

function healthColor(h) {
  if (h === "healthy") return "text-emerald-400"
  if (h === "degraded") return "text-amber-400"
  return "text-red-400"
}

function healthBg(h) {
  if (h === "healthy") return "bg-emerald-500/15 border-emerald-500/30"
  if (h === "degraded") return "bg-amber-500/15 border-amber-500/30"
  return "bg-red-500/15 border-red-500/30"
}

function verdictBadge(v) {
  const map = {
    SUPPORTED: "bg-emerald-500/20 text-emerald-400 border-emerald-500/30",
    REFUTED: "bg-red-500/20 text-red-400 border-red-500/30",
    MISLEADING: "bg-amber-500/20 text-amber-400 border-amber-500/30",
    UNVERIFIED: "bg-slate-500/20 text-slate-400 border-slate-500/30",
  }
  return map[v] || "bg-surface-elevated text-on-surface-variant border-surface-elevated"
}

// ── sub-components ────────────────────────────────────────────────────────────

function StatCard({ label, value, sub, icon: Icon, accent = "text-primary" }) {
  return (
    <div className="surface-card rounded-xl p-5 flex flex-col gap-2">
      <div className="flex items-center gap-2 text-on-surface-variant text-sm font-medium">
        {Icon && <Icon className={`h-4 w-4 ${accent}`} />}
        {label}
      </div>
      <div className={`text-3xl font-black tracking-tight ${accent}`}>{value}</div>
      {sub && <div className="text-xs text-on-surface-variant">{sub}</div>}
    </div>
  )
}

function AgentRow({ agent }) {
  const pct = agent.total_runs
    ? Math.round((agent.passed / agent.total_runs) * 100)
    : 0
  const color = pct === 100 ? "bg-emerald-500" : pct >= 70 ? "bg-amber-500" : "bg-red-500"
  return (
    <tr className="border-t border-surface-elevated hover:bg-surface-elevated/40 transition-colors">
      <td className="py-3 px-4 font-mono text-sm text-text-primary">{agent.name}</td>
      <td className="py-3 px-4 text-center text-sm">{agent.total_runs}</td>
      <td className="py-3 px-4 text-center text-emerald-400 text-sm font-semibold">{agent.passed}</td>
      <td className="py-3 px-4 text-center text-red-400 text-sm font-semibold">{agent.failed}</td>
      <td className="py-3 px-4 text-center text-sm text-on-surface-variant">{agent.retries}</td>
      <td className="py-3 px-4">
        <div className="flex items-center gap-2">
          <div className="flex-1 h-2 bg-surface-elevated rounded-full overflow-hidden">
            <div className={`h-full rounded-full ${color}`} style={{ width: `${pct}%` }} />
          </div>
          <span className="text-xs text-on-surface-variant w-10 text-right">{pct}%</span>
        </div>
      </td>
      <td className="py-3 px-4 text-xs text-on-surface-variant whitespace-nowrap">{fmt(agent.last_run)}</td>
    </tr>
  )
}

function SpanRow({ span }) {
  const isPass = span.status === "pass"
  return (
    <div className="border border-surface-elevated rounded-lg p-3 bg-surface-elevated/30">
      <div className="flex items-center justify-between mb-2 gap-2 flex-wrap">
        <span className="font-mono text-sm text-text-primary font-semibold">{span.agent}</span>
        <div className="flex items-center gap-2">
          {isPass
            ? <CheckCircle2 className="h-4 w-4 text-emerald-400" />
            : <XCircle className="h-4 w-4 text-red-400" />}
          <span className={`text-xs font-bold ${isPass ? "text-emerald-400" : "text-red-400"}`}>
            {span.status?.toUpperCase()}
          </span>
          <span className="text-xs text-on-surface-variant">{span.duration_seconds}s</span>
          {span.retries > 0 && (
            <span className="text-xs text-amber-400">↻ {span.retries}</span>
          )}
        </div>
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2 text-xs">
        <div>
          <p className="text-on-surface-variant mb-1 font-medium">Input</p>
          <pre className="bg-surface-base rounded p-2 overflow-x-auto text-text-secondary max-h-24 whitespace-pre-wrap break-all">
            {typeof span.input === "object" ? JSON.stringify(span.input, null, 2) : String(span.input ?? "—")}
          </pre>
        </div>
        <div>
          <p className="text-on-surface-variant mb-1 font-medium">Output</p>
          <pre className="bg-surface-base rounded p-2 overflow-x-auto text-text-secondary max-h-24 whitespace-pre-wrap break-all">
            {typeof span.output === "object" ? JSON.stringify(span.output, null, 2) : String(span.output ?? "—")}
          </pre>
        </div>
      </div>
    </div>
  )
}

function TraceRow({ trace, onSelect, expanded, detail, loadingDetail }) {
  return (
    <>
      <tr
        className="border-t border-surface-elevated hover:bg-surface-elevated/40 transition-colors cursor-pointer"
        onClick={() => onSelect(trace.trace_id)}
      >
        <td className="py-3 px-4">
          <div className="flex items-center gap-1 text-on-surface-variant">
            {expanded ? <ChevronDown className="h-3.5 w-3.5" /> : <ChevronRight className="h-3.5 w-3.5" />}
            <span className="font-mono text-xs text-primary">{shortId(trace.trace_id)}</span>
          </div>
        </td>
        <td className="py-3 px-4 text-sm text-text-primary max-w-xs truncate">{trace.claim || "—"}</td>
        <td className="py-3 px-4">
          <span className={`px-2 py-0.5 rounded-full text-xs font-bold border ${verdictBadge(trace.final_verdict)}`}>
            {trace.final_verdict || "—"}
          </span>
        </td>
        <td className="py-3 px-4 text-sm text-center">
          {trace.trust_score != null ? (
            <span className="font-semibold text-primary">{Number(trace.trust_score).toFixed(1)}</span>
          ) : "—"}
        </td>
        <td className="py-3 px-4 text-sm text-center text-on-surface-variant">
          {trace.total_duration_seconds != null ? `${trace.total_duration_seconds}s` : "—"}
        </td>
        <td className="py-3 px-4 text-xs text-on-surface-variant whitespace-nowrap">{fmt(trace.timestamp)}</td>
      </tr>
      {expanded && (
        <tr className="bg-surface-elevated/20">
          <td colSpan={6} className="px-4 py-4">
            {loadingDetail ? (
              <p className="text-on-surface-variant text-sm text-center">Loading spans…</p>
            ) : detail?.spans?.length > 0 ? (
              <div className="flex flex-col gap-2">
                <p className="text-xs font-semibold text-on-surface-variant mb-1">
                  {detail.spans.length} span{detail.spans.length !== 1 ? "s" : ""}
                  {" · "}total {detail.total_duration_seconds}s
                </p>
                {detail.spans.map((span, i) => <SpanRow key={i} span={span} />)}
              </div>
            ) : (
              <p className="text-on-surface-variant text-sm">No spans recorded for this trace.</p>
            )}
          </td>
        </tr>
      )}
    </>
  )
}

// ── main page ─────────────────────────────────────────────────────────────────

export default function MonitorDashboard() {
  const [dashboard, setDashboard] = useState(null)
  const [traces, setTraces] = useState([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [expandedTrace, setExpandedTrace] = useState(null)
  const [traceDetails, setTraceDetails] = useState({})
  const [loadingDetail, setLoadingDetail] = useState(false)

  // silent=true → background refresh, don't re-show the full loading skeleton
  const load = useCallback(async (silent = false) => {
    if (!silent) setLoading(true)
    setError(null)
    try {
      const [dashRes, tracesRes] = await Promise.all([
        getMonitorDashboard(),
        getObservabilityTraces(),
      ])
      setDashboard(dashRes.data)
      setTraces(tracesRes.data?.traces || [])
    } catch (err) {
      setError(err?.response?.data?.detail || err?.message || "Failed to load monitoring data")
    } finally {
      if (!silent) setLoading(false)
    }
  }, [])

  useEffect(() => {
    load()                                          // initial load (shows spinner)
    const id = setInterval(() => load(true), 30_000) // silent refresh every 30s
    return () => clearInterval(id)                 // cleanup on unmount
  }, [load])

  const handleTraceSelect = useCallback(async (traceId) => {
    if (expandedTrace === traceId) {
      setExpandedTrace(null)
      return
    }
    setExpandedTrace(traceId)
    if (traceDetails[traceId]) return
    setLoadingDetail(true)
    try {
      const res = await getTraceDetail(traceId)
      setTraceDetails(prev => ({ ...prev, [traceId]: res.data?.trace }))
    } catch {
      setTraceDetails(prev => ({ ...prev, [traceId]: { spans: [] } }))
    } finally {
      setLoadingDetail(false)
    }
  }, [expandedTrace, traceDetails])

  const health = dashboard?.pipeline_health
  const verdicts = dashboard?.verdicts || {}
  const agents = dashboard?.agents || []

  return (
    <Navbar>
      <main className="flex-1 overflow-y-auto p-6 md:p-10 relative z-10">
        <div className="max-w-7xl mx-auto flex flex-col gap-8 mt-4 pb-12">

          {/* ── Header ── */}
          <div className="flex items-center justify-between flex-wrap gap-4">
            <div>
              <h1 className="text-4xl font-black tracking-tight text-text-primary font-hero-display flex items-center gap-3">
                <Activity className="h-9 w-9 text-primary" />
                Monitor Dashboard
              </h1>
              <p className="text-on-surface-variant mt-1">
                Real-time pipeline health and observability traces
              </p>
            </div>
            <button
              onClick={() => load(false)}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 rounded-lg bg-surface-base border border-surface-elevated text-sm text-on-surface-variant hover:text-primary hover:border-primary/50 transition-colors disabled:opacity-50"
            >
              <RefreshCw className={`h-4 w-4 ${loading ? "animate-spin" : ""}`} />
              Refresh
            </button>
          </div>

          {/* ── Error ── */}
          {error && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-4 flex items-center gap-3 text-red-400 text-sm">
              <AlertTriangle className="h-5 w-5 shrink-0" />
              {error}
            </div>
          )}

          {/* ── Top stat cards ── */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <div className={`col-span-2 md:col-span-1 surface-card border rounded-xl p-5 flex flex-col gap-2 ${healthBg(health)}`}>
              <div className="flex items-center gap-2 text-sm font-medium text-on-surface-variant">
                <Server className="h-4 w-4" />
                Pipeline Health
              </div>
              <div className={`text-3xl font-black capitalize tracking-tight ${healthColor(health)}`}>
                {loading ? "…" : (health || "—")}
              </div>
              <div className="text-xs text-on-surface-variant">
                {fmt(dashboard?.last_updated)}
              </div>
            </div>
            <StatCard
              label="Claims Analyzed"
              value={loading ? "…" : (dashboard?.total_claims_analyzed ?? "—")}
              icon={CheckCircle2}
              accent="text-primary"
            />
            <StatCard
              label="Agents Passing"
              value={loading ? "…" : `${agents.filter(a => a.failed === 0).length}/${agents.length}`}
              icon={Activity}
              accent="text-emerald-400"
            />
            <StatCard
              label="Traces Stored"
              value={loading ? "…" : traces.length}
              icon={Clock}
              accent="text-violet-400"
            />
          </div>

          {/* ── Verdicts ── */}
          {!loading && (
            <div className="surface-card border-surface-elevated rounded-xl p-6">
              <h2 className="text-lg font-bold text-text-primary mb-4">Verdict Distribution</h2>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
                {["SUPPORTED", "REFUTED", "MISLEADING", "UNVERIFIED"].map(v => (
                  <div key={v} className={`rounded-lg p-4 border text-center ${verdictBadge(v)}`}>
                    <div className="text-2xl font-black">{verdicts[v] ?? 0}</div>
                    <div className="text-xs font-semibold mt-1 tracking-wider">{v}</div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* ── Agent stats table ── */}
          {!loading && agents.length > 0 && (
            <div className="surface-card border-surface-elevated rounded-xl overflow-hidden">
              <div className="px-6 py-4 border-b border-surface-elevated">
                <h2 className="text-lg font-bold text-text-primary">Agent Statistics</h2>
              </div>
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead>
                    <tr className="text-xs text-on-surface-variant font-semibold uppercase tracking-wider">
                      <th className="py-3 px-4">Agent</th>
                      <th className="py-3 px-4 text-center">Runs</th>
                      <th className="py-3 px-4 text-center">Passed</th>
                      <th className="py-3 px-4 text-center">Failed</th>
                      <th className="py-3 px-4 text-center">Retries</th>
                      <th className="py-3 px-4">Pass Rate</th>
                      <th className="py-3 px-4">Last Run</th>
                    </tr>
                  </thead>
                  <tbody>
                    {agents.map(a => <AgentRow key={a.name} agent={a} />)}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {/* ── Traces table ── */}
          <div className="surface-card border-surface-elevated rounded-xl overflow-hidden">
            <div className="px-6 py-4 border-b border-surface-elevated flex items-center justify-between">
              <h2 className="text-lg font-bold text-text-primary">Observability Traces</h2>
              <span className="text-xs text-on-surface-variant">Last 20 · Click a row to expand spans</span>
            </div>
            {loading ? (
              <div className="p-8 text-center text-on-surface-variant text-sm animate-pulse">Loading traces…</div>
            ) : traces.length === 0 ? (
              <div className="p-8 text-center text-on-surface-variant text-sm">
                No traces yet — traces are recorded on every /analyze call.
              </div>
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-left">
                  <thead>
                    <tr className="text-xs text-on-surface-variant font-semibold uppercase tracking-wider">
                      <th className="py-3 px-4">Trace ID</th>
                      <th className="py-3 px-4">Claim</th>
                      <th className="py-3 px-4">Verdict</th>
                      <th className="py-3 px-4 text-center">Trust</th>
                      <th className="py-3 px-4 text-center">Duration</th>
                      <th className="py-3 px-4">Timestamp</th>
                    </tr>
                  </thead>
                  <tbody>
                    {traces.map(trace => (
                      <TraceRow
                        key={trace.trace_id}
                        trace={trace}
                        onSelect={handleTraceSelect}
                        expanded={expandedTrace === trace.trace_id}
                        detail={traceDetails[trace.trace_id]}
                        loadingDetail={loadingDetail && expandedTrace === trace.trace_id}
                      />
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>

        </div>
      </main>
      <Footer />
    </Navbar>
  )
}
