import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import Footer from "../components/Footer"
import Navbar from "../components/Navbar"
import { adminApiClient } from "../lib/api"
import {
  Radar, Search, RefreshCw, CheckCircle2, XCircle, AlertTriangle,
  ExternalLink, ChevronDown, ChevronUp, Brain, ShieldCheck,
  MessageSquareWarning, Pencil, X, Activity, ThumbsUp, MessageCircle,
  Repeat2, Eye, ArrowUpRight, BookOpen,
} from "lucide-react"

/* ── Platform config ─────────────────────────────────────────────────────── */

const PLATFORMS = {
  twitter:   { label: "𝕏", name: "X (Twitter)", color: "#1DA1F2", bg: "#1DA1F215", accent: "#0D8BD9" },
  youtube:   { label: "▶", name: "YouTube",      color: "#FF0000", bg: "#FF000012", accent: "#CC0000" },
  reddit:    { label: "⬡", name: "Reddit",       color: "#FF4500", bg: "#FF450012", accent: "#CC3700" },
  instagram: { label: "◎", name: "Instagram",    color: "#E1306C", bg: "#E1306C12", accent: "#B8204F" },
}

const VERDICTS = {
  REFUTED:   { color: "#EF4444", bg: "#EF444415", label: "❌ FALSE",       icon: XCircle },
  MISLEADING:{ color: "#F59E0B", bg: "#F59E0B15", label: "⚠️ MISLEADING", icon: AlertTriangle },
  SUPPORTED: { color: "#10B981", bg: "#10B98115", label: "✅ ACCURATE",    icon: CheckCircle2 },
  UNVERIFIED:{ color: "#8B5CF6", bg: "#8B5CF615", label: "❓ UNVERIFIED",  icon: Eye },
}

const getVerdict = (v) => VERDICTS[v] || VERDICTS.UNVERIFIED
const getPlatform = (p) => PLATFORMS[p] || PLATFORMS.twitter

/* ── Avatar from initials ────────────────────────────────────────────────── */

function Avatar({ name, platform }) {
  const p = getPlatform(platform)
  const initials = (name || "?").replace(/^[@u\/]+/, "").slice(0, 2).toUpperCase()
  return (
    <div
      className="w-11 h-11 rounded-full flex items-center justify-center text-sm font-bold flex-shrink-0"
      style={{ backgroundColor: p.bg, color: p.color, border: `2px solid ${p.color}30` }}
    >
      {initials}
    </div>
  )
}

/* ── Stat Card ───────────────────────────────────────────────────────────── */

function StatCard({ label, value, icon: Icon, color }) {
  return (
    <div className="bg-surface-base border border-surface-elevated rounded-xl p-4 flex items-center gap-4 hover:border-primary/20 transition-all">
      <div className="w-10 h-10 rounded-lg flex items-center justify-center" style={{ backgroundColor: `${color}15` }}>
        <Icon className="w-5 h-5" style={{ color }} />
      </div>
      <div>
        <div className="font-data-num text-2xl text-text-primary">{value}</div>
        <div className="text-xs text-on-surface-variant uppercase tracking-wider">{label}</div>
      </div>
    </div>
  )
}

/* ── Filter Tabs ─────────────────────────────────────────────────────────── */

function Filters({ active, onChange }) {
  const tabs = [
    { key: "all",        label: "All" },
    { key: "REFUTED",    label: "🔴 False" },
    { key: "MISLEADING", label: "🟡 Misleading" },
    { key: "SUPPORTED",  label: "🟢 Accurate" },
    { key: "UNVERIFIED", label: "🟣 Unverified" },
  ]
  return (
    <div className="flex flex-wrap gap-2">
      {tabs.map(t => (
        <button
          key={t.key}
          onClick={() => onChange(t.key)}
          className={`px-4 py-2 rounded-lg text-sm font-medium transition-all border ${
            active === t.key
              ? "bg-primary/15 text-primary border-primary/30"
              : "text-on-surface-variant border-surface-elevated hover:border-on-surface-variant/20"
          }`}
        >
          {t.label}
        </button>
      ))}
    </div>
  )
}

