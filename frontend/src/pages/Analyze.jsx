import AgentPipeline from "../components/AgentPipeline"
import Footer from "../components/Footer"
import Navbar from "../components/Navbar"
import TrustScoreBadge from "../components/TrustScoreBadge"

const pipelineSteps = [
  { id: "01", label: "01. Source Scraper", status: "complete" },
  { id: "02", label: "02. Entity Extractor", status: "complete" },
  { id: "03", label: "03. Sentiment Classifier", status: "complete" },
  { id: "04", label: "04. Claim Deconstructor", status: "complete" },
  { id: "05", label: "05. Cross-Reference Engine", status: "active" },
  { id: "06", label: "06. Image Forgery Detector", status: "waiting" },
  { id: "07", label: "07. Network Propagation Analyzer", status: "waiting" },
  { id: "08", label: "08. Legal Precedent Checker", status: "waiting" },
  { id: "09", label: "09. Generative AI Probability", status: "waiting" },
  { id: "10", label: "10. Verdict Synthesis", status: "waiting" }
]

const logLines = [
  "[INFO] Initiating ingestion protocol...",
  "[INFO] Source text normalized. Length: 245 chars.",
  "[WARN] High velocity pattern detected in phrasing.",
  "[DATA] Entity Extractor found: 'Central Bank', 'Currency'.",
  "[OK] API connection established to RBI Gov portal.",
  "[INFO] Querying recent circulars (T-48h)...",
  "[ERR] Null response. Pattern match failed against official DB.",
  "[INFO] Running historical rumor signature comparison...",
  "[MATCH] Signature match (98%) with Incident ID #2016-11-R04.",
  "[INFO] Compiling counter-narrative vectors..."
]

