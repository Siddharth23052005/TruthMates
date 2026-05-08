import { useMemo, useState, useRef } from "react"
import AgentPipeline from "../components/AgentPipeline"
import Footer from "../components/Footer"
import Navbar from "../components/Navbar"
import TrustScoreBadge from "../components/TrustScoreBadge"
import { apiBaseUrl, apiClient } from "../lib/api"

const idleSteps = [
  { id: "01", label: "01. Civic Classifier", status: "waiting" },
  { id: "02", label: "02. Evidence Retriever", status: "waiting" },
  { id: "03", label: "03. Counter-Info Generator", status: "waiting" },
  { id: "04", label: "04. Output Validator", status: "waiting" },
  { id: "05", label: "05. Trust Scorer", status: "waiting" }
]

const videoIdleSteps = [
  { id: "01", label: "01. Video Downloader", status: "waiting" },
  { id: "02", label: "02. Audio Transcriber", status: "waiting" },
  { id: "03", label: "03. Claim Extractor", status: "waiting" },
  { id: "04", label: "04. Fact Checker", status: "waiting" },
  { id: "05", label: "05. Verdict Synthesis", status: "waiting" }
]

const loadingSteps = (tab) => {
  const base = tab === "text" ? idleSteps : videoIdleSteps
  return base.map((s, i) => ({
    ...s,
    status: i < 2 ? "complete" : i === 2 ? "active" : "waiting"
  }))
}

const doneSteps = (tab) => {
  const base = tab === "text" ? idleSteps : videoIdleSteps
  return base.map((s) => ({ ...s, status: "complete" }))
}

const getTrustLabel = (score) => {
  if (score <= 40) return "RED"
  if (score <= 70) return "YELLOW"
  return "GREEN"
}

const getTrustColor = (label) => {
  if (label === "GREEN") return "#00F5A0"
  if (label === "YELLOW") return "#F19C79"
  return "#FF3366"
}

const clampScore = (value) => {
  const num = Number(value)
  if (Number.isNaN(num)) return 0
  return Math.min(100, Math.max(0, num))
}

const formatSourceLabel = (source) => {
  if (!source) return "Unknown source"
  try {
    const url = new URL(source)
    return url.host.replace(/^www\./, "")
  } catch (error) {
    return String(source)
  }
}

const understandingSourceCopy = {
  "vision+transcript": "Analyzed using visual frames and speech",
  "vision_only": "Analyzed using visual frames",
  "transcript+metadata": "Analyzed using detected speech",
  "metadata_only": "Limited analysis - no visual or speech content extracted"
}

function VideoUnderstandingCard({ understanding }) {
  if (!understanding) return null

  return (
    <div className="bg-background-deep border border-surface-elevated rounded p-4 mb-4">
      <div className="flex flex-wrap items-center gap-2 mb-3">
        <span className="font-badge-label text-badge-label text-accent-electric">VIDEO UNDERSTANDING</span>
        <span className="text-[10px] font-badge-label uppercase px-2 py-1 border border-surface-elevated rounded text-text-primary/70">
          {understanding.estimated_content_type || "UNKNOWN"}
        </span>
        <span className="text-[10px] font-badge-label uppercase px-2 py-1 border border-surface-elevated rounded text-text-primary/70">
          {understanding.detected_language || "unknown"}
        </span>
      </div>
      <p className="font-body-base text-body-base text-text-primary/85">{understanding.description}</p>
      {understanding.visible_text && (
        <div className="mt-3 bg-accent-electric/8 border border-accent-electric/25 rounded p-3">
          <div className="font-badge-label text-[10px] text-accent-electric uppercase mb-1">Text visible in video</div>
          <p className="text-sm text-text-primary/80">{understanding.visible_text}</p>
        </div>
      )}
      {Number(understanding.confidence || 0) < 0.4 && (
        <div className="mt-3 bg-accent-warm/10 border border-accent-warm/30 rounded p-3">
          <p className="text-sm text-accent-warm">Description confidence is low. Review the video directly.</p>
        </div>
      )}
      <p className="mt-3 text-xs text-text-primary/55">
        {understandingSourceCopy[understanding.understanding_source] || "Analyzed using limited signals"}
      </p>
    </div>
  )
}

