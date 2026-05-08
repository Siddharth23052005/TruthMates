import Footer from "../components/Footer"
import Navbar from "../components/Navbar"
import TrustScoreBadge from "../components/TrustScoreBadge"

const trending = [
  {
    label: "Critical",
    claim: "Water supply poisoned in Sector 4...",
    time: "14:02 IST",
    rate: "+4,290/hr",
    verdict: "REFUTED",
    color: "danger"
  },
  {
    label: "Emerging",
    claim: "Fake currency notes distributed at local ATM.",
    time: "13:45 IST",
    rate: "+840/hr",
    verdict: "UNVERIFIED",
    color: "warm"
  },
  {
    label: "Contained",
    claim: "Highway blocked due to protest...",
    time: "10:12 IST",
    rate: "-120/hr",
    verdict: "SUPPORTED",
    color: "success"
  }
]

const colorClasses = {
  danger: {
    stripe: "bg-danger-bold",
    badge: "text-danger-bold bg-danger-bold/10 border-danger-bold/20",
    rate: "text-danger-bold"
  },
  warm: {
    stripe: "bg-accent-warm",
    badge: "text-accent-warm bg-accent-warm/10 border-accent-warm/20",
    rate: "text-accent-warm"
  },
  success: {
    stripe: "bg-success-neon",
    badge: "text-success-neon bg-success-neon/10 border-success-neon/20",
    rate: "text-success-neon"
  }
}

