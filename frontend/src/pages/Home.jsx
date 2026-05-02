import { useEffect, useState } from "react"
import { Link } from "react-router-dom"
import {
  Activity,
  Send,
  ShieldCheck,
  Sparkles,
  Target,
  Waves,
  Webhook
} from "lucide-react"
import Footer from "../components/Footer"
import TrustScoreBadge from "../components/TrustScoreBadge"

const statPills = [
  {
    label: "10K+ Claims Analyzed",
    icon: Target
  },
  {
    label: "94% Accuracy",
    icon: Sparkles
  },
  {
    label: "8 Languages Supported",
    icon: Waves
  }
]

const protocolSteps = [
  {
    id: 1,
    title: "Submit",
    description: "Paste text, forward WhatsApp message, or upload audio/video",
    icon: Webhook
  },
  {
    id: 2,
    title: "Analyze",
    description: "10 AI agents verify your claim against official sources",
    icon: Activity
  },
  {
    id: 3,
    title: "Get Truth",
    description: "Receive a verified counter-statement with trust score",
    icon: ShieldCheck
  }
]

const agentCards = [
  {
    name: "Web Scraper",
    description: "Crawls global news endpoints for claim origins."
  },
  {
    name: "Deepfake Detector",
    description: "Analyzes media artifacts for manipulation."
  },
  {
    name: "Propagation Analyst",
    description: "Maps social network spread velocity."
  },
  {
    name: "Historical Matcher",
    description: "Checks against debunked claim database."
  },
  {
    name: "Legal Context",
    description: "Verifies claims against statutory laws."
  },
  {
    name: "Evidence Retriever",
    description: "Scours trusted databases for corroboration."
  },
  {
    name: "Context Analyzer",
    description: "Evaluates historical precedence and framing."
  },
  {
    name: "Source Verifier",
    description: "Ranks publisher credibility and domain trust."
  },
  {
    name: "Sentiment Engine",
    description: "Detects emotional manipulation patterns."
  },
  {
    name: "Final Arbiter",
    description: "Synthesizes agent outputs into a verdict."
  }
]

const liveFeed = [
  {
    time: "14:02:45",
    claim: "New tax law to confiscate all savings accounts over 1M...",
    verdict: "FALSE"
  },
  {
    time: "14:02:38",
    claim: "Video showing protests outside national assembly today...",
    verdict: "UNVERIFIED"
  },
  {
    time: "14:02:10",
    claim: "Official government portal offline due to cyberattack...",
    verdict: "TRUE"
  },
  {
    time: "14:01:55",
    claim: "Water supply contaminated with industrial chemicals in Sector 4...",
    verdict: "FALSE"
  }
]

