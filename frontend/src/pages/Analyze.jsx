import { useMemo, useState, useRef } from "react"
import AgentPipeline from "../components/AgentPipeline"
import Footer from "../components/Footer"
import Navbar from "../components/Navbar"
import TrustScoreBadge from "../components/TrustScoreBadge"
import { apiBaseUrl, apiClient } from "../lib/api"
import { Search, Mic, ExternalLink, FileText, BookOpen, Globe, Shield, Database } from "lucide-react"

const idleSteps = [
  { id: "01", label: "01. Civic Classifier", status: "waiting" },
  { id: "02", label: "02. Evidence Retriever", status: "waiting" },
  { id: "03", label: "03. Counter-Info", status: "waiting" },
  { id: "04", label: "04. Output Validator", status: "waiting" }
]

const loadingSteps = () => {
  return idleSteps.map((s, i) => ({
    ...s,
    status: i < 2 ? "complete" : i === 2 ? "active" : "waiting"
  }))
}

const doneSteps = () => {
  return idleSteps.map((s) => ({ ...s, status: "complete" }))
}

const getTrustLabel = (score) => {
  if (score <= 40) return "FALSE"
  if (score <= 70) return "UNVERIFIED"
  return "TRUE"
}

const getTrustColor = (label) => {
  if (label === "TRUE") return "#10B981"
  if (label === "UNVERIFIED") return "#F59E0B"
  return "#EF4444"
}

const clampScore = (value) => {
  const num = Number(value)
  if (Number.isNaN(num)) return 0
  return Math.min(100, Math.max(0, num))
}

