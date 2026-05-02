import Footer from "../components/Footer"
import Navbar from "../components/Navbar"

export default function PropagationGraph() {
  return (
    <Navbar topSearchPlaceholder="QUERY GRAPH...">
      <main className="flex-1 flex overflow-hidden relative bg-graph-pattern">
        <div className="absolute top-0 left-0 right-80 z-20 p-container-padding">
          <div className="bg-background-deep/80 border border-surface-elevated rounded p-4 backdrop-blur-sm">
            <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-3">
              <div>
                <h1 className="font-headline-lg text-headline-lg text-text-primary">
                  Propagation Tracker — How Misinformation Spreads
                </h1>
                <p className="text-body-sm text-on-surface-variant">
                  Enter claim text or URL to trace...
                </p>
              </div>
              <div className="flex flex-wrap gap-2">
                <select className="bg-surface-base border border-surface-elevated rounded px-3 py-2 text-body-sm text-text-primary">
                  <option>Platform: All</option>
                  <option>Twitter</option>
                  <option>WhatsApp</option>
                  <option>Facebook</option>
                </select>
                <select className="bg-surface-base border border-surface-elevated rounded px-3 py-2 text-body-sm text-text-primary">
                  <option>Date Range</option>
                  <option>Last 24h</option>
                  <option>Last 7 days</option>
                </select>
                <select className="bg-surface-base border border-surface-elevated rounded px-3 py-2 text-body-sm text-text-primary">
                  <option>Reach</option>
                  <option>0-10k</option>
                  <option>10k-100k</option>
                </select>
              </div>
            </div>
          </div>
        </div>
        <div className="flex-1 relative w-full h-full pt-28">
          <svg className="absolute inset-0 w-full h-full pointer-events-none" style={{ zIndex: 10 }}>
            <path d="M 300 250 Q 400 200 500 300" fill="none" opacity="0.6" stroke="#5E2BFF" strokeDasharray="4 4" strokeWidth="2"></path>
            <path d="M 500 300 C 600 400 700 250 800 350" fill="none" opacity="0.4" stroke="#00F5A0" strokeWidth="1.5"></path>
            <path d="M 500 300 L 450 450" fill="none" opacity="0.8" stroke="#FF3366" strokeWidth="3"></path>
            <path d="M 800 350 L 900 200" fill="none" opacity="0.3" stroke="#5E2BFF" strokeWidth="1"></path>
          </svg>

          <div className="absolute top-[230px] left-[280px] z-20 flex flex-col items-center group">
            <div className="w-10 h-10 rounded-full bg-surface-elevated border-2 border-outline-variant flex items-center justify-center shadow-[0_0_15px_rgba(26,26,46,0.5)] group-hover:border-accent-electric transition-colors cursor-pointer">
              <span className="text-text-primary text-sm">◎</span>
            </div>
            <span className="font-terminal-log text-terminal-log text-text-primary/60 mt-1 bg-background-deep/80 px-1 rounded">
              Source
            </span>
          </div>

          <div className="absolute top-[280px] left-[480px] z-20 flex flex-col items-center group">
            <div className="w-14 h-14 rounded-full bg-accent-electric/20 border-2 border-accent-electric flex items-center justify-center shadow-[0_0_20px_rgba(94,43,255,0.4)] cursor-pointer">
              <span className="text-accent-electric">◉</span>
            </div>
            <span className="font-terminal-log text-terminal-log text-accent-electric mt-1 bg-background-deep/80 px-1 rounded">
              Hub Alpha
            </span>
          </div>

          <div className="absolute top-[430px] left-[430px] z-20 flex flex-col items-center group">
            <div className="w-8 h-8 rounded-full bg-danger-bold/10 border border-danger-bold flex items-center justify-center shadow-[0_0_10px_rgba(255,51,102,0.3)] cursor-pointer">
              <span className="text-danger-bold text-xs">!</span>
            </div>
          </div>

          <div className="absolute top-[330px] left-[780px] z-20 flex flex-col items-center group">
            <div className="w-12 h-12 rounded-full bg-success-neon/10 border-2 border-success-neon flex items-center justify-center shadow-[0_0_15px_rgba(0,245,160,0.3)] cursor-pointer">
              <span className="text-success-neon">●</span>
            </div>
            <span className="font-terminal-log text-terminal-log text-success-neon mt-1 bg-background-deep/80 px-1 rounded">
              Cluster B
            </span>
          </div>

          <div className="absolute top-[180px] left-[880px] z-20 flex flex-col items-center group">
            <div className="w-6 h-6 rounded-full bg-surface-elevated border border-outline-variant flex items-center justify-center cursor-pointer"></div>
          </div>
        </div>

        <aside className="w-80 bg-surface-base border-l border-surface-elevated flex flex-col h-full z-30 shadow-[-10px_0_20px_rgba(0,0,0,0.5)]">
          <div className="p-gutter border-b border-surface-elevated bg-surface-container-low">
            <div className="flex items-center justify-between mb-2">
              <h2 className="font-headline-md text-headline-md text-text-primary">Node Details</h2>
              <span className="font-badge-label text-badge-label text-accent-electric bg-accent-electric/10 border border-accent-electric/30 px-2 py-1 rounded">
                SELECTED
              </span>
            </div>
            <p className="font-terminal-log text-terminal-log text-text-primary/60">ID: N-492-X</p>
          </div>
          <div className="p-gutter flex-1 overflow-y-auto flex flex-col gap-card-gap">
            <div className="grid grid-cols-2 gap-unit">
              <div className="bg-surface-elevated border border-outline-variant/30 p-3 rounded">
                <p className="font-badge-label text-badge-label text-text-primary/50 mb-1">REACH</p>
                <p className="font-data-num text-data-num text-accent-electric">14.2K</p>
              </div>
              <div className="bg-surface-elevated border border-outline-variant/30 p-3 rounded">
                <p className="font-badge-label text-badge-label text-text-primary/50 mb-1">SHARES</p>
                <p className="font-data-num text-data-num text-success-neon">3,492</p>
              </div>
            </div>
            <div className="bg-surface-elevated border border-outline-variant/30 p-3 rounded mt-2">
              <p className="font-badge-label text-badge-label text-text-primary/50 mb-2">FIRST SEEN</p>
              <p className="font-terminal-log text-terminal-log text-text-primary">2023-10-24T08:14:22Z</p>
            </div>
            <div className="mt-4">
              <h3 className="font-badge-label text-badge-label text-text-primary/70 mb-2 border-b border-surface-elevated pb-1">
                PROPAGATION LOG
              </h3>
              <div className="bg-background-deep border border-surface-elevated rounded p-2 h-32 overflow-y-auto font-terminal-log text-[10px] text-text-primary/80 flex flex-col gap-1">
                <div>
                  <span className="text-success-neon">[+0s]</span> Node initiated on Platform X
                </div>
                <div>
                  <span className="text-accent-electric">[+14s]</span> Re-shared by high-influence user (ID:882)
                </div>
                <div>
                  <span className="text-text-primary/50">[+45s]</span> Cross-platform bridge detected (WhatsApp)
                </div>
                <div>
                  <span className="text-danger-bold">[+2m]</span> Velocity spike: 500 shares/min
                </div>
                <div>
                  <span className="text-accent-electric">[+5m]</span> Cluster formation verified
                </div>
                <div className="animate-pulse text-text-primary">_</div>
              </div>
            </div>
          </div>
          <div className="p-gutter border-t border-surface-elevated">
            <button className="w-full bg-accent-electric text-white font-headline-md text-sm py-3 rounded hover:bg-inverse-primary transition-colors flex items-center justify-center gap-2">
              ISOLATE SUBGRAPH
              <span aria-hidden="true">→</span>
            </button>
          </div>
        </aside>

        <div className="absolute bottom-0 left-0 right-80 h-24 bg-surface-base/90 backdrop-blur-sm border-t border-surface-elevated z-30 p-gutter flex flex-col justify-center gap-2 shadow-[0_-10px_20px_rgba(0,0,0,0.5)]">
          <div className="flex items-center justify-between font-terminal-log text-[10px] text-text-primary/60">
            <span>T-00:00:00</span>
            <span className="text-accent-electric">LIVE VIEW</span>
          </div>
          <div className="flex items-center gap-4">
            <button className="w-8 h-8 rounded-full bg-surface-elevated border border-outline-variant flex items-center justify-center text-text-primary hover:text-accent-electric hover:border-accent-electric transition-colors flex-shrink-0">
              ▶
            </button>
            <div className="flex-1 relative h-1.5 bg-surface-elevated rounded-full">
              <div className="absolute left-0 top-0 bottom-0 w-[80%] bg-gradient-to-r from-success-neon/50 to-accent-electric rounded-full shadow-[0_0_10px_rgba(94,43,255,0.5)]"></div>
              <div className="absolute left-[80%] top-1/2 -translate-y-1/2 -translate-x-1/2 w-3 h-3 rounded-full bg-text-primary border-2 border-accent-electric cursor-pointer hover:scale-125 transition-transform shadow-[0_0_5px_rgba(240,239,244,0.8)]"></div>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </Navbar>
  )
}