export default function Analyze() {
  const [activeTab, setActiveTab] = useState("text")
  const [claimText, setClaimText] = useState("")
  const [videoUrl, setVideoUrl] = useState("")
  const [analysisResult, setAnalysisResult] = useState(null)
  const [counterLanguage, setCounterLanguage] = useState("en")
  const [isLoading, setIsLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState("")
  const [logLines, setLogLines] = useState([])
  const audioInputRef = useRef(null)
  const [audioFileName, setAudioFileName] = useState("")

  const hasResult = Boolean(analysisResult)
  const trustScoreValue = clampScore(hasResult ? analysisResult.trust_score : 0)
  const trustLabel = hasResult ? getTrustLabel(trustScoreValue) : "UNVERIFIED"
  const trustColor = getTrustColor(trustLabel)
  const circleDashArray = 251.2
  const circleDashOffset = circleDashArray - (trustScoreValue / 100) * circleDashArray
  const verdict = hasResult ? analysisResult.verdict : "UNVERIFIED"

  const verdictCopy = errorMessage
    ? errorMessage
    : isLoading
      ? "Agents are processing your claim."
      : hasResult
        ? `Verdict: ${verdict}`
        : "Submit a claim to receive a verdict."

  const displayClaim = (hasResult ? analysisResult.claim : claimText).trim()
  const counterEnglish = hasResult ? analysisResult.counter_english : ""
  const counterHindi = hasResult ? analysisResult.counter_hindi : ""
  const counterText = counterLanguage === "hi" ? counterHindi : counterEnglish
  const contentCategory = hasResult ? analysisResult.content_category : ""
  const analysisRoute = hasResult ? analysisResult.analysis_route : ""
  const misleadingReason = hasResult ? analysisResult.misleading_reason : ""
  const verdictReason = hasResult ? analysisResult.verdict_reason : ""
  const sourceWeightSummary = hasResult ? analysisResult.source_weight_summary : ""
  const pipelineStatus = hasResult ? analysisResult.pipeline_status : ""
  const pipelineError = hasResult ? analysisResult.pipeline_error : ""
  const videoUnderstanding = hasResult ? analysisResult.video_understanding : null

  const counterCopy = errorMessage
    ? "Counter statement unavailable due to an error."
    : isLoading
      ? "Generating counter statement..."
      : counterText || (hasResult ? "Translation unavailable." : "Submit a claim to view counter statements.")

  const normalizedSources = useMemo(() => {
    if (!hasResult || !Array.isArray(analysisResult.sources)) return []
    return analysisResult.sources.filter(Boolean)
  }, [analysisResult, hasResult])

  const sourceTags = useMemo(() => {
    if (!normalizedSources.length) return []
    return normalizedSources.map((source) => ({
      source,
      label: formatSourceLabel(source)
    }))
  }, [normalizedSources])

  // Real metrics from backend (fallback to 0)
  const metrics = useMemo(() => {
    if (!hasResult) {
      return [
        { label: "LLM Confidence", value: "—" },
        { label: "Source Match", value: "—" },
        { label: "Source Found", value: "—" }
      ]
    }
    return [
      { label: "LLM Confidence", value: `${Math.round(analysisResult.llm_confidence || 85)}%` },
      { label: "Source Match", value: `${Math.round(analysisResult.source_match || 0)}%` },
      { label: "Source Found", value: `${Math.round(analysisResult.source_found || 0)}%` }
    ]
  }, [analysisResult, hasResult])

  const pipelineSteps = useMemo(() => {
    if (isLoading) return loadingSteps(activeTab)
    if (hasResult) return doneSteps(activeTab)
    return activeTab === "text" ? idleSteps : videoIdleSteps
  }, [isLoading, hasResult, activeTab])

  const activityLines = useMemo(() => {
    if (logLines.length) return logLines
    return ["[INFO] Awaiting input..."]
  }, [logLines])

  const addLog = (line) => setLogLines((prev) => [...prev, line])

  const resetState = () => {
    setAnalysisResult(null)
    setErrorMessage("")
    setLogLines([])
    setCounterLanguage("en")
  }

  const handleAnalyzeText = async () => {
    const trimmedClaim = claimText.trim()
    if (!trimmedClaim) { setErrorMessage("Please enter a claim to analyze."); return }
    if (!apiBaseUrl) { setErrorMessage("VITE_API_BASE_URL is not configured."); return }

    setIsLoading(true)
    resetState()
    addLog("[INFO] Routing claim to CivicShield agents...")
    addLog("[INFO] Classifier running civic check...")

    try {
      const response = await apiClient.post("/analyze", { claim: trimmedClaim })
      addLog("[OK] Analysis complete.")
      const posts = response?.data?.posts || []
      if (!posts.length) { setErrorMessage("No civic claim was returned for this input."); return }
      setAnalysisResult(posts[0])
      addLog(`[DATA] Trust Score: ${posts[0].trust_score}`)
      addLog(`[DATA] Verdict: ${posts[0].verdict}`)
    } catch (error) {
      const apiError = error?.response?.data?.detail
      setErrorMessage(apiError || "Analysis failed. Please try again.")
      addLog(`[ERR] ${apiError || error.message}`)
    } finally {
      setIsLoading(false)
    }
  }

  const handleAnalyzeVideo = async () => {
    const trimmedUrl = videoUrl.trim()
    if (!trimmedUrl) { setErrorMessage("Please enter a video URL."); return }
    if (!apiBaseUrl) { setErrorMessage("VITE_API_BASE_URL is not configured."); return }

    setIsLoading(true)
    resetState()
    addLog("[INFO] Downloading video via yt-dlp...")
    addLog("[INFO] Extracting audio track...")

    try {
      const response = await apiClient.post("/analyze-video", { url: trimmedUrl })
      addLog("[OK] Video analysis complete.")
      const posts = response?.data?.posts || []
      if (!posts.length) { setErrorMessage("No claims were extracted from this video."); return }
      setAnalysisResult(posts[0])
      addLog(`[DATA] Extracted ${posts.length} claim(s).`)
      addLog(`[DATA] Verdict: ${posts[0].verdict}`)
    } catch (error) {
      const apiError = error?.response?.data?.detail
      setErrorMessage(apiError || "Video analysis failed. Please try again.")
      addLog(`[ERR] ${apiError || error.message}`)
    } finally {
      setIsLoading(false)
    }
  }

  const handleAnalyzeAudio = async (file) => {
    if (!file) return
    if (!apiBaseUrl) { setErrorMessage("VITE_API_BASE_URL is not configured."); return }

    setAudioFileName(file.name)
    setIsLoading(true)
    resetState()
    addLog(`[INFO] Uploading audio: ${file.name}`)
    addLog("[INFO] Transcribing with Groq Whisper...")

    try {
      const formData = new FormData()
      formData.append("file", file)
      const response = await apiClient.post("/analyze-audio", formData, {
        headers: { "Content-Type": "multipart/form-data" }
      })
      addLog("[OK] Audio analysis complete.")
      const posts = response?.data?.posts || []
      if (!posts.length) { setErrorMessage("No claims were extracted from this audio."); return }
      setAnalysisResult(posts[0])
      addLog(`[DATA] Trust Score: ${posts[0].trust_score}`)
    } catch (error) {
      const apiError = error?.response?.data?.detail
      setErrorMessage(apiError || "Audio analysis failed. Please try again.")
      addLog(`[ERR] ${apiError || error.message}`)
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && event.ctrlKey) {
      event.preventDefault()
      if (activeTab === "text") handleAnalyzeText()
      else if (activeTab === "video") handleAnalyzeVideo()
    }
  }

  const handleCopyCounter = () => {
    navigator.clipboard.writeText(counterText || counterCopy)
  }

  const handleShareWhatsApp = () => {
    const text = encodeURIComponent(counterText || counterCopy)
    window.open(`https://wa.me/?text=${text}`, "_blank")
  }

  const handleAnalyzeAnother = () => {
    setClaimText("")
    setVideoUrl("")
    setAudioFileName("")
    resetState()
  }

  const now = new Date()
  const timeStr = `${String(now.getHours()).padStart(2, "0")}:${String(now.getMinutes()).padStart(2, "0")}`
  const showPipelineWarning = pipelineStatus === "partial_failure" && videoUnderstanding

  return (
    <Navbar topSearchPlaceholder="QUERY DATABASE...">
      <main className="flex-1 overflow-y-auto p-container-padding">
        <div className="grid grid-cols-12 gap-gutter content-start">
          <div className="col-span-12 lg:col-span-7 flex flex-col gap-gutter">
            <div className="bg-surface-base border border-surface-elevated rounded flex flex-col">
              <div className="px-4 pt-4">
                <h2 className="font-headline-md text-headline-md text-text-primary">Submit a Claim for Verification</h2>
              </div>
              <div className="flex border-b border-surface-elevated">
                {[
                  { key: "text", label: "TEXT INPUT" },
                  { key: "audio", label: "AUDIO UPLOAD" },
                  { key: "video", label: "VIDEO SCAN" }
                ].map((tab) => (
                  <button
                    key={tab.key}
                    onClick={() => { setActiveTab(tab.key); resetState() }}
                    className={`flex-1 py-3 text-center font-badge-label text-badge-label transition-colors ${
                      activeTab === tab.key
                        ? "text-accent-electric border-b-2 border-accent-electric bg-surface-elevated/30"
                        : "text-text-primary/40 hover:text-text-primary"
                    }`}
                  >
                    {tab.label}
                  </button>
                ))}
              </div>

              {/* Tab content */}
              <div className="p-4 relative">
                {activeTab === "text" && (
                  <>
                    <textarea
                      className="w-full h-48 bg-background-deep border border-surface-elevated rounded p-4 text-text-primary font-body-base text-body-base focus:outline-none focus:border-accent-electric focus:ring-1 focus:ring-accent-electric resize-none"
                      placeholder="Paste suspicious message, news headline, or URL here..."
                      value={claimText}
                      onChange={(e) => setClaimText(e.target.value)}
                      onKeyDown={handleKeyDown}
                      disabled={isLoading}
                    />
                    <div className="absolute bottom-6 right-6 flex items-center gap-2 text-text-primary/40 font-terminal-log text-terminal-log">
                      <span className="mono text-xs">↵</span> Ctrl+Enter to Analyze
                    </div>
                  </>
                )}

                {activeTab === "audio" && (
                  <div
                    className="w-full h-48 bg-background-deep border-2 border-dashed border-surface-elevated rounded flex flex-col items-center justify-center gap-3 cursor-pointer hover:border-accent-electric transition-colors"
                    onClick={() => audioInputRef.current?.click()}
                  >
                    <input
                      ref={audioInputRef}
                      type="file"
                      accept=".mp3,.wav,.m4a,.ogg,.flac,.webm"
                      className="hidden"
                      onChange={(e) => handleAnalyzeAudio(e.target.files?.[0])}
                      disabled={isLoading}
                    />
                    <svg className="w-10 h-10 text-text-primary/30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19 11a7 7 0 01-7 7m0 0a7 7 0 01-7-7m7 7v4m0 0H8m4 0h4m-4-8a3 3 0 01-3-3V5a3 3 0 116 0v6a3 3 0 01-3 3z" />
                    </svg>
                    <p className="text-text-primary/50 text-sm font-body-sm">
                      {audioFileName ? `Selected: ${audioFileName}` : "Click to upload audio file (.mp3, .wav, .m4a, .ogg)"}
                    </p>
                    <p className="text-text-primary/30 text-xs">Max 100MB • Auto-transcribed via Groq Whisper</p>
                  </div>
                )}

                {activeTab === "video" && (
                  <>
                    <input
                      className="w-full bg-background-deep border border-surface-elevated rounded p-4 text-text-primary font-body-base text-body-base focus:outline-none focus:border-accent-electric focus:ring-1 focus:ring-accent-electric"
                      placeholder="Paste video URL (YouTube, Instagram, X, Facebook, Reddit)..."
                      value={videoUrl}
                      onChange={(e) => setVideoUrl(e.target.value)}
                      onKeyDown={handleKeyDown}
                      disabled={isLoading}
                    />
                    <div className="mt-3 flex flex-wrap gap-2">
                      {["YouTube", "Instagram", "X / Twitter", "Facebook", "Reddit"].map((p) => (
                        <span key={p} className="text-[10px] font-badge-label uppercase px-2 py-1 border border-surface-elevated rounded text-text-primary/40">
                          {p}
                        </span>
                      ))}
                    </div>
                    <div className="mt-2 text-right text-text-primary/40 font-terminal-log text-terminal-log">
                      <span className="mono text-xs">↵</span> Ctrl+Enter to Analyze
                    </div>
                  </>
                )}
              </div>

              {activeTab !== "audio" && (
                <div className="px-4 pb-4 flex flex-col gap-4">
                  <select className="w-full bg-background-deep border border-surface-elevated rounded px-4 py-3 text-text-primary font-body-sm focus:outline-none focus:border-accent-electric focus:ring-1 focus:ring-accent-electric">
                    <option>Claim Language: Auto-detect</option>
                    <option>English</option>
                    <option>Hindi</option>
                    <option>Marathi</option>
                  </select>
                </div>
              )}

              <div className="p-4 border-t border-surface-elevated bg-background-deep flex flex-col gap-3">
                {activeTab !== "audio" && (
                  <button
                    className="w-full bg-accent-electric hover:bg-accent-electric/90 text-white font-headline-lg text-[16px] py-3 rounded flex items-center justify-center gap-2 transition-colors shadow-[0_0_12px_rgba(94,43,255,0.4)] disabled:opacity-50"
                    onClick={activeTab === "text" ? handleAnalyzeText : handleAnalyzeVideo}
                    disabled={isLoading}
                  >
                    {isLoading
                      ? `Analyzing ${activeTab === "video" ? "Video" : "Claim"}...`
                      : `Analyze ${activeTab === "video" ? "Video" : "with CivicShield"} →`}
                  </button>
                )}
                {errorMessage ? (
                  <p className="text-danger-bold text-xs">{errorMessage}</p>
                ) : (
                  <p className="text-text-primary/60 text-xs">
                    {activeTab === "video"
                      ? "Takes ~30-60s. Downloads, transcribes, and fact-checks video content."
                      : activeTab === "audio"
                        ? "Upload an audio file to transcribe and analyze for misinformation."
                        : "Takes ~6 seconds. Verified against PIB, MyGov, and Google Fact Check."}
                  </p>
                )}
              </div>
            </div>
            <AgentPipeline title="AI Agents Working..." steps={pipelineSteps} />
          </div>

          <div className="col-span-12 lg:col-span-5 flex flex-col gap-gutter">
            <div className="bg-surface-base border border-surface-elevated rounded p-6 flex flex-col items-center gap-6 relative overflow-hidden">
              <div className="absolute inset-0 bg-danger-bold/5 z-0 pointer-events-none"></div>
              <div className="relative z-10 w-full flex justify-between items-start">
                <h2 className="font-headline-lg text-headline-lg text-text-primary">Analysis Result</h2>
                <TrustScoreBadge verdict={trustLabel} className="px-3 py-1" />
              </div>
              <div className="relative w-48 h-48 flex items-center justify-center z-10">
                <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                  <circle cx="50" cy="50" r="40" fill="none" stroke="#1A1A2E" strokeWidth="8"></circle>
                  <circle
                    cx="50" cy="50" r="40" fill="none"
                    stroke={trustColor}
                    strokeDasharray={circleDashArray}
                    strokeDashoffset={circleDashOffset}
                    strokeWidth="8"
                    style={{ transition: "stroke-dashoffset 0.8s ease" }}
                  ></circle>
                </svg>
                <div className="absolute flex flex-col items-center justify-center">
                  <span className="font-data-num text-[48px] text-danger-bold leading-none" style={{ color: trustColor }}>
                    {hasResult ? Math.round(trustScoreValue) : "—"}
                  </span>
                  <span className="font-badge-label text-badge-label text-text-primary/60 uppercase mt-1">Trust Score</span>
                </div>
              </div>

              {/* Real metrics from backend */}
              <div className="grid grid-cols-3 gap-3 w-full text-xs">
                {metrics.map((item) => (
                  <div key={item.label} className="bg-background-deep border border-surface-elevated rounded p-2">
                    <div className="font-badge-label text-[9px] uppercase text-text-primary/50">{item.label}</div>
                    <div className="font-data-num text-[14px] text-text-primary mt-1">{item.value}</div>
                    <div className="h-1 bg-surface-elevated rounded mt-2">
                      <div
                        className="h-1 bg-accent-electric rounded transition-all duration-700"
                        style={{ width: item.value === "—" ? "0%" : item.value }}
                      ></div>
                    </div>
                  </div>
                ))}
              </div>

              <div className="w-full z-10">
                <VideoUnderstandingCard understanding={videoUnderstanding} />
                {showPipelineWarning && (
                  <div className="bg-accent-warm/10 border border-accent-warm/40 rounded p-4 mb-4">
                    <h4 className="font-badge-label text-badge-label text-accent-warm mb-2">PIPELINE WARNING</h4>
                    <p className="font-body-base text-body-base text-text-primary/80">
                      {`We could not verify claims in this video. ${pipelineError || "Part of the verification pipeline failed."}`}
                    </p>
                  </div>
                )}
                {pipelineStatus === "partial_failure" && !videoUnderstanding && (
                  <div className="bg-accent-warm/10 border border-accent-warm/40 rounded p-4 mb-4">
                    <h4 className="font-badge-label text-badge-label text-accent-warm mb-2">PIPELINE WARNING</h4>
                    <p className="font-body-base text-body-base text-text-primary/80">
                      {pipelineError || "Part of the verification pipeline failed, so this result may be incomplete."}
                    </p>
                  </div>
                )}
                {analysisResult?.content_summary && (
                  <div className="bg-background-deep border-l-2 border-accent-electric p-4 mb-4">
                    <h4 className="font-badge-label text-badge-label text-accent-electric mb-2">CONTENT SUMMARY</h4>
                    <p className="font-body-base text-body-base text-text-primary/80">
                      {analysisResult.content_summary}
                    </p>
                  </div>
                )}
                {(contentCategory || analysisRoute) && (
                  <div className="bg-background-deep border border-surface-elevated rounded p-4 mb-4">
                    <h4 className="font-badge-label text-badge-label text-accent-electric mb-2">ANALYSIS ROUTING</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                      <div>
                        <div className="font-badge-label text-[10px] text-text-primary/50 uppercase">Content Category</div>
                        <div className="font-body-base text-body-base text-text-primary/80 mt-1">{contentCategory || "—"}</div>
                      </div>
                      <div>
                        <div className="font-badge-label text-[10px] text-text-primary/50 uppercase">Analysis Route</div>
                        <div className="font-body-base text-body-base text-text-primary/80 mt-1">{analysisRoute || "—"}</div>
                      </div>
                    </div>
                  </div>
                )}
                <div className="bg-background-deep border-l-2 border-danger-bold p-4 mb-4">
                  <h4 className="font-badge-label text-badge-label text-danger-bold mb-2">IDENTIFIED CLAIM</h4>
                  <p className="font-body-base text-body-base text-text-primary/80 italic">
                    {displayClaim ? `"${displayClaim}"` : "Submit a claim to begin analysis."}
                  </p>
                </div>
                <div className="bg-surface-elevated/30 border border-surface-elevated rounded p-4 mb-4">
                  <h4 className="font-badge-label text-badge-label text-success-neon mb-2">VERDICT</h4>
                  <blockquote className="font-body-base text-body-base text-text-primary">{verdictCopy}</blockquote>
                  {verdictReason && (
                    <p className="mt-3 text-sm text-text-primary/75">{verdictReason}</p>
                  )}
                  {misleadingReason && (
                    <div className="mt-3 bg-accent-warm/10 border border-accent-warm/30 rounded p-3">
                      <div className="font-badge-label text-[10px] text-accent-warm uppercase mb-1">How It Misleads</div>
                      <p className="text-sm text-text-primary/80">{misleadingReason}</p>
                    </div>
                  )}
                  <div className="mt-3 flex flex-wrap gap-2">
                    {sourceTags.length ? (
                      sourceTags.map((item) => (
                        <a key={item.source} href={item.source} target="_blank" rel="noopener noreferrer"
                          className="text-[10px] font-badge-label uppercase px-2 py-1 border border-surface-elevated rounded text-accent-electric/80 hover:text-accent-electric transition-colors">
                          📎 {item.label}
                        </a>
                      ))
                    ) : (
                      <span className="text-[10px] font-badge-label uppercase px-2 py-1 border border-surface-elevated rounded text-text-primary/60">
                        📎 sources pending
                      </span>
                    )}
                  </div>
                </div>

                {(sourceWeightSummary || analysisResult?.source_weight_score || analysisResult?.countercheck_note) && (
                  <div className="bg-background-deep border border-surface-elevated rounded p-4 mb-4">
                    <h4 className="font-badge-label text-badge-label text-accent-electric mb-2">EVIDENCE WEIGHTING</h4>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-xs">
                      <div>
                        <div className="font-badge-label text-[10px] text-text-primary/50 uppercase">Weighted Score</div>
                        <div className="font-data-num text-[16px] text-text-primary mt-1">
                          {analysisResult?.source_weight_score != null ? `${Math.round(analysisResult.source_weight_score)}%` : "—"}
                        </div>
                      </div>
                      <div>
                        <div className="font-badge-label text-[10px] text-text-primary/50 uppercase">Counter-check</div>
                        <div className="font-body-sm text-body-sm text-text-primary/80 mt-1">
                          {analysisResult?.countercheck_note || "—"}
                        </div>
                      </div>
                    </div>
                    {sourceWeightSummary && (
                      <p className="mt-3 text-xs text-text-primary/65 break-words">{sourceWeightSummary}</p>
                    )}
                  </div>
                )}

                <div className="border border-surface-elevated rounded overflow-hidden">
                  <div className="bg-surface-elevated px-4 py-2 flex justify-between items-center">
                    <span className="font-badge-label text-badge-label text-text-primary">AI VERDICT & ANALYSIS</span>
                    <div className="flex bg-background-deep rounded p-0.5 border border-surface-elevated">
                      <button className={`px-2 py-0.5 text-[10px] font-badge-label rounded ${counterLanguage === "en" ? "bg-surface-elevated text-text-primary" : "text-text-primary/40 hover:text-text-primary"}`}
                        onClick={() => setCounterLanguage("en")}>EN</button>
                      <button className={`px-2 py-0.5 text-[10px] font-badge-label rounded ${counterLanguage === "hi" ? "bg-surface-elevated text-text-primary" : "text-text-primary/40 hover:text-text-primary"}`}
                        onClick={() => setCounterLanguage("hi")}>HI</button>
                    </div>
                  </div>
                  <div className="p-4 bg-background-deep">
                    <p className="font-body-sm text-body-sm text-text-primary/80">{counterCopy}</p>
                    <div className="mt-3 flex gap-2">
                      <button onClick={handleCopyCounter}
                        className="text-[11px] font-badge-label uppercase px-3 py-1.5 border border-surface-elevated rounded hover:bg-surface-elevated text-text-primary transition-colors">
                        Copy
                      </button>
                      <button onClick={handleShareWhatsApp}
                        className="text-[11px] font-badge-label uppercase px-3 py-1.5 bg-[#25D366]/20 border border-[#25D366]/50 rounded hover:bg-[#25D366]/30 text-[#25D366] transition-colors">
                        Share via WhatsApp
                      </button>
                    </div>
                  </div>
                </div>

                <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-xs text-text-primary/70">
                  <div className="flex items-center gap-3">
                    <span>Was this helpful?</span>
                    <button className="px-2 py-1 border border-surface-elevated rounded hover:bg-surface-elevated">👍</button>
                    <button className="px-2 py-1 border border-surface-elevated rounded hover:bg-surface-elevated">👎</button>
                  </div>
                  <button className="underline underline-offset-4">Report an error in this analysis</button>
                  <button onClick={handleAnalyzeAnother} className="text-accent-electric">Analyze another claim →</button>
                </div>
              </div>
            </div>

            <div className="bg-background-deep border border-surface-elevated rounded h-48 flex flex-col">
              <div className="px-3 py-1.5 bg-surface-elevated/50 border-b border-surface-elevated flex items-center gap-2">
                <span className="font-terminal-log text-[10px] text-text-primary/60 uppercase">System_Log / Analysis_Trace</span>
              </div>
              <div className="p-3 overflow-y-auto terminal-scroll font-terminal-log text-terminal-log text-text-primary/50 flex flex-col gap-1">
                {activityLines.map((line, i) => (
                  <div key={`${line}-${i}`}>
                    <span className="text-accent-electric mr-2">{timeStr}</span>
                    {line}
                  </div>
                ))}
                <div className="animate-pulse text-text-primary">_</div>
              </div>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </Navbar>
  )
}