export default function Home() {
  const [seconds, setSeconds] = useState(15)

  useEffect(() => {
    const timer = setInterval(() => {
      setSeconds((value) => (value <= 1 ? 15 : value - 1))
    }, 1000)

    return () => clearInterval(timer)
  }, [])

  const counter = `00:${String(seconds).padStart(2, "0")}`

  return (
    <div className="bg-background-deep text-text-primary min-h-screen flex flex-col">
      <main className="flex-grow">
        <section className="min-h-screen relative flex items-center justify-center overflow-hidden border-b border-surface-elevated pt-14">
          <div
            className="absolute inset-0 z-0 bg-cover bg-center opacity-30"
            style={{
              backgroundImage:
                "url('https://lh3.googleusercontent.com/aida-public/AB6AXuBlXWHrbrFa29PlC3iFPFm-oKsmiNncCPAXQYqHApItGPNtt2vO4ZhzZcMVGJT1eyZZbs1U1yRUw9zU_ObnPU3yAeiXg7xyqZklTNSIcizZeVJp_3Y3zK_AZJEtQjV-GY541--R89QD5dFD6ffeabmkdS1FLdYZrL94Vo88eOaGc33YBfUXK8obT0jVgMoJ9h7mcv8sIGKXGXz9EkgL7NSXgldPcRtZZZF_KlhbgQ7UPMCm_DTXU7Wuea_DBJ7bVxXF56nHPDSKTCUI')"
            }}
          ></div>
          <div className="absolute inset-0 z-0 bg-gradient-to-b from-transparent to-background-deep opacity-90"></div>
          <div className="relative z-10 w-full max-w-7xl px-container-padding flex flex-col items-center text-center gap-card-gap">
            <h1 className="font-hero-display text-hero-display text-white max-w-4xl tracking-tight">
              Misinformation spreads in
              <br />
              <span className="text-accent-electric tabular-nums">{counter}</span>
            </h1>
            <p className="font-body-base text-body-base text-on-surface-variant max-w-2xl mt-4">
              TruthMates detects, verifies, and counters civic fake news before it spreads.
            </p>
            <div className="flex flex-wrap gap-4 mt-8 justify-center">
              <Link
                to="/analyze"
                className="bg-accent-electric text-white font-badge-label text-badge-label px-8 py-4 rounded hover:opacity-90 transition-opacity flex items-center gap-2"
              >
                Try It Now <span aria-hidden="true">→</span>
              </Link>
              <a
                href="#protocol"
                className="bg-transparent text-text-primary font-badge-label text-badge-label px-8 py-4 rounded border border-surface-elevated hover:bg-surface-elevated transition-colors"
              >
                See How It Works
              </a>
            </div>
            <div className="flex flex-wrap justify-center gap-4 mt-12 w-full max-w-4xl">
              {statPills.map((pill) => {
                const Icon = pill.icon
                return (
                  <div
                    key={pill.label}
                    className="bg-surface-base border border-surface-elevated px-6 py-3 rounded flex items-center gap-3"
                  >
                    <Icon className="h-4 w-4 text-success-neon" />
                    <span className="font-data-num text-data-num text-white">{pill.label}</span>
                  </div>
                )
              })}
            </div>
          </div>
        </section>

        <section id="protocol" className="py-24 px-container-padding bg-surface-base border-b border-surface-elevated">
          <div className="max-w-7xl mx-auto">
            <h2 className="font-headline-lg text-headline-lg text-white mb-12 text-center">Protocol Operation</h2>
            <div className="flex flex-col md:flex-row justify-between items-start md:items-center gap-8 relative">
              <div className="hidden md:block absolute top-1/2 left-0 w-full h-[1px] bg-surface-elevated -z-10"></div>
              {protocolSteps.map((step, index) => {
                const Icon = step.icon
                return (
                  <div key={step.id} className="flex items-center w-full">
                    <div className="bg-background-deep border border-surface-elevated p-6 rounded flex flex-col items-center text-center gap-4 flex-1 relative">
                      <div className="w-12 h-12 rounded-full bg-surface-elevated flex items-center justify-center border border-accent-electric shadow-[0_0_20px_rgba(94,43,255,0.2)]">
                        <Icon className="h-5 w-5 text-accent-electric" />
                      </div>
                      <h3 className="font-headline-md text-white text-lg">
                        {step.id}. {step.title}
                      </h3>
                      <p className="font-body-sm text-body-sm text-on-surface-variant">
                        {step.description}
                      </p>
                    </div>
                    {index < protocolSteps.length - 1 && (
                      <span className="hidden md:inline-flex text-surface-elevated text-2xl ml-4">›</span>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        </section>

        <section className="py-24 px-container-padding bg-background-deep border-b border-surface-elevated overflow-hidden">
          <div className="max-w-7xl mx-auto mb-12 flex justify-between items-end">
            <div>
              <h2 className="font-headline-lg text-headline-lg text-white">Meet the Intelligence Behind TruthMates</h2>
              <p className="font-body-sm text-body-sm text-on-surface-variant mt-2">Active verification pipeline.</p>
            </div>
          </div>
          <div className="flex overflow-x-auto gap-4 pb-8 snap-x hide-scrollbar">
            {agentCards.map((agent) => (
              <div
                key={agent.name}
                className="min-w-[280px] bg-surface-base border border-surface-elevated p-6 rounded snap-start shrink-0 flex flex-col gap-4"
              >
                <div className="flex justify-between items-center">
                  <span className="text-accent-electric text-3xl">◆</span>
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-success-neon shadow-[0_0_10px_#00F5A0] animate-pulse"></div>
                    <span className="font-badge-label text-badge-label text-success-neon">ACTIVE</span>
                  </div>
                </div>
                <h3 className="font-headline-md text-headline-md text-white mt-4">{agent.name}</h3>
                <p className="font-body-sm text-body-sm text-on-surface-variant">{agent.description}</p>
              </div>
            ))}
          </div>
        </section>

        <section className="py-24 px-container-padding bg-surface-base border-b border-surface-elevated">
          <div className="max-w-7xl mx-auto">
            <h2 className="font-headline-lg text-headline-lg text-white mb-8">Live Claims Being Analyzed Right Now</h2>
            <div className="bg-background-deep border border-surface-elevated rounded overflow-hidden">
              <div className="font-terminal-log text-terminal-log text-on-surface-variant p-4 border-b border-surface-elevated bg-[#1A1A2E] flex justify-between">
                <span>TERMINAL_OUTPUT // LIVE_STREAM</span>
                <div className="flex items-center gap-2">
                  <div className="w-2 h-2 rounded-full bg-accent-electric animate-pulse"></div>
                  <span>SYNCING</span>
                </div>
              </div>
              <div className="p-6 font-terminal-log text-terminal-log text-white">
                <div className="overflow-hidden ticker-mask">
                  <div className="flex gap-6 animate-ticker w-max">
                    {[...liveFeed, ...liveFeed].map((item, index) => (
                      <div
                        key={`${item.time}-${index}`}
                        className="flex items-center gap-4 border border-surface-elevated bg-surface-base/40 px-4 py-2 rounded"
                      >
                        <span className="text-on-surface-variant">[{item.time}]</span>
                        <span className="max-w-[260px] truncate">{item.claim}</span>
                        <TrustScoreBadge verdict={item.verdict} className="text-[9px]" />
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>
      </main>
      <Footer variant="home" />
    </div>
  )
}