export default function RumorHeatmap() {
  return (
    <Navbar topSearchPlaceholder="Trace query ID...">
      <main className="flex-1 relative flex flex-col overflow-hidden">
        <div className="relative z-20 px-container-padding pt-6">
          <div className="flex flex-col gap-4 border-b border-surface-elevated pb-4">
            <div className="flex items-center justify-between">
              <h1 className="font-headline-lg text-headline-lg text-text-primary">
                Rumor Heatmap — Live Spread Tracker
              </h1>
              <div className="hidden lg:flex items-center gap-2 text-[10px] font-badge-label uppercase tracking-widest text-text-primary/60">
                Live Map
              </div>
            </div>
            <div className="flex flex-col lg:flex-row gap-3">
              <div className="flex flex-1 flex-wrap gap-3">
                <select className="bg-surface-base border border-surface-elevated rounded px-3 py-2 text-body-sm text-text-primary">
                  <option>Last 24h</option>
                  <option>Last 7 days</option>
                  <option>Last 30 days</option>
                </select>
                <select className="bg-surface-base border border-surface-elevated rounded px-3 py-2 text-body-sm text-text-primary">
                  <option>All Claim Types</option>
                  <option>Public Safety</option>
                  <option>Finance</option>
                  <option>Infrastructure</option>
                </select>
                <select className="bg-surface-base border border-surface-elevated rounded px-3 py-2 text-body-sm text-text-primary">
                  <option>All States</option>
                  <option>Maharashtra</option>
                  <option>Delhi</option>
                  <option>Tamil Nadu</option>
                </select>
                <input
                  className="bg-surface-base border border-surface-elevated rounded px-3 py-2 text-body-sm text-text-primary w-full lg:w-64"
                  placeholder="Search claim..."
                  type="text"
                />
              </div>
              <div className="flex gap-2">
                {[
                  "All Claims",
                  "Election",
                  "Schemes",
                  "Health"
                ].map((label) => (
                  <button
                    key={label}
                    className={`px-3 py-2 rounded border text-[10px] font-badge-label uppercase tracking-widest transition-colors ${
                      label === "All Claims"
                        ? "bg-accent-electric/10 border-accent-electric text-accent-electric"
                        : "bg-surface-base border-surface-elevated text-text-primary/60 hover:text-text-primary"
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
          </div>
        </div>
        <div className="absolute inset-0 z-0">
          <img
            alt="Map of India"
            className="w-full h-full object-cover opacity-20"
            src="https://lh3.googleusercontent.com/aida-public/AB6AXuBf8GOP8fU0y4Ed5oED22MPel9Prz2Q-Bbh5vFf_I-X11Rgd1qIRVM-FnfxQksByw9z0_ld_vSDUnGzIsm9OOzR_6iLgWsQDvcQEE4tK1pYzNJsxeCimlXYCbwd4yG8RlCRKBCCuFC_UYn654lz256cnJCiXpaoKHbhnjW8IQyriVKpsImH0gQDVobWKhN9yRK2YHRkSGXDujNaoB3nDOclN_XHz6i3EJM-Jlvtm9AobPP98h4szUAc1xnbkGuVTqIiklooM32gUdrw"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-background-deep via-transparent to-background-deep opacity-80 pointer-events-none"></div>
          <div className="absolute inset-0 bg-gradient-to-r from-background-deep via-transparent to-transparent opacity-60 pointer-events-none w-1/3"></div>
        </div>

        <div className="relative z-10 flex-1 flex p-container-padding gap-container-padding overflow-hidden pt-6">
          <div className="flex-1 relative">
            <div className="absolute top-[30%] left-[45%] w-32 h-32 bg-danger-bold/20 rounded-full blur-xl animate-pulse"></div>
            <div className="absolute top-[32%] left-[47%] w-4 h-4 bg-danger-bold rounded-full shadow-[0_0_20px_rgba(255,51,102,0.8)] border-2 border-background-deep flex items-center justify-center">
              <span className="w-1 h-1 bg-white rounded-full"></span>
            </div>
            <div
              className="absolute top-[60%] left-[30%] w-24 h-24 bg-accent-warm/20 rounded-full blur-lg animate-pulse"
              style={{ animationDelay: "1s" }}
            ></div>
            <div className="absolute top-[62%] left-[32%] w-3 h-3 bg-accent-warm rounded-full shadow-[0_0_15px_rgba(241,156,121,0.6)] border border-background-deep"></div>
            <div className="absolute top-[20%] left-[20%] w-16 h-16 bg-success-neon/20 rounded-full blur-md"></div>
            <div className="absolute top-[21%] left-[21%] w-2 h-2 bg-success-neon rounded-full shadow-[0_0_10px_rgba(0,245,160,0.4)]"></div>
          </div>

          <div className="w-80 flex flex-col gap-card-gap h-full overflow-y-auto pr-2 terminal-scroll">
            <div className="bg-surface-base/80 backdrop-blur-md border border-surface-elevated rounded p-4 sticky top-0 z-20">
              <h2 className="font-headline-md text-body-base text-text-primary flex items-center gap-2">
                Trending Rumors
              </h2>
            </div>
            {trending.map((item) => {
              const classes = colorClasses[item.color]
              return (
              <div
                key={item.claim}
                className="bg-surface-base border border-surface-elevated rounded p-4 hover:border-accent-electric transition-colors group cursor-pointer relative overflow-hidden"
              >
                <div className={`absolute top-0 left-0 w-1 h-full ${classes.stripe}`}></div>
                <div className="flex justify-between items-start mb-3 pl-2">
                  <span
                    className={`font-badge-label text-badge-label px-2 py-1 rounded border uppercase tracking-widest ${classes.badge}`}
                  >
                    {item.label}
                  </span>
                  <span className="font-data-num text-terminal-log text-text-primary/60">{item.time}</span>
                </div>
                <p className="font-body-sm text-body-sm text-text-primary mb-4 pl-2 leading-relaxed">{item.claim}</p>
                <div className="flex items-end justify-between pl-2">
                  <div>
                    <div className="text-[10px] text-text-primary/40 uppercase mb-1 font-badge-label">Spread Rate</div>
                    <div className={`font-data-num text-data-num ${classes.rate}`}>{item.rate}</div>
                  </div>
                  <TrustScoreBadge verdict={item.verdict} className="text-[9px]" />
                </div>
              </div>
              )
            })}
          </div>
        </div>

        <div className="absolute bottom-0 left-0 w-full pointer-events-auto p-6 z-20">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-gutter max-w-3xl">
            <div className="bg-surface-base/90 backdrop-blur-md border border-surface-elevated rounded p-4 flex flex-col justify-center relative overflow-hidden">
              <div className="text-[10px] text-text-primary/50 uppercase font-badge-label tracking-widest mb-1">
                Active Rumors
              </div>
              <div className="font-data-num text-[32px] font-bold text-text-primary leading-none">1,204</div>
              <div className="text-[11px] text-danger-bold mt-2 font-terminal-log">+12% vs yday</div>
            </div>
            <div className="bg-surface-base/90 backdrop-blur-md border border-surface-elevated rounded p-4 flex flex-col justify-center relative overflow-hidden">
              <div className="text-[10px] text-text-primary/50 uppercase font-badge-label tracking-widest mb-1">
                Cities Affected
              </div>
              <div className="font-data-num text-[32px] font-bold text-text-primary leading-none">42</div>
              <div className="text-[11px] text-accent-warm mt-2 font-terminal-log">Stable</div>
            </div>
            <div className="bg-surface-base/90 backdrop-blur-md border border-surface-elevated rounded p-4 flex flex-col justify-center relative overflow-hidden">
              <div className="text-[10px] text-text-primary/50 uppercase font-badge-label tracking-widest mb-1">
                Avg Detection Time
              </div>
              <div className="font-data-num text-[32px] font-bold text-success-neon leading-none">4.2m</div>
              <div className="text-[11px] text-success-neon mt-2 font-terminal-log">-0.8m improved</div>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </Navbar>
  )
}