export default function Analyze() {
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
                <button className="flex-1 py-3 text-center font-badge-label text-badge-label text-accent-electric border-b-2 border-accent-electric bg-surface-elevated/30">
                  TEXT INPUT
                </button>
                <button className="flex-1 py-3 text-center font-badge-label text-badge-label text-text-primary/40 hover:text-text-primary transition-colors">
                  AUDIO UPLOAD
                </button>
                <button className="flex-1 py-3 text-center font-badge-label text-badge-label text-text-primary/40 hover:text-text-primary transition-colors">
                  VIDEO SCAN
                </button>
              </div>
              <div className="p-4 relative">
                <textarea
                  className="w-full h-48 bg-background-deep border border-surface-elevated rounded p-4 text-text-primary font-body-base text-body-base focus:outline-none focus:border-accent-electric focus:ring-1 focus:ring-accent-electric resize-none"
                  placeholder="Paste suspicious message, news headline, or URL here..."
                ></textarea>
                <div className="absolute bottom-6 right-6 flex items-center gap-2 text-text-primary/40 font-terminal-log text-terminal-log">
                  <span className="mono text-xs">↵</span>
                  Ctrl+Enter to Analyze
                </div>
              </div>
              <div className="px-4 pb-4 flex flex-col gap-4">
                <input
                  className="w-full bg-background-deep border border-surface-elevated rounded px-4 py-3 text-text-primary font-body-sm focus:outline-none focus:border-accent-electric focus:ring-1 focus:ring-accent-electric"
                  placeholder="WhatsApp Forward? Enter your number to receive result on WhatsApp"
                  type="text"
                />
                <select className="w-full bg-background-deep border border-surface-elevated rounded px-4 py-3 text-text-primary font-body-sm focus:outline-none focus:border-accent-electric focus:ring-1 focus:ring-accent-electric">
                  <option>Claim Language: Auto-detect</option>
                  <option>English</option>
                  <option>Hindi</option>
                  <option>Marathi</option>
                </select>
              </div>
              <div className="p-4 border-t border-surface-elevated bg-background-deep flex flex-col gap-3">
                <button className="w-full bg-accent-electric hover:bg-accent-electric/90 text-white font-headline-lg text-[16px] py-3 rounded flex items-center justify-center gap-2 transition-colors shadow-[0_0_12px_rgba(94,43,255,0.4)]">
                  Analyze with CivicShield →
                </button>
                <p className="text-text-primary/60 text-xs">
                  Takes ~6 seconds. Verified against PIB, MyGov, and Google Fact Check.
                </p>
              </div>
            </div>
            <AgentPipeline title="AI Agents Working..." steps={pipelineSteps} />
          </div>

          <div className="col-span-12 lg:col-span-5 flex flex-col gap-gutter">
            <div className="bg-surface-base border border-surface-elevated rounded p-6 flex flex-col items-center gap-6 relative overflow-hidden">
              <div className="absolute inset-0 bg-danger-bold/5 z-0 pointer-events-none"></div>
              <div className="relative z-10 w-full flex justify-between items-start">
                <h2 className="font-headline-lg text-headline-lg text-text-primary">Analysis Result</h2>
                <TrustScoreBadge verdict="FALSE" className="px-3 py-1" />
              </div>
              <div className="relative w-48 h-48 flex items-center justify-center z-10">
                <svg className="w-full h-full transform -rotate-90" viewBox="0 0 100 100">
                  <circle cx="50" cy="50" r="40" fill="none" stroke="#1A1A2E" strokeWidth="8"></circle>
                  <circle
                    cx="50"
                    cy="50"
                    r="40"
                    fill="none"
                    stroke="#FF3366"
                    strokeDasharray="251.2"
                    strokeDashoffset="213.5"
                    strokeWidth="8"
                  ></circle>
                </svg>
                <div className="absolute flex flex-col items-center justify-center">
                  <span className="font-data-num text-[48px] text-danger-bold leading-none">15</span>
                  <span className="font-badge-label text-badge-label text-text-primary/60 uppercase mt-1">
                    Trust Score
                  </span>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-3 w-full text-xs">
                {[
                  { label: "LLM Confidence", value: "28%" },
                  { label: "Source Match", value: "19%" },
                  { label: "Source Found", value: "0%" },
                  { label: "Deepfake Score", value: "91%" },
                  { label: "Crowd Reports", value: "3%" }
                ].map((item) => (
                  <div key={item.label} className="bg-background-deep border border-surface-elevated rounded p-2">
                    <div className="font-badge-label text-[9px] uppercase text-text-primary/50">{item.label}</div>
                    <div className="font-data-num text-[14px] text-text-primary mt-1">{item.value}</div>
                    <div className="h-1 bg-surface-elevated rounded mt-2">
                      <div className="h-1 bg-accent-electric rounded" style={{ width: item.value }}></div>
                    </div>
                  </div>
                ))}
              </div>
              <div className="w-full z-10">
                <div className="bg-background-deep border-l-2 border-danger-bold p-4 mb-4">
                  <h4 className="font-badge-label text-badge-label text-danger-bold mb-2">IDENTIFIED CLAIM</h4>
                  <p className="font-body-base text-body-base text-text-primary/80 italic">
                    "The central bank has announced a sudden currency recall effective midnight tonight."
                  </p>
                </div>
                <div className="bg-surface-elevated/30 border border-surface-elevated rounded p-4 mb-4">
                  <h4 className="font-badge-label text-badge-label text-success-neon mb-2">VERIFIED FACT</h4>
                  <blockquote className="font-body-base text-body-base text-text-primary">
                    The central bank has issued no such directive. Official channels confirm this is a recirculated rumor
                    from 2016. Current currency remains legal tender with no immediate policy changes planned.
                  </blockquote>
                  <div className="mt-3 flex flex-wrap gap-2">
                    <span className="text-[10px] font-badge-label uppercase px-2 py-1 border border-surface-elevated rounded text-text-primary/60">
                      📎 pib.gov.in
                    </span>
                    <span className="text-[10px] font-badge-label uppercase px-2 py-1 border border-surface-elevated rounded text-text-primary/60">
                      📎 mygov.in
                    </span>
                  </div>
                </div>
                <div className="border border-surface-elevated rounded overflow-hidden">
                  <div className="bg-surface-elevated px-4 py-2 flex justify-between items-center">
                    <span className="font-badge-label text-badge-label text-text-primary">COUNTER STATEMENT</span>
                    <div className="flex bg-background-deep rounded p-0.5 border border-surface-elevated">
                      <button className="px-2 py-0.5 text-[10px] font-badge-label rounded bg-surface-elevated text-text-primary">
                        EN
                      </button>
                      <button className="px-2 py-0.5 text-[10px] font-badge-label rounded text-text-primary/40 hover:text-text-primary">
                        HI
                      </button>
                    </div>
                  </div>
                  <div className="p-4 bg-background-deep">
                    <p className="font-body-sm text-body-sm text-text-primary/80">
                      Please disregard messages claiming an immediate currency recall. The Central Bank has officially
                      stated these claims are entirely false. Rely only on verified announcements from official
                      government portals.
                    </p>
                    <div className="mt-3 flex gap-2">
                      <button className="text-[11px] font-badge-label uppercase px-3 py-1.5 border border-surface-elevated rounded hover:bg-surface-elevated text-text-primary transition-colors">
                        Copy
                      </button>
                      <button className="text-[11px] font-badge-label uppercase px-3 py-1.5 bg-[#25D366]/20 border border-[#25D366]/50 rounded hover:bg-[#25D366]/30 text-[#25D366] transition-colors">
                        Share via WhatsApp
                      </button>
                    </div>
                  </div>
                </div>
                <div className="mt-4 flex flex-wrap items-center justify-between gap-3 text-xs text-text-primary/70">
                  <div className="flex items-center gap-3">
                    <span>Was this helpful?</span>
                    <button className="px-2 py-1 border border-surface-elevated rounded hover:bg-surface-elevated">
                      👍
                    </button>
                    <button className="px-2 py-1 border border-surface-elevated rounded hover:bg-surface-elevated">
                      👎
                    </button>
                  </div>
                  <button className="underline underline-offset-4">Report an error in this analysis</button>
                  <button className="text-accent-electric">Analyze another claim →</button>
                </div>
              </div>
            </div>

            <div className="bg-background-deep border border-surface-elevated rounded h-48 flex flex-col">
              <div className="px-3 py-1.5 bg-surface-elevated/50 border-b border-surface-elevated flex items-center gap-2">
                <span className="font-terminal-log text-[10px] text-text-primary/60 uppercase">
                  System_Log / Analysis_Trace
                </span>
              </div>
              <div className="p-3 overflow-y-auto terminal-scroll font-terminal-log text-terminal-log text-text-primary/50 flex flex-col gap-1">
                {logLines.map((line) => (
                  <div key={line}>
                    <span className="text-accent-electric mr-2">14:02</span>
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
