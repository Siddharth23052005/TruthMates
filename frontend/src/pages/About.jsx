import Navbar from "../components/Navbar"
import Footer from "../components/Footer"
import { Heart, ShieldCheck, Users, CheckCircle2 } from "lucide-react"
import { useEffect, useMemo, useState } from "react"
import { apiClient } from "../lib/api"

const POLL_MS = 30000

const formatTimeAgo = (isoTime) => {
  if (!isoTime) return "just now"
  const timestamp = new Date(isoTime).getTime()
  if (Number.isNaN(timestamp)) return "just now"
  const seconds = Math.max(0, Math.floor((Date.now() - timestamp) / 1000))
  if (seconds < 60) return `${seconds}s ago`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  const days = Math.floor(hours / 24)
  return `${days}d ago`
}

export default function About() {
  const [liveFeed, setLiveFeed] = useState([])

  useEffect(() => {
    let mounted = true

    const loadFeed = async () => {
      try {
        const response = await apiClient.get("/api/trending")
        if (!mounted) return
        setLiveFeed(response?.data?.items || [])
      } catch {
        if (!mounted) return
        setLiveFeed([])
      }
    }

    loadFeed()
    const interval = setInterval(loadFeed, POLL_MS)
    return () => {
      mounted = false
      clearInterval(interval)
    }
  }, [])

  const liveCards = useMemo(() => liveFeed.slice(0, 8), [liveFeed])

  return (
    <Navbar>
      <main className="flex-1 overflow-y-auto p-6 md:p-12 relative z-10">
        <div className="max-w-4xl mx-auto flex flex-col items-center gap-10 mt-4 pb-12">
          
          <div className="text-center flex flex-col items-center">
            <div className="inline-flex items-center justify-center gap-2 px-4 py-1.5 rounded-full border border-danger-bold/30 bg-danger-bold/5 mb-6 text-danger-bold text-sm font-medium">
              <Heart className="h-4 w-4" />
              Our Purpose
            </div>
            <h1 className="text-5xl md:text-6xl font-black text-text-primary tracking-tight font-hero-display">
              Our Mission
            </h1>
          </div>

          <div className="w-full bg-surface-base border border-surface-elevated rounded-2xl p-8 md:p-12 shadow-sm text-center">
            <div className="mb-8 space-y-3">
              <h2 className="text-xl md:text-2xl font-bold text-danger-bold mb-2">Misinformation is not harmless.</h2>
              <p className="text-xl md:text-2xl text-text-primary font-medium mb-4">It creates fear, panic, and wrong actions.</p>
              <p className="text-lg text-on-surface-variant">During emergencies, even a single false message can cause chaos.</p>
            </div>
            
            <div className="pt-8 mt-4 border-t border-surface-elevated/50">
              <p className="text-lg text-text-primary">
                TruthMates exists to slow the spread of misinformation and help people <span className="text-danger-bold font-bold">think before they share</span>.
              </p>
            </div>
          </div>

          <div className="w-full mt-10">
            <h2 className="text-2xl font-bold text-text-primary text-center mb-8">When people verify before sharing:</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              
              <div className="bg-surface-base border border-surface-elevated rounded-2xl p-6 shadow-sm flex flex-col items-center text-center hover:border-[#10B981]/50 transition-colors">
                <div className="p-4 rounded-2xl bg-[#10B981]/10 mb-5 border border-[#10B981]/20">
                  <ShieldCheck className="h-8 w-8 text-[#10B981]" />
                </div>
                <h3 className="text-lg font-bold text-text-primary mb-3">Peace of mind</h3>
                <p className="text-sm text-on-surface-variant leading-relaxed">Less anxiety from fake news meant to cause emotional panic.</p>
              </div>

              <div className="bg-surface-base border border-surface-elevated rounded-2xl p-6 shadow-sm flex flex-col items-center text-center hover:border-primary/50 transition-colors">
                <div className="p-4 rounded-2xl bg-primary/10 mb-5 border border-primary/20">
                  <Users className="h-8 w-8 text-primary" />
                </div>
                <h3 className="text-lg font-bold text-text-primary mb-3">Trust Returns</h3>
                <p className="text-sm text-on-surface-variant leading-relaxed">Communities start relying on real facts instead of rumors.</p>
              </div>

              <div className="bg-surface-base border border-surface-elevated rounded-2xl p-6 shadow-sm flex flex-col items-center text-center hover:border-danger-bold/50 transition-colors">
                <div className="p-4 rounded-2xl bg-danger-bold/10 mb-5 border border-danger-bold/20">
                  <CheckCircle2 className="h-8 w-8 text-danger-bold" />
                </div>
                <h3 className="text-lg font-bold text-text-primary mb-3">Lives are Saved</h3>
                <p className="text-sm text-on-surface-variant leading-relaxed">During crisis, exact information leads to better decisions.</p>
              </div>

            </div>
          </div>

          <div className="w-full mt-10 bg-surface-base border border-surface-elevated rounded-2xl p-10 md:p-14 shadow-sm text-center">
            <h2 className="text-2xl md:text-3xl font-bold text-text-primary leading-relaxed">
              "In the right moment, the right information<br />
              <span className="text-danger-bold">can save lives.</span>"
            </h2>
          </div>

          <div className="w-full mt-10">
            <div className="flex items-center justify-between mb-6">
              <h2 className="text-2xl font-bold text-text-primary">Live Misinformation Dashboard</h2>
              <span className="text-xs text-on-surface-variant">refreshes every 30s</span>
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {liveCards.map((item) => (
                <div key={item.id} className="bg-surface-base border border-surface-elevated rounded-xl p-5 shadow-sm">
                  <div className="flex items-start justify-between gap-3">
                    <h3 className="text-base font-semibold text-text-primary">{item.topic}</h3>
                    <span className="px-2 py-1 rounded text-xs font-semibold border border-surface-elevated text-on-surface-variant">
                      {item.verdict}
                    </span>
                  </div>
                  <p className="text-xs text-on-surface-variant mt-2">{item.source || "Unknown source"}</p>
                  <div className="mt-4">
                    <div className="flex justify-between text-xs mb-1">
                      <span className="text-on-surface-variant">Trust score</span>
                      <span className="text-primary font-semibold">{item.trust_score ?? 0}%</span>
                    </div>
                    <div className="h-2 w-full bg-surface-elevated rounded-full overflow-hidden">
                      <div
                        className="h-full bg-primary"
                        style={{ width: `${Math.max(0, Math.min(100, Number(item.trust_score) || 0))}%` }}
                      />
                    </div>
                  </div>
                  <p className="text-xs text-on-surface-variant mt-3">{formatTimeAgo(item.timestamp)}</p>
                </div>
              ))}
              {!liveCards.length && (
                <div className="col-span-full bg-surface-base border border-surface-elevated rounded-xl p-5 text-on-surface-variant text-sm">
                  No live items yet. The monitoring scheduler will populate this feed automatically.
                </div>
              )}
            </div>
          </div>

        </div>
      </main>
      <Footer />
    </Navbar>
  )
}
