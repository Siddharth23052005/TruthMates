import { useEffect, useMemo, useState } from "react"
import Footer from "../components/Footer"
import Navbar from "../components/Navbar"
import TrustScoreBadge from "../components/TrustScoreBadge"
import { adminApiClient, apiBaseUrl } from "../lib/api"

const formatTime = (timestamp) => {
  if (!timestamp) return "--:--:--"
  const parsed = new Date(timestamp)
  if (Number.isNaN(parsed.getTime())) return "--:--:--"
  return parsed.toLocaleTimeString("en-GB", {
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false
  })
}

const formatSnippet = (value, fallback) => {
  const text = String(value || "").replace(/\s+/g, " ").trim()
  if (!text) return fallback
  if (text.length <= 80) return text
  return `${text.slice(0, 77)}...`
}

const emptySummary = {
  status: "unknown",
  total_validated: 0,
  verdict_counts: {},
  monitor_status_counts: {},
  average_trust_score: 0,
  timeline: []
}

export default function Dashboard() {
  const [monitorLogs, setMonitorLogs] = useState([])
  const [monitorStatus, setMonitorStatus] = useState({ status: "unknown", agents: {} })
  const [monitorSummary, setMonitorSummary] = useState(emptySummary)
  const [errorMessage, setErrorMessage] = useState("")
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    let isMounted = true

    const loadMonitorData = async () => {
      if (!apiBaseUrl) {
        if (isMounted) {
          setErrorMessage("VITE_API_BASE_URL is not configured.")
          setIsLoading(false)
        }
        return
      }

      try {
        const [logsResponse, statusResponse, summaryResponse] = await Promise.all([
          adminApiClient.get("/monitor/logs"),
          adminApiClient.get("/monitor/status"),
          adminApiClient.get("/monitor/summary")
        ])

        if (!isMounted) return

        setMonitorLogs(logsResponse?.data?.logs || [])
        setMonitorStatus(statusResponse?.data || { status: "unknown", agents: {} })
        setMonitorSummary(summaryResponse?.data || emptySummary)
        setErrorMessage("")
      } catch (error) {
        if (!isMounted) return
        const apiError = error?.response?.data?.detail
        setErrorMessage(apiError || "Unable to load monitor data.")
      } finally {
        if (isMounted) {
          setIsLoading(false)
        }
      }
    }

    loadMonitorData()
    const intervalId = setInterval(loadMonitorData, 8000)

    return () => {
      isMounted = false
      clearInterval(intervalId)
    }
  }, [])

  const liveStream = useMemo(() => {
    return monitorLogs.map((log, index) => ({
      id: log.id || `${log.agent_name || "log"}-${index}`,
      claim: formatSnippet(log.input || log.output || log.agent_name, "Monitor update"),
      verdict: log.status || "UNKNOWN",
      time: formatTime(log.timestamp),
      trust: "--"
    }))
  }, [monitorLogs])

  const statusText = (monitorStatus?.status || "unknown").toUpperCase()
  const statusLabel = errorMessage ? "PIPELINE ERROR" : `PIPELINE HEALTH: ${statusText}`
  const tableMessage = errorMessage
    ? errorMessage
    : isLoading
      ? "Loading monitor logs..."
      : "No monitor logs yet."

  const totalClaimsAnalyzed = monitorSummary?.total_validated || 0
  const averageTrust = Math.round(monitorSummary?.average_trust_score || 0)
  const verdictCounts = monitorSummary?.verdict_counts || {}
  const activePriorityThreats = (verdictCounts.REFUTED || 0) + (verdictCounts.MISLEADING || 0)
  const supportedPct = totalClaimsAnalyzed ? Math.round(((verdictCounts.SUPPORTED || 0) / totalClaimsAnalyzed) * 100) : 0
  const misleadingPct = totalClaimsAnalyzed ? Math.round(((verdictCounts.MISLEADING || 0) / totalClaimsAnalyzed) * 100) : 0
  const refutedPct = totalClaimsAnalyzed ? Math.round(((verdictCounts.REFUTED || 0) / totalClaimsAnalyzed) * 100) : 0
  const timelineBars = (monitorSummary?.timeline || []).slice(-6)
  const maxTimelineCount = Math.max(...timelineBars.map((item) => item.count), 1)

  return (
    <Navbar topSearchPlaceholder="QUERY DATABASE...">
      <main className="flex-1 overflow-y-auto p-container-padding">
        <div className="max-w-7xl mx-auto space-y-6">
          <div className="flex justify-between items-end border-b border-surface-elevated pb-4">
            <div>
              <h1 className="font-headline-lg text-headline-lg text-text-primary tracking-tight">System Status</h1>
              <p className="font-body-base text-body-base text-on-surface-variant mt-1">
                Real-time verification metrics and active threat analysis.
              </p>
            </div>
            <div className="flex items-center gap-2 text-success-neon font-badge-label text-badge-label bg-success-neon/10 border border-success-neon/20 px-3 py-1 rounded">
              <span className="w-1.5 h-1.5 bg-success-neon rounded-full animate-pulse"></span>
              {statusLabel}
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-gutter">
            <div className="bg-surface-base border border-surface-elevated p-4 flex flex-col relative overflow-hidden group">
              <div className="absolute inset-0 bg-gradient-to-br from-surface-elevated/20 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
              <div className="flex justify-between items-start mb-2 z-10">
                <span className="font-badge-label text-badge-label text-on-surface-variant uppercase">
                  Total Claims Analyzed
                </span>
                <span className="text-outline text-[16px]">O</span>
              </div>
              <div className="font-data-num text-[32px] font-bold text-text-primary z-10 mt-2">{totalClaimsAnalyzed}</div>
              <div className="mt-2 text-success-neon font-terminal-log text-terminal-log flex items-center gap-1 z-10">
                <span>{timelineBars[timelineBars.length - 1]?.count || 0} recent</span>
                <span className="text-on-surface-variant ml-1">validated outputs</span>
              </div>
            </div>

            <div className="bg-surface-base border border-surface-elevated p-4 flex flex-col relative overflow-hidden group">
              <div className="absolute inset-0 bg-gradient-to-br from-success-neon/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
              <div className="flex justify-between items-start mb-2 z-10">
                <span className="font-badge-label text-badge-label text-on-surface-variant uppercase">
                  Average Trust Score
                </span>
                <span className="text-success-neon/60 text-[16px]">+</span>
              </div>
              <div className="flex items-end gap-3 z-10 mt-2">
                <div className="font-data-num text-[32px] font-bold text-success-neon">{averageTrust}%</div>
                <div className="font-terminal-log text-terminal-log text-on-surface-variant mb-1">live average</div>
              </div>
              <div className="h-1 w-full bg-surface-elevated mt-4 rounded-full overflow-hidden z-10">
                <div className="h-full bg-success-neon relative" style={{ width: `${averageTrust}%` }}>
                  <div className="absolute right-0 top-0 bottom-0 w-8 bg-gradient-to-r from-transparent to-white/50"></div>
                </div>
              </div>
            </div>

            <div className="bg-surface-base border border-surface-elevated p-4 flex flex-col relative overflow-hidden group">
              <div className="absolute inset-0 bg-gradient-to-br from-danger-bold/5 to-transparent opacity-0 group-hover:opacity-100 transition-opacity"></div>
              <div className="flex justify-between items-start mb-2 z-10">
                <span className="font-badge-label text-badge-label text-on-surface-variant uppercase">
                  Active Priority Threats
                </span>
                <span className="text-danger-bold/60 text-[16px]">!</span>
              </div>
              <div className="font-data-num text-[32px] font-bold text-danger-bold z-10 mt-2">{activePriorityThreats}</div>
              <div className="mt-2 text-danger-bold font-terminal-log text-terminal-log flex items-center gap-1 z-10">
                <span>{verdictCounts.MISLEADING || 0} misleading</span>
                <span className="text-on-surface-variant ml-1">{verdictCounts.REFUTED || 0} refuted</span>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-gutter h-[500px]">
            <div className="lg:col-span-8 bg-surface-base border border-surface-elevated flex flex-col h-full">
              <div className="p-4 border-b border-surface-elevated flex justify-between items-center bg-surface-base">
                <h2 className="font-headline-md text-[16px] text-text-primary uppercase flex items-center gap-2">
                  Live Verdict Stream
                </h2>
                <button className="font-badge-label text-badge-label text-accent-electric border border-surface-elevated px-2 py-1 hover:border-accent-electric transition-colors">
                  Filter
                </button>
              </div>
              <div className="flex-1 overflow-auto">
                <table className="w-full text-left border-collapse">
                  <thead className="sticky top-0 bg-surface-base z-10">
                    <tr className="font-badge-label text-badge-label text-on-surface-variant uppercase border-b border-surface-elevated">
                      <th className="py-3 px-4 w-1/2">Claim Snippet</th>
                      <th className="py-3 px-4 w-1/6">Verdict</th>
                      <th className="py-3 px-4 w-1/6">Time (UTC)</th>
                      <th className="py-3 px-4 w-1/6 text-right">Trust Score</th>
                    </tr>
                  </thead>
                  <tbody className="font-terminal-log text-terminal-log divide-y divide-surface-elevated">
                    {liveStream.length ? (
                      liveStream.map((row) => (
                        <tr key={row.id} className="hover:bg-surface-elevated transition-colors group cursor-pointer">
                          <td className="py-3 px-4 text-text-primary truncate max-w-[200px]">{row.claim}</td>
                          <td className="py-3 px-4">
                            <TrustScoreBadge verdict={row.verdict} />
                          </td>
                          <td className="py-3 px-4 text-on-surface-variant">{row.time}</td>
                          <td className="py-3 px-4 text-right font-data-num text-[14px] text-text-primary">
                            {row.trust}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td className="py-3 px-4 text-on-surface-variant" colSpan={4}>
                          {tableMessage}
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="lg:col-span-4 flex flex-col gap-gutter h-full">
              <div className="bg-surface-base border border-surface-elevated p-4 flex-1 flex flex-col">
                <h3 className="font-badge-label text-badge-label text-on-surface-variant uppercase mb-4">
                  Score Distribution (Recent)
                </h3>
                <div className="flex-1 flex items-end gap-2 px-2 pb-6 relative">
                  <div className="w-full flex justify-between items-end h-full gap-1">
                    {timelineBars.length ? (
                      timelineBars.map((item) => (
                        <div
                          key={item.date}
                          className="w-1/6 bg-success-neon/70 border-t border-success-neon"
                          style={{ height: `${Math.max(12, Math.round((item.count / maxTimelineCount) * 100))}%` }}
                          title={`${item.date}: ${item.count}`}
                        ></div>
                      ))
                    ) : (
                      <div className="w-full h-[20%] bg-surface-elevated"></div>
                    )}
                  </div>
                  <div className="absolute bottom-0 left-0 right-0 flex justify-between px-2 text-[9px] font-terminal-log text-on-surface-variant">
                    <span>{timelineBars[0]?.date || "--"}</span>
                    <span>{timelineBars[Math.floor(timelineBars.length / 2)]?.date || "--"}</span>
                    <span>{timelineBars[timelineBars.length - 1]?.date || "--"}</span>
                  </div>
                </div>
              </div>

              <div className="bg-surface-base border border-surface-elevated p-4 flex-1 flex flex-col">
                <h3 className="font-badge-label text-badge-label text-on-surface-variant uppercase mb-4">Verdict Matrix</h3>
                <div className="flex-1 flex items-center justify-center relative">
                  <div
                    className="w-32 h-32 rounded-full border-8 border-surface-elevated relative flex items-center justify-center"
                    style={{
                      background: `conic-gradient(#00F5A0 0% ${supportedPct}%, #F19C79 ${supportedPct}% ${supportedPct + misleadingPct}%, #FF3366 ${supportedPct + misleadingPct}% 100%)`
                    }}
                  >
                    <div className="w-24 h-24 bg-surface-base rounded-full absolute flex items-center justify-center flex-col">
                      <span className="font-data-num text-[18px] text-text-primary">{totalClaimsAnalyzed}</span>
                      <span className="font-badge-label text-[8px] text-on-surface-variant">CLAIMS</span>
                    </div>
                  </div>
                </div>
                <div className="mt-4 flex flex-col gap-2 font-terminal-log text-[10px]">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 bg-success-neon"></span> SUPPORTED
                    </div>
                    <div className="font-data-num">{supportedPct}%</div>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 bg-accent-warm"></span> MISLEADING
                    </div>
                    <div className="font-data-num">{misleadingPct}%</div>
                  </div>
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2">
                      <span className="w-2 h-2 bg-danger-bold"></span> REFUTED
                    </div>
                    <div className="font-data-num">{refutedPct}%</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </Navbar>
  )
}
