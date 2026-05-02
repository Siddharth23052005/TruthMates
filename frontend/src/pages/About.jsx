import Footer from "../components/Footer"
import Navbar from "../components/Navbar"

const agents = [
  {
    id: "01",
    name: "Deepfake Detector",
    description: "Analyzes pixel-level noise, biometrics, and synthetic artifacts."
  },
  {
    id: "02",
    name: "Evidence Retriever",
    description: "Scours trusted global databases for corroborating or conflicting data."
  },
  {
    id: "03",
    name: "Context Analyzer",
    description: "Evaluates historical precedence and sociopolitical framing."
  },
  {
    id: "04",
    name: "Source Verifier",
    description: "Ranks publisher credibility and domain reputation scores."
  },
  {
    id: "05",
    name: "Sentiment Engine",
    description: "Detects emotional manipulation and inflammatory linguistics."
  },
  {
    id: "06",
    name: "Bias Evaluator",
    description: "Flags logical fallacies and partisan skew in narrative structure."
  },
  {
    id: "07",
    name: "Geospatial Tracker",
    description: "Cross-references metadata with global satellite and weather APIs."
  },
  {
    id: "08",
    name: "Linguistic Profiler",
    description: "Identifies bot-farm syntax and foreign interference patterns."
  },
  {
    id: "09",
    name: "Network Mapper",
    description: "Graphs the propagation vector across social graphs."
  },
  {
    id: "10",
    name: "Final Arbiter",
    description: "Synthesizes agent outputs into a definitive Trust Score."
  }
]

const stack = [
  "Vector DB Cluster",
  "Large Language Models (LLM)",
  "Apache Kafka Stream",
  "Zero-Trust Architecture",
  "GraphQL Gateway"
]

const team = [
  {
    name: "Dr. Aris Thorne",
    title: "Chief Data Architect",
    image:
      "https://lh3.googleusercontent.com/aida-public/AB6AXuB4s6tAIy4JCOU1WXSkHQOke93PzOx1pX7gHcBgMpSuB5qljqtXHNoqVXldCTcTueclX7EwNdIEdkU-ekOvQPyDIVmua4wXXLy3rpuxp5fbIOIQ5ZqNy1yt4jQjUBOsbI2sdJj_r5IcjzYE4mye_bGSCRmunxHh9QQrfNawpUFnGU0alWpTf_xnarPSPuV30Q_MjDFhTR8d-eDPMbnBhQ0YbycnFaPB3kbEtxQz5an4GHliTNa7HJU2wPTPkFrgmXqbOHl5moKjGV8c"
  },
  {
    name: "Elena Rostova",
    title: "Head of NLP Models",
    image:
      "https://lh3.googleusercontent.com/aida-public/AB6AXuATtZDwuLCRB_ptkdhg5JVwK1iO2-7sXXkeLusZ9Dy8MHBHZEC-4_8h9sS24qzJuG-4L1bwWZuNAw_B5TPQoesq9w7-dzjL1CBE9rjgLuwzeV7dkxwbFXjM84-4gwLeDgsi7TYoMIsLC_T7dIiRSnJrEh5UaDfOOMxTEtYxL4cJdItgBy_rmkgAPUgm4l5q6go1iGUod1HTDQTm4Zbq5jqonpg-AILQwL0vauICh_N0P0PdHMNndNpYsFEFoQcU_CM4jQK-Z_cUZzK5"
  },
  {
    name: "Marcus Vance",
    title: "Threat Intel Lead",
    image:
      "https://lh3.googleusercontent.com/aida-public/AB6AXuC96pUXvRKz08-xxrKNkwKkpK94CzSg1ydTSlpm17fCNEhZ2WjIICwGSE4ltlkoE3JPaxWH0MEHqQ1w8vlUbQrxCpkSbEQOU2vGcMrEm0XXncn8uqHP3npYr0ktJ5cIspN8bRkV9wle16_uemj-TrYYT00ZdLBAB9kzvGM3ZIrMLAJnKIgVfyVSAXG1M4I2UkDm1vYFG7II5gsY0zFVmkKqnOHBIIZSqQKlnOwlxbiJ-pgs5CyNz0_CJ38NRfOa_lTOhBozmoULgdJO"
  }
]

