import { useEffect, useState } from "react"
import { ExternalLink, AlertTriangle, Clock } from "lucide-react"
import { apiClient } from "../lib/api"
import Navbar from "../components/Navbar"
import Footer from "../components/Footer"

const POLL_MS = 30000

function formatTimeAgo(isoString) {
  if (!isoString) return "Unknown"
  const now = new Date()
  const past = new Date(isoString)
  const diffMs = now - past
  const diffMins = Math.round(diffMs / 60000)
  if (diffMins < 60) return `${diffMins}m ago`
  const diffHrs = Math.round(diffMins / 60)
  if (diffHrs < 24) return `${diffHrs}h ago`
  return `${Math.round(diffHrs / 24)}d ago`
}

export default function Trending() {
  const [claims, setClaims] = useState([])

  useEffect(() => {
    let mounted = true

    const loadClaims = async () => {
      try {
        const response = await apiClient.get("/api/trending-claims")
        if (!mounted) return
        setClaims(response?.data?.items || [])
      } catch (err) {
        console.error("Failed to load trending claims", err)
      }
    }

    loadClaims()
    const interval = setInterval(loadClaims, POLL_MS)
    return () => {
      mounted = false
      clearInterval(interval)
    }
  }, [])

  return (
    <Navbar>
      <main className="flex-1 bg-background-deep p-6">
        <div className="max-w-5xl mx-auto flex flex-col mt-4">
          <div className="text-center mb-10">
            <h1 className="text-4xl md:text-5xl font-black text-text-primary mb-3 tracking-tight font-hero-display flex items-center justify-center gap-3">
              <AlertTriangle className="h-10 w-10 text-primary" />
              Trending Claims
            </h1>
            <p className="text-on-surface-variant text-lg">
              Live feed of potentially misleading claims circulating in the news. Auto-refresh every 30s.
            </p>
          </div>

          <div className="grid grid-cols-1 gap-6 mb-12">
            {claims.map((claim) => {
              const verdictLower = (claim.verdict || "").toLowerCase()
              let verdictBadge = "bg-blue-500/20 text-blue-400 border-blue-500/30"
              if (verdictLower.includes("misleading")) {
                verdictBadge = "bg-amber-500/20 text-amber-400 border-amber-500/30"
              } else if (verdictLower.includes("false")) {
                verdictBadge = "bg-red-500/20 text-red-400 border-red-500/30"
              }

              return (
                <div key={claim.id} className="bg-surface-base border border-surface-elevated rounded-xl p-6 shadow-sm flex flex-col hover:border-primary/50 transition-colors">
                  <div className="flex flex-col sm:flex-row sm:justify-between sm:items-start gap-4 mb-4">
                    <h3 className="text-xl font-bold text-text-primary flex-1">{claim.claim}</h3>
                    <div className={`px-3 py-1 rounded-full text-xs font-bold border whitespace-nowrap ${verdictBadge}`}>
                      {claim.verdict}
                    </div>
                  </div>

                  <div className="mb-4">
                    <p className="text-sm text-on-surface-variant font-medium mb-1">Original Headline</p>
                    <p className="text-sm text-text-secondary italic">"{claim.headline}"</p>
                  </div>
                  
                  {claim.reasoning && (
                    <div className="mb-4 text-sm text-on-surface-variant bg-surface-elevated/50 p-3 rounded-lg">
                      {claim.reasoning}
                    </div>
                  )}

                  <div className="flex items-center gap-4 text-xs text-on-surface-variant mb-6">
                    <span className="flex items-center gap-1 font-semibold text-primary">
                      {claim.source}
                    </span>
                    <span className="flex items-center gap-1">
                      <Clock className="w-3 h-3" />
                      {formatTimeAgo(claim.timestamp)}
                    </span>
                    {claim.url && (
                      <a href={claim.url} target="_blank" rel="noreferrer" className="flex items-center gap-1 hover:text-primary transition-colors ml-auto">
                        View Article <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>

                  {/* Score Progress Bar */}
                  <div className="mt-auto">
                    <div className="flex justify-between items-center mb-2">
                      <span className="text-xs font-semibold text-on-surface-variant">Misleading Score</span>
                      <span className="text-xs font-bold text-text-primary">{claim.score}/100</span>
                    </div>
                    <div className="h-2 w-full bg-surface-elevated rounded-full overflow-hidden">
                      <div 
                        className={`h-full rounded-full ${claim.score >= 80 ? 'bg-red-500' : claim.score >= 60 ? 'bg-amber-500' : 'bg-blue-500'}`}
                        style={{ width: `${Math.max(0, Math.min(100, claim.score))}%` }}
                      />
                    </div>
                  </div>
                </div>
              )
            })}
            
            {claims.length === 0 && (
              <div className="col-span-full bg-surface-base border border-surface-elevated rounded-xl p-6 text-on-surface-variant text-center">
                No trending claims available yet.
              </div>
            )}
          </div>
        </div>
      </main>
      <Footer />
    </Navbar>
  )
}