/* ── Social Post Card (looks like a real tweet/post) ─────────────────────── */

function PostCard({ entry, onApprove, onReject }) {
  const [showAnalysis, setShowAnalysis] = useState(false)
  const [editReply, setEditReply] = useState(false)
  const [replyText, setReplyText] = useState(entry.suggested_reply || "")
  const [note, setNote] = useState("")

  const { post, analysis, status } = entry
  const platform = getPlatform(post.platform)
  const verdict = getVerdict(analysis?.verdict)
  const VIcon = verdict.icon
  const isMisleading = analysis?.is_misleading
  const isReviewed = status === "approved" || status === "rejected"

  const timeAgo = useMemo(() => {
    const d = post.posted_at || post.scraped_at
    if (!d) return ""
    const ms = Date.now() - new Date(d).getTime()
    const m = Math.floor(ms / 60000)
    if (m < 60) return `${m}m`
    const h = Math.floor(m / 60)
    if (h < 24) return `${h}h`
    return `${Math.floor(h / 24)}d`
  }, [post])

  return (
    <div
      className="rounded-2xl border overflow-hidden transition-all duration-300"
      style={{
        backgroundColor: "#0a0a0a",
        borderColor: isMisleading ? `${verdict.color}40` : "#1a1a2e",
        opacity: isReviewed ? 0.75 : 1,
      }}
    >
      {/* ── The Post (looks like an actual social media embed) ─────────── */}
      <div className="p-5">
        {/* Header: avatar + name + handle + platform + time */}
        <div className="flex items-start gap-3 mb-3">
          <Avatar name={post.author_name || post.author_handle} platform={post.platform} />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-semibold text-text-primary text-sm truncate">
                {post.author_name || post.author_handle}
              </span>
              <span className="text-on-surface-variant text-xs truncate">
                {post.author_handle}
              </span>
              <span className="text-on-surface-variant text-xs">·</span>
              <span className="text-on-surface-variant text-xs">{timeAgo}</span>
            </div>
            <div className="flex items-center gap-1.5 mt-0.5">
              <span className="text-xs font-medium" style={{ color: platform.color }}>
                {platform.label} {platform.name}
              </span>
              {post.engagement?.subreddit && (
                <span className="text-xs text-on-surface-variant">· {post.engagement.subreddit}</span>
              )}
            </div>
          </div>

          {/* Verdict badge */}
          <div
            className="px-2.5 py-1 rounded-lg text-xs font-bold flex items-center gap-1 flex-shrink-0"
            style={{ backgroundColor: verdict.bg, color: verdict.color }}
          >
            <VIcon className="w-3 h-3" />
            {verdict.label}
          </div>
        </div>

        {/* Post content */}
        <div className="text-text-primary text-[15px] leading-relaxed mb-3 whitespace-pre-line">
          {post.content}
        </div>

        {/* Engagement bar */}
        <div className="flex items-center gap-5 text-on-surface-variant text-xs">
          {post.engagement?.likes && (
            <span className="flex items-center gap-1"><ThumbsUp className="w-3.5 h-3.5" />{post.engagement.likes}</span>
          )}
          {post.engagement?.retweets && (
            <span className="flex items-center gap-1"><Repeat2 className="w-3.5 h-3.5" />{post.engagement.retweets}</span>
          )}
          {post.engagement?.comments && (
            <span className="flex items-center gap-1"><MessageCircle className="w-3.5 h-3.5" />{post.engagement.comments}</span>
          )}
          {post.engagement?.upvotes && (
            <span className="flex items-center gap-1"><ThumbsUp className="w-3.5 h-3.5" />⬆ {post.engagement.upvotes}</span>
          )}
          {post.engagement?.views && (
            <span className="flex items-center gap-1"><Eye className="w-3.5 h-3.5" />{post.engagement.views}</span>
          )}
          {post.post_url && (
            <a href={post.post_url} target="_blank" rel="noopener noreferrer"
              className="flex items-center gap-1 text-primary hover:underline ml-auto">
              <ExternalLink className="w-3 h-3" />View post
            </a>
          )}
        </div>
      </div>

      {/* ── Fact Check Section (below the post) ──────────────────────────── */}
      {analysis && (
        <div className="border-t" style={{ borderColor: `${verdict.color}25` }}>
          {/* Quick summary — always visible */}
          <div className="px-5 py-4" style={{ backgroundColor: `${verdict.color}08` }}>
            {/* What this post claims */}
            <div className="mb-3">
              <h4 className="text-xs font-bold text-on-surface-variant uppercase tracking-wider mb-1 flex items-center gap-1.5">
                <MessageSquareWarning className="w-3.5 h-3.5" />
                What This Post Claims
              </h4>
              <p className="text-sm text-text-primary leading-relaxed">
                {post.content.length > 200 ? post.content.slice(0, 200) + "..." : post.content}
              </p>
            </div>

            {/* Why it's wrong / Verification result */}
            <div className="mb-3">
              <h4 className="text-xs font-bold uppercase tracking-wider mb-1 flex items-center gap-1.5"
                style={{ color: verdict.color }}>
                <ShieldCheck className="w-3.5 h-3.5" />
                {isMisleading ? "Why This Is Not Correct" : "Verification Result"}
              </h4>
              <p className="text-sm text-text-primary leading-relaxed">
                {analysis.correct_information}
              </p>
            </div>

            {/* Trust score bar */}
            <div className="flex items-center gap-3">
              <span className="text-xs text-on-surface-variant">Trust Score</span>
              <div className="flex-1 h-1.5 bg-surface-elevated rounded-full overflow-hidden">
                <div className="h-full rounded-full transition-all duration-700"
                  style={{ width: `${Math.min(100, Math.max(0, analysis.trust_score))}%`, backgroundColor: verdict.color }} />
              </div>
              <span className="text-xs font-data-num" style={{ color: verdict.color }}>
                {Math.round(analysis.trust_score)}/100
              </span>
            </div>
          </div>

          {/* Expand for full analysis */}
          <button
            onClick={() => setShowAnalysis(!showAnalysis)}
            className="w-full px-5 py-2.5 flex items-center justify-between text-xs text-primary hover:bg-surface-elevated/30 transition-colors border-t border-surface-elevated"
          >
            <span className="flex items-center gap-1.5">
              <Brain className="w-3.5 h-3.5" />
              {showAnalysis ? "Hide Detailed Analysis" : "View Full Human-Style Analysis"}
            </span>
            {showAnalysis ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </button>

          {showAnalysis && (
            <div className="px-5 pb-5 pt-2 space-y-3 animate-fade-up">
              {/* Critical thinking */}
              <div className="bg-surface-dim rounded-lg p-4">
                <h4 className="flex items-center gap-2 text-xs font-bold text-primary uppercase tracking-wider mb-2">
                  <Brain className="w-3.5 h-3.5" />
                  🧠 How a Critical Thinker Would See This
                </h4>
                <p className="text-sm text-on-surface-variant leading-relaxed whitespace-pre-line">
                  {analysis.critical_thinking}
                </p>
              </div>

              {/* Evidence */}
              <div className="bg-surface-dim rounded-lg p-4">
                <h4 className="flex items-center gap-2 text-xs font-bold text-accent-warm uppercase tracking-wider mb-2">
                  <BookOpen className="w-3.5 h-3.5" />
                  📊 What the Evidence Says
                </h4>
                <p className="text-sm text-on-surface-variant leading-relaxed whitespace-pre-line">
                  {analysis.evidence_summary}
                </p>
              </div>

              {/* Sources */}
              {analysis.sources?.length > 0 && (
                <div className="bg-surface-dim rounded-lg p-4">
                  <h4 className="text-xs font-bold text-on-surface-variant uppercase tracking-wider mb-2">📎 Sources</h4>
                  {analysis.sources.map((s, i) => (
                    <a key={i} href={s} target="_blank" rel="noopener noreferrer"
                      className="flex items-center gap-1.5 text-xs text-primary hover:underline truncate mb-1">
                      <ArrowUpRight className="w-3 h-3 flex-shrink-0" />{s}
                    </a>
                  ))}
                </div>
              )}

              {/* Suggested reply */}
              {isMisleading && entry.suggested_reply && (
                <div className="bg-surface-dim rounded-lg p-4">
                  <div className="flex items-center justify-between mb-2">
                    <h4 className="text-xs font-bold text-on-surface-variant uppercase tracking-wider">💬 Suggested Reply</h4>
                    <button onClick={() => setEditReply(!editReply)} className="text-xs text-primary flex items-center gap-1">
                      <Pencil className="w-3 h-3" />{editReply ? "Cancel" : "Edit"}
                    </button>
                  </div>
                  {editReply ? (
                    <textarea className="w-full bg-surface-base border border-surface-elevated rounded-lg p-3 text-sm text-text-primary resize-none min-h-[80px] outline-none focus:border-primary"
                      value={replyText} onChange={e => setReplyText(e.target.value)} />
                  ) : (
                    <p className="text-sm text-text-primary leading-relaxed">{replyText || entry.suggested_reply}</p>
                  )}
                </div>
              )}

              {/* Metrics */}
              <div className="grid grid-cols-2 gap-3">
                <div className="bg-surface-dim rounded-lg p-3 text-center">
                  <div className="text-xs text-on-surface-variant uppercase mb-1">AI Confidence</div>
                  <div className="font-data-num text-lg text-text-primary">{Math.round(analysis.confidence)}%</div>
                </div>
                <div className="bg-surface-dim rounded-lg p-3 text-center">
                  <div className="text-xs text-on-surface-variant uppercase mb-1">Trust Score</div>
                  <div className="font-data-num text-lg" style={{ color: verdict.color }}>{Math.round(analysis.trust_score)}</div>
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Moderator Actions ────────────────────────────────────────────── */}
      {!isReviewed && isMisleading && (
        <div className="px-5 py-3 flex items-center gap-3 border-t border-surface-elevated">
          <input type="text" placeholder="Moderator note..." value={note} onChange={e => setNote(e.target.value)}
            className="flex-1 bg-surface-dim border border-surface-elevated rounded-lg px-3 py-2 text-xs text-text-primary outline-none focus:border-primary" />
          <button onClick={() => onApprove(entry.entry_id, note, replyText)}
            className="px-4 py-2 rounded-lg text-xs font-bold flex items-center gap-1.5 hover:scale-105 transition-transform"
            style={{ backgroundColor: "#10B98115", color: "#10B981", border: "1px solid #10B98130" }}>
            <CheckCircle2 className="w-3.5 h-3.5" />Approve
          </button>
          <button onClick={() => onReject(entry.entry_id, note)}
            className="px-4 py-2 rounded-lg text-xs font-bold flex items-center gap-1.5 hover:scale-105 transition-transform"
            style={{ backgroundColor: "#EF444415", color: "#EF4444", border: "1px solid #EF444430" }}>
            <XCircle className="w-3.5 h-3.5" />Reject
          </button>
        </div>
      )}

      {isReviewed && (
        <div className="px-5 py-3 border-t border-surface-elevated flex items-center gap-2">
          <span className="px-3 py-1 rounded-lg text-xs font-bold uppercase"
            style={{
              backgroundColor: status === "approved" ? "#10B98115" : "#EF444415",
              color: status === "approved" ? "#10B981" : "#EF4444",
            }}>
            {status === "approved" ? "✅ Approved" : "❌ Rejected"}
          </span>
          {entry.moderator_note && <span className="text-xs text-on-surface-variant italic">— {entry.moderator_note}</span>}
        </div>
      )}
    </div>
  )
}

/* ── Main Page ────────────────────────────────────────────────────────────── */

export default function SocialMonitor() {
  const [entries, setEntries] = useState([])
  const [stats, setStats] = useState(null)
  const [isLoading, setIsLoading] = useState(true)
  const [isCrawling, setIsCrawling] = useState(false)
  const [crawlProgress, setCrawlProgress] = useState(null)
  const [activeFilter, setActiveFilter] = useState("all")
  const [searchQuery, setSearchQuery] = useState("")
  const [error, setError] = useState("")

  const fetchEntries = useCallback(async () => {
    try {
      const [eRes, sRes] = await Promise.all([
        adminApiClient.get("/social/entries", { params: { limit: 100 } }),
        adminApiClient.get("/social/stats"),
      ])
      setEntries(eRes.data?.entries || [])
      setStats(sRes.data)
    } catch (err) {
      if (err?.response?.status === 404 || err?.response?.status === 401) {
        setEntries([]); setStats(null)
      }
    }
  }, [])

  useEffect(() => { setIsLoading(true); fetchEntries().finally(() => setIsLoading(false)) }, [fetchEntries])

  // Live polling during crawl
  useEffect(() => {
    if (!isCrawling) return
    const id = setInterval(async () => {
      try {
        const { data } = await adminApiClient.get("/social/crawl-status")
        setCrawlProgress(data)
        await fetchEntries()
        if (!data.is_running) { setIsCrawling(false); setCrawlProgress(null) }
      } catch { /* continue */ }
    }, 3000)
    return () => clearInterval(id)
  }, [isCrawling, fetchEntries])

  const handleCrawl = async () => {
    setIsCrawling(true)
    setCrawlProgress({ is_running: true, current_post: "Starting scan...", analyzed: 0, total_scraped: 0, flagged: 0 })
    setError("")
    try {
      await adminApiClient.post("/social/crawl", null, {
        params: { keywords: ["india government scam", "modi fake news", "BJP misleading", "aadhaar data leak", "UPI fraud"], max_posts: 50 },
      })
    } catch (err) {
      setError("Crawl failed: " + (err?.response?.data?.detail || err.message))
      setIsCrawling(false); setCrawlProgress(null)
    }
  }

  const handleAction = async (entryId, action, noteVal, replyVal) => {
    try {
      await adminApiClient.post(`/social/entries/${entryId}/review`, {
        action, moderator_note: noteVal || null, edited_reply: replyVal || null,
      })
      await fetchEntries()
    } catch { setError(`Failed to ${action} entry.`) }
  }

  const filtered = useMemo(() => {
    let r = entries
    if (activeFilter !== "all") r = r.filter(e => e.analysis?.verdict === activeFilter)
    if (searchQuery.trim()) {
      const q = searchQuery.toLowerCase()
      r = r.filter(e => e.post.content.toLowerCase().includes(q) || (e.analysis?.correct_information || "").toLowerCase().includes(q))
    }
    return r
  }, [entries, activeFilter, searchQuery])

  return (
    <Navbar>
      <main className="flex-1 overflow-y-auto bg-background-deep p-6">
        <div className="max-w-4xl mx-auto flex flex-col gap-6">

          {/* Header */}
          <div className="flex flex-col md:flex-row md:items-end justify-between gap-4 mt-6">
            <div>
              <div className="flex items-center gap-3 mb-2">
                <div className="w-10 h-10 rounded-xl bg-primary/15 flex items-center justify-center">
                  <Radar className="w-5 h-5 text-primary" />
                </div>
                <h1 className="text-3xl md:text-4xl font-black text-text-primary tracking-tight font-hero-display">
                  Social Monitor
                </h1>
              </div>
              <p className="text-on-surface-variant text-sm">
                Scanning Indian political misinformation across 𝕏, YouTube, Reddit & Instagram.
                <br />
                <span className="text-xs text-on-surface-variant/60">Posts verified via TruthMates pipeline · Human-moderated before any action</span>
              </p>
            </div>
            <button onClick={handleCrawl} disabled={isCrawling}
              className="px-6 py-3 rounded-xl font-bold text-sm flex items-center gap-2 transition-all hover:scale-105 disabled:opacity-60 disabled:cursor-not-allowed whitespace-nowrap"
              style={{ backgroundColor: isCrawling ? "#1A1A2E" : "#5E2BFF", color: "#fff", border: "1px solid #5E2BFF40" }}>
              <RefreshCw className={`w-4 h-4 ${isCrawling ? "animate-spin" : ""}`} />
              {isCrawling ? "Scanning..." : "Scan Now (50 Posts)"}
            </button>
          </div>

          {/* Live progress */}
          {isCrawling && crawlProgress && (
            <div className="rounded-xl px-5 py-4 flex flex-col gap-2"
              style={{ background: "linear-gradient(135deg, #5E2BFF14, #8B5CF60A)", border: "1px solid #5E2BFF30" }}>
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <div className="w-2 h-2 rounded-full bg-primary animate-pulse" />
                  <span className="text-sm font-semibold text-primary">Live Scanning</span>
                </div>
                <div className="flex gap-4 text-xs text-on-surface-variant">
                  <span>Analyzed: <b className="text-text-primary">{crawlProgress.analyzed}</b></span>
                  <span>Flagged: <b className="text-red-400">{crawlProgress.flagged}</b></span>
                </div>
              </div>
              <p className="text-xs text-on-surface-variant truncate">{crawlProgress.current_post}</p>
              {crawlProgress.total_scraped > 0 && (
                <div className="w-full h-1 bg-surface-elevated rounded-full overflow-hidden">
                  <div className="h-full rounded-full transition-all duration-500"
                    style={{ width: `${(crawlProgress.analyzed / crawlProgress.total_scraped) * 100}%`, background: "linear-gradient(90deg, #5E2BFF, #8B5CF6)" }} />
                </div>
              )}
            </div>
          )}

          {error && (
            <div className="bg-red-500/10 border border-red-500/30 rounded-xl px-4 py-3 text-sm text-red-400 flex items-center gap-2">
              <AlertTriangle className="w-4 h-4" />{error}
              <button onClick={() => setError("")} className="ml-auto"><X className="w-4 h-4" /></button>
            </div>
          )}

          {/* Stats */}
          {stats && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <StatCard label="Total Scanned" value={stats.total_scraped} icon={Radar} color="#c9beff" />
              <StatCard label="Misleading" value={stats.total_misleading} icon={AlertTriangle} color="#EF4444" />
              <StatCard label="Accurate" value={stats.total_accurate} icon={CheckCircle2} color="#10B981" />
              <StatCard label="Pending Review" value={stats.pending_review} icon={Activity} color="#F59E0B" />
            </div>
          )}

          {/* Filters + search */}
          <div className="flex flex-col md:flex-row gap-4 items-start md:items-center">
            <Filters active={activeFilter} onChange={setActiveFilter} />
            <div className="flex-1 relative md:max-w-xs">
              <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant" />
              <input type="text" placeholder="Search posts..." value={searchQuery} onChange={e => setSearchQuery(e.target.value)}
                className="w-full bg-surface-base border border-surface-elevated rounded-lg pl-9 pr-3 py-2 text-sm text-text-primary outline-none focus:border-primary" />
            </div>
          </div>

          {/* Posts */}
          {isLoading ? (
            <div className="flex flex-col items-center py-20 gap-4">
              <RefreshCw className="w-8 h-8 text-primary animate-spin" />
              <p className="text-on-surface-variant text-sm">Loading...</p>
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center py-20 gap-4 text-center">
              <div className="w-16 h-16 rounded-2xl bg-surface-elevated flex items-center justify-center">
                <Radar className="w-8 h-8 text-on-surface-variant" />
              </div>
              <h3 className="text-lg font-semibold text-text-primary">No posts found</h3>
              <p className="text-sm text-on-surface-variant max-w-md">
                {entries.length === 0 ? 'Click "Scan Now" to start scanning Indian political posts for misinformation.' : "No posts match your filters."}
              </p>
            </div>
          ) : (
            <div className="flex flex-col gap-5">
              <p className="text-xs text-on-surface-variant">
                {filtered.length} posts {isCrawling && "· scanning live..."}
              </p>
              {filtered.map(entry => (
                <PostCard
                  key={entry.entry_id}
                  entry={entry}
                  onApprove={(id, n, r) => handleAction(id, "approved", n, r)}
                  onReject={(id, n) => handleAction(id, "rejected", n)}
                />
              ))}
            </div>
          )}
        </div>
      </main>
      <Footer />
    </Navbar>
  )
}