export default function About() {
  return (
    <Navbar topSearchPlaceholder="QUERY ARCHIVE...">
      <main className="flex-1 overflow-y-auto bg-background-deep p-container-padding pb-32">
        <div className="max-w-[1400px] mx-auto space-y-[48px]">
          <div className="border-b border-surface-elevated pb-6">
            <div className="font-badge-label text-badge-label text-accent-electric mb-2 tracking-widest">
              [ SYS_DIR: /ABOUT/MISSION ]
            </div>
            <h2 className="font-hero-display text-hero-display text-text-primary mb-4">
              Civic Truth <br />
              <span className="text-on-surface-variant">Infrastructure.</span>
            </h2>
            <p className="font-body-base text-body-base text-on-surface-variant max-w-3xl">
              TruthMates is a high-stakes verification engine designed for national security and social stability. We
              deploy autonomous, specialized AI agents to dissect, trace, and neutralize digital misinformation in
              real-time. Our mission is to restore consensus reality through absolute cryptographic and analytical
              transparency.
            </p>
          </div>

          <section className="grid grid-cols-1 lg:grid-cols-3 gap-gutter">
            <div className="lg:col-span-2 bg-surface-base border border-surface-elevated p-6 relative overflow-hidden group hover:border-outline-variant transition-colors">
              <div className="absolute top-0 right-0 w-32 h-32 bg-accent-electric/5 rounded-bl-full pointer-events-none"></div>
              <h3 className="font-headline-lg text-headline-lg text-text-primary mb-4">The Architecture of Trust</h3>
              <p className="font-body-base text-body-base text-on-surface-variant mb-6">
                In an era where synthetic media outpaces human verification, relying on single-source fact-checking is a
                vulnerability. TruthMates utilizes a decentralized pipeline of specialized agents. Each rumor, claim, or
                media asset is subjected to hostile scrutiny by our proprietary 10-stage consensus protocol before a
                final verdict is recorded on the immutable ledger.
              </p>
              <div className="flex gap-4">
                <div className="px-4 py-2 bg-surface-elevated border-l-2 border-accent-electric">
                  <div className="font-data-num text-data-num text-text-primary">99.9%</div>
                  <div className="font-badge-label text-badge-label text-on-surface-variant mt-1">Uptime SLA</div>
                </div>
                <div className="px-4 py-2 bg-surface-elevated border-l-2 border-success-neon">
                  <div className="font-data-num text-data-num text-text-primary">&lt; 400ms</div>
                  <div className="font-badge-label text-badge-label text-on-surface-variant mt-1">Verdict Latency</div>
                </div>
              </div>
            </div>
            <div className="bg-surface-base border border-surface-elevated p-6 flex flex-col justify-center items-center text-center relative">
              <div className="text-[48px] text-accent-electric mb-4">🛡️</div>
              <h4 className="font-headline-md text-headline-md text-text-primary mb-2">Protocol Active</h4>
              <p className="font-body-sm text-body-sm text-on-surface-variant">
                Continuous monitoring of high-risk vectors across 50+ global intelligence feeds.
              </p>
            </div>
          </section>

          <section>
            <div className="flex items-center justify-between mb-6">
              <h3 className="font-headline-lg text-headline-lg text-text-primary">The 10 AI Agents</h3>
              <div className="font-terminal-log text-terminal-log text-on-surface-variant border border-surface-elevated px-3 py-1 rounded bg-surface-base">
                &gt; pipeline_status: ONLINE
              </div>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-card-gap">
              {agents.map((agent) => (
                <div
                  key={agent.id}
                  className="bg-surface-base border border-surface-elevated p-4 hover:bg-surface-elevated hover:border-accent-electric transition-all duration-200 group"
                >
                  <div className="flex justify-between items-start mb-4">
                    <span className="text-accent-electric text-[24px]">◆</span>
                    <span className="font-data-num text-data-num text-on-surface-variant/30 text-sm group-hover:text-accent-electric/50">
                      {agent.id}
                    </span>
                  </div>
                  <h4 className="font-headline-md text-[18px] text-text-primary mb-2 leading-tight">{agent.name}</h4>
                  <div className="h-px w-full bg-surface-elevated mb-3 group-hover:bg-accent-electric/30"></div>
                  <p className="font-body-sm text-body-sm text-on-surface-variant leading-snug">{agent.description}</p>
                </div>
              ))}
            </div>
          </section>

          <section className="border-y border-surface-elevated py-8">
            <h3 className="font-badge-label text-badge-label text-on-surface-variant uppercase tracking-widest mb-4">
              Core Infrastructure
            </h3>
            <div className="flex flex-wrap gap-3">
              {stack.map((item) => (
                <div
                  key={item}
                  className="px-4 py-2 border border-surface-elevated bg-[#0A0A10] font-terminal-log text-terminal-log text-text-primary flex items-center gap-2"
                >
                  <span className="text-accent-electric">◆</span>
                  {item}
                </div>
              ))}
            </div>
          </section>

          <section>
            <h3 className="font-headline-lg text-headline-lg text-text-primary mb-6">Key Personnel</h3>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {team.map((member) => (
                <div key={member.name} className="group cursor-pointer">
                  <div className="aspect-square bg-surface-base border border-surface-elevated mb-3 overflow-hidden relative">
                    <div className="absolute inset-0 bg-accent-electric/10 group-hover:bg-transparent transition-colors z-10"></div>
                    <img
                      alt={member.name}
                      className="w-full h-full object-cover filter grayscale contrast-125 group-hover:grayscale-0 transition-all duration-500"
                      src={member.image}
                    />
                  </div>
                  <h4 className="font-headline-md text-[18px] text-text-primary leading-none mb-1">
                    {member.name}
                  </h4>
                  <p className="font-terminal-log text-terminal-log text-accent-electric">{member.title}</p>
                </div>
              ))}
              <div className="group cursor-pointer">
                <div className="aspect-square bg-surface-base border border-surface-elevated mb-3 overflow-hidden relative flex items-center justify-center">
                  <span className="text-[48px] text-on-surface-variant">◎</span>
                </div>
                <h4 className="font-headline-md text-[18px] text-text-primary leading-none mb-1 text-on-surface-variant">
                  REDACTED
                </h4>
                <p className="font-terminal-log text-terminal-log text-on-surface-variant/50">Cryptography Specialist</p>
              </div>
            </div>
          </section>
        </div>
      </main>
      <Footer />
    </Navbar>
  )
}