export default function Analyze() {
  const [claimText, setClaimText] = useState("")
  const [analysisResult, setAnalysisResult] = useState(null)
  const [isLoading, setIsLoading] = useState(false)
  const [errorMessage, setErrorMessage] = useState("")

  const hasResult = Boolean(analysisResult)
  const trustScoreValue = clampScore(hasResult ? analysisResult.trust_score : 0)
  const trustLabel = hasResult ? getTrustLabel(trustScoreValue) : "UNVERIFIED"

  const metrics = useMemo(() => {
    if (!hasResult) {
      return [
        { label: "LLM Confidence", value: "—" },
        { label: "Source Match", value: "—" },
        { label: "Sources Found", value: "—" }
      ]
    }
    return [
      { label: "LLM Confidence", value: `${Math.round(analysisResult.llm_confidence || 85)}%` },
      { label: "Source Match", value: `${Math.round(analysisResult.source_match || 0)}%` },
      { label: "Sources Found", value: `${Math.round(analysisResult.source_found || 0)}%` }
    ]
  }, [analysisResult, hasResult])

  const pipelineSteps = useMemo(() => {
    if (isLoading) return loadingSteps()
    if (hasResult) return doneSteps()
    return idleSteps
  }, [isLoading, hasResult])

  const handleAnalyzeText = async () => {
    const trimmedClaim = claimText.trim()
    if (!trimmedClaim) { setErrorMessage("Please enter a claim to analyze."); return }
    if (!apiBaseUrl) { setErrorMessage("VITE_API_BASE_URL is not configured."); return }

    setIsLoading(true)
    setAnalysisResult(null)
    setErrorMessage("")

    try {
      // Detect if input is a video URL
      const videoUrlPattern = /^https?:\/\/.*(youtube\.com\/watch|youtu\.be\/|youtube\.com\/shorts|vimeo\.com\/|dailymotion\.com\/video|\.mp4|\.webm|\.mov)/i
      const isVideoUrl = videoUrlPattern.test(trimmedClaim)

      let response
      if (isVideoUrl) {
        response = await apiClient.post("/analyze-video", { url: trimmedClaim })
      } else {
        response = await apiClient.post("/analyze", { claim: trimmedClaim })
      }
      const posts = response?.data?.posts || []
      if (!posts.length) { setErrorMessage("No claim was returned for this input."); return }
      setAnalysisResult(posts[0])
    } catch (error) {
      const apiError = error?.response?.data?.detail
      setErrorMessage(apiError || "Analysis failed. Please try again.")
    } finally {
      setIsLoading(false)
    }
  }

  const handleKeyDown = (event) => {
    if (event.key === "Enter" && event.ctrlKey) {
      event.preventDefault()
      handleAnalyzeText()
    }
  }

  const setExample = (text) => {
    setClaimText(text)
  }

  return (
    <Navbar>
      <main className="flex-1 overflow-y-auto bg-background-deep p-6">
        <div className="max-w-3xl mx-auto flex flex-col gap-8">
          
          <div className="flex flex-col items-center mt-10">
            <h1 className="text-4xl md:text-5xl font-black text-text-primary mb-3 tracking-tight font-hero-display text-center">Check a News Claim</h1>
            <p className="text-on-surface-variant text-base md:text-lg mb-8 text-center">Put any news or viral message below to understand its current status.</p>
            
            <div className="w-full bg-surface-base border border-surface-elevated rounded-xl shadow-sm p-4 flex items-start focus-within:border-primary focus-within:ring-1 focus-within:ring-primary transition-all">
               <Search className="h-5 w-5 text-on-surface-variant mr-3 mt-1" />
               <textarea 
                  className="flex-1 bg-transparent resize-none outline-none text-text-primary placeholder:text-on-surface-variant/50 min-h-[100px]" 
                  placeholder="Enter a news headline, message, or paste a YouTube video link..." 
                  value={claimText}
                  onChange={(e) => setClaimText(e.target.value)}
                  onKeyDown={handleKeyDown}
               />
               <Mic className="h-5 w-5 text-on-surface-variant ml-3 mt-1 cursor-pointer hover:text-primary transition-colors" />
            </div>
            
            <div className="flex justify-between w-full mt-2 mb-6 text-xs text-on-surface-variant">
              <span>{errorMessage && <span className="text-danger-bold">{errorMessage}</span>}</span>
              <span>{claimText.length} / 2000</span>
            </div>
            
            <button 
              className="w-full bg-primary hover:bg-primary-fixed text-white font-bold py-4 rounded-xl transition-colors shadow-md text-lg disabled:opacity-70 disabled:cursor-not-allowed"
              onClick={handleAnalyzeText}
              disabled={isLoading}
            >
               {isLoading ? "Analyzing..." : "Analyze Claim"}
            </button>
            <p className="text-xs text-on-surface-variant mt-4 text-center">
               Verified against PIB, MyGov, and Google Fact Check.
            </p>

            <div className="mt-10 text-sm text-on-surface-variant text-center w-full">
               <p className="mb-4">Try an example:</p>
               <div className="flex flex-wrap gap-3 justify-center">
                  <button onClick={() => setExample("5G towers cause cancer")} className="px-4 py-2 rounded-full border border-surface-elevated hover:bg-surface-elevated transition-colors text-xs text-text-primary">5G towers cause cancer</button>
                  <button onClick={() => setExample("Onion juice cures dengue fever")} className="px-4 py-2 rounded-full border border-surface-elevated hover:bg-surface-elevated transition-colors text-xs text-text-primary">Onion juice cures dengue fever</button>
                  <button onClick={() => setExample("India's GDP grew 8.2% in 2024")} className="px-4 py-2 rounded-full border border-surface-elevated hover:bg-surface-elevated transition-colors text-xs text-text-primary">India's GDP grew 8.2% in 2024</button>
               </div>
            </div>
          </div>

          {(isLoading || hasResult) && (
            <div className="w-full mt-8 animate-fade-up">
              <h2 className="font-headline-lg text-2xl text-text-primary mb-6">Analysis Results</h2>
              
              <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
                <div className="md:col-span-2 flex flex-col gap-6">
                  
                  <div className="bg-surface-base border border-surface-elevated rounded-xl p-6 shadow-sm">
                    <div className="flex justify-between items-start mb-6">
                      <h3 className="font-badge-label text-text-primary/60 uppercase text-sm">Verdict</h3>
                      <div className="px-3 py-1 rounded border font-bold text-sm" style={{ borderColor: getTrustColor(trustLabel), color: getTrustColor(trustLabel) }}>
                        {isLoading ? "EVALUATING..." : trustLabel}
                      </div>
                    </div>
                    
                    <div className="mb-6">
                      <h4 className="text-sm font-semibold text-text-primary mb-2">Claim Analyzed</h4>
                      <p className="text-on-surface-variant italic border-l-4 border-surface-elevated pl-3 py-1">
                        {hasResult ? analysisResult.claim : claimText}
                      </p>
                    </div>

                    {isLoading ? (
                      <div>
                        <h4 className="text-sm font-semibold text-text-primary mb-2">Analysis Details</h4>
                        <p className="text-text-primary leading-relaxed">Generating verdict...</p>
                      </div>
                    ) : hasResult ? (
                      <div className="flex flex-col gap-5">
                        <div>
                          <h4 className="text-sm font-semibold text-text-primary mb-1">Content Description</h4>
                          <p className="text-text-primary leading-relaxed text-sm">
                            {analysisResult.content_summary || analysisResult.video_title || (analysisResult.input_type === 'video' ? "Video content analyzed." : "Text claim analyzed.")}
                          </p>
                        </div>
                        <div>
                          <h4 className="text-sm font-semibold text-text-primary mb-1">Misleading Check</h4>
                          <p className="text-text-primary leading-relaxed text-sm">
                            {analysisResult.verdict === "MISLEADING" ? (
                              <span><span className="font-bold text-warning-bold">⚠️ Yes, it is misleading:</span> {analysisResult.misleading_reason || analysisResult.verdict_reason || analysisResult.counter_english}</span>
                            ) : analysisResult.verdict === "REFUTED" ? (
                              <span><span className="font-bold text-danger-bold">❌ False:</span> {analysisResult.verdict_reason || analysisResult.counter_english}</span>
                            ) : analysisResult.verdict === "SUPPORTED" ? (
                              <span><span className="font-bold text-success-bold">✅ No, it is not misleading:</span> {analysisResult.verdict_reason || "The content accurately reflects verified facts."}</span>
                            ) : analysisResult.verdict === "SATIRE" ? (
                              <span><span className="font-bold text-primary">🎭 Satire:</span> This is parody and not meant to be taken as a factual claim.</span>
                            ) : analysisResult.verdict === "OUT_OF_SCOPE" ? (
                              <span><span className="font-bold text-on-surface-variant">⏭️ Out of Scope:</span> Not a civic or political claim.</span>
                            ) : (
                              <span><span className="font-bold text-warning-bold">❓ Unverified:</span> {analysisResult.counter_english}</span>
                            )}
                          </p>
                        </div>
                      </div>
                    ) : (
                      <div>
                        <h4 className="text-sm font-semibold text-text-primary mb-2">Analysis Details</h4>
                        <p className="text-text-primary leading-relaxed">Detailed analysis not available.</p>
                      </div>
                    )}
                  </div>

                  <div className="bg-surface-base border border-surface-elevated rounded-xl p-6 shadow-sm">
                    <h3 className="font-badge-label text-text-primary/60 uppercase text-sm mb-4">Scores</h3>
                    <div className="grid grid-cols-3 gap-4">
                      {metrics.map((item) => (
                        <div key={item.label} className="bg-background-deep border border-surface-elevated rounded-lg p-3">
                          <div className="text-xs uppercase text-on-surface-variant mb-1">{item.label}</div>
                          <div className="font-data-num text-lg text-text-primary">{item.value}</div>
                        </div>
                      ))}
                    </div>
                  </div>

                  {/* Detailed Explanation Section */}
                  {hasResult && analysisResult.detailed_explanation && (
                    <div className="bg-surface-base border border-surface-elevated rounded-xl p-6 shadow-sm">
                      <div className="flex items-center gap-2 mb-4">
                        <FileText className="h-4 w-4 text-primary" />
                        <h3 className="font-badge-label text-text-primary/60 uppercase text-sm">Detailed Explanation</h3>
                      </div>
                      <div className="space-y-3">
                        {analysisResult.detailed_explanation.split("\n").map((line, idx) => {
                          if (!line.trim()) return null
                          // Section headers (e.g. "Finding:", "Evidence Found:", "Conclusion:")
                          const isHeader = /^(Claim Analyzed:|Finding:|Why it may be misleading:|Evidence Found:|Evidence:|Source Analysis:|Conclusion:)/i.test(line.trim())
                          const isBullet = line.trim().startsWith("\u2022") || line.trim().startsWith("-")
                          if (isHeader) {
                            const [label, ...rest] = line.split(":")
                            const content = rest.join(":")
                            return (
                              <div key={idx} className="mt-2">
                                <span className="text-xs font-bold uppercase tracking-wider text-primary/80">{label}</span>
                                {content && <p className="text-sm text-text-primary leading-relaxed mt-1">{content.trim()}</p>}
                              </div>
                            )
                          }
                          if (isBullet) {
                            return (
                              <div key={idx} className="flex items-start gap-2 pl-2">
                                <span className="text-primary mt-0.5 text-xs">●</span>
                                <p className="text-sm text-on-surface-variant leading-relaxed flex-1">{line.trim().replace(/^[\u2022\-]\s*/, "")}</p>
                              </div>
                            )
                          }
                          return <p key={idx} className="text-sm text-text-primary leading-relaxed">{line}</p>
                        })}
                      </div>
                    </div>
                  )}

                  {/* Source References Section */}
                  {hasResult && analysisResult.source_references && analysisResult.source_references.length > 0 && (
                    <div className="bg-surface-base border border-surface-elevated rounded-xl p-6 shadow-sm">
                      <div className="flex items-center gap-2 mb-4">
                        <BookOpen className="h-4 w-4 text-primary" />
                        <h3 className="font-badge-label text-text-primary/60 uppercase text-sm">Related Sources & References</h3>
                      </div>
                      <div className="space-y-3">
                        {analysisResult.source_references.map((ref, idx) => {
                          const typeConfig = {
                            pinecone: { icon: Database, label: "Government DB", color: "text-emerald-400", bg: "bg-emerald-400/10", border: "border-emerald-400/20" },
                            google_fact_check: { icon: Shield, label: "Fact Check", color: "text-blue-400", bg: "bg-blue-400/10", border: "border-blue-400/20" },
                            official: { icon: Shield, label: "Official", color: "text-amber-400", bg: "bg-amber-400/10", border: "border-amber-400/20" },
                            web: { icon: Globe, label: "Web", color: "text-slate-400", bg: "bg-slate-400/10", border: "border-slate-400/20" },
                          }
                          const config = typeConfig[ref.source_type] || typeConfig.web
                          const IconComponent = config.icon
                          return (
                            <a
                              key={idx}
                              href={ref.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="group flex items-start gap-3 p-3 rounded-lg border border-surface-elevated hover:border-primary/30 hover:bg-primary/5 transition-all duration-200"
                            >
                              <div className={`flex-shrink-0 p-1.5 rounded-md ${config.bg} border ${config.border}`}>
                                <IconComponent className={`h-3.5 w-3.5 ${config.color}`} />
                              </div>
                              <div className="flex-1 min-w-0">
                                <p className="text-sm text-text-primary group-hover:text-primary transition-colors line-clamp-2 leading-snug">
                                  {ref.title}
                                </p>
                                <div className="flex items-center gap-2 mt-1.5">
                                  <span className={`text-[10px] uppercase font-bold px-1.5 py-0.5 rounded ${config.bg} ${config.color}`}>
                                    {config.label}
                                  </span>
                                  {ref.similarity != null && (
                                    <span className="text-[10px] text-on-surface-variant">
                                      {Math.round(ref.similarity * 100)}% match
                                    </span>
                                  )}
                                  <span className="text-[10px] text-on-surface-variant truncate max-w-[200px]">
                                    {ref.url.replace(/^https?:\/\//, "").split("/")[0]}
                                  </span>
                                </div>
                              </div>
                              <ExternalLink className="h-3.5 w-3.5 text-on-surface-variant group-hover:text-primary transition-colors flex-shrink-0 mt-0.5" />
                            </a>
                          )
                        })}
                      </div>
                    </div>
                  )}

                </div>

                <div className="md:col-span-1">
                  <div className="sticky top-20">
                    <AgentPipeline title="Live AI Agents Progress" steps={pipelineSteps} />
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </main>
      <Footer />
    </Navbar>
  )
}
