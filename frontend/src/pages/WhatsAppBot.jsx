import Footer from "../components/Footer"
import Navbar from "../components/Navbar"

const topNavLinks = [
  { label: "Analyze", to: "/analyze" },
  { label: "Dashboard", to: "/dashboard" },
  { label: "Rumor Heatmap", to: "/rumor-heatmap" },
  { label: "Propagation Graph", to: "/propagation-graph" },
  { label: "Citizen Reporter", to: "/citizen-reporter" },
  { label: "WhatsApp Bot", to: "/whatsapp-bot" },
  { label: "About", to: "/about" }
]

export default function WhatsAppBot() {
  return (
    <Navbar showTopSearch={false} topNavLinks={topNavLinks}>
      <main className="flex-1 overflow-y-auto p-container-padding">
        <div className="max-w-7xl mx-auto h-full flex flex-col">
          <header className="mb-gutter">
            <h1 className="font-headline-lg text-headline-lg text-text-primary mb-2">Deploy Verification Bot</h1>
            <p className="font-body-base text-body-base text-on-surface-variant max-w-2xl">
              Integrate the TruthMates analysis engine directly into your communication streams. Forward suspicious
              claims for instant, secure verification.
            </p>
          </header>
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-gutter flex-1">
            <div className="lg:col-span-5 flex flex-col gap-gutter">
              <div className="bg-surface-base border border-surface-elevated p-6 relative overflow-hidden flex flex-col items-center text-center">
                <div className="absolute top-0 left-0 w-full h-1 bg-[#25D366]"></div>
                <div className="w-16 h-16 bg-[#25D366]/10 rounded-full flex items-center justify-center mb-4 border border-[#25D366]/30">
                  <span className="text-[#25D366] text-3xl">◉</span>
                </div>
                <h3 className="font-headline-md text-headline-md text-text-primary mb-1">+1 (800) TRUTH-01</h3>
                <p className="font-terminal-log text-terminal-log text-on-surface-variant mb-6 uppercase">
                  Encrypted Comm Link Active
                </p>
                <div className="bg-white p-4 rounded-sm border-2 border-surface-elevated mb-6 w-48 h-48 flex flex-col items-center justify-center">
                  <img
                    alt="QR Code"
                    className="w-full h-full object-cover opacity-80"
                    src="https://lh3.googleusercontent.com/aida-public/AB6AXuCBOxFSf8W6a7gvyd4bU4T1iPDdtGNjhLWQx3Ibb0BhX5LpxL3Y0HySIHaT4o0STyOGPx3qGFktf-EyhfVL1FwRPPYbGv3sNT3py94jtrgov9NM2mf9Rc2G5SNrtFJWCEEaTqNXivw_iAUC6TdZC2f2dqamMNvgPridaZ-oZQQ9eKSAa8B-QGrX6ElmRX7pLPYjSeeadUs_Ub-B3FfL57hkqHlBDvNw3uUWiqCSrFiGVr56qH8Phq9KQwCgh75mxSQtOwLr4DA09JEB"
                  />
                </div>
                <button className="w-full bg-[#25D366] hover:bg-[#1EBE5C] text-[#080810] font-headline-md text-sm font-bold uppercase tracking-wider py-3 px-4 flex items-center justify-center gap-2 transition-colors">
                  Open WhatsApp Link
                </button>
              </div>

              <div className="bg-surface-base border border-surface-elevated p-6">
                <h4 className="font-badge-label text-badge-label text-on-surface-variant mb-4 uppercase tracking-widest border-b border-surface-elevated pb-2">
                  Deployment Sequence
                </h4>
                <ol className="space-y-6">
                  <li className="flex items-start gap-4">
                    <div className="w-6 h-6 shrink-0 bg-surface-elevated border border-outline-variant flex items-center justify-center font-data-num text-sm text-text-primary mt-0.5">
                      1
                    </div>
                    <div>
                      <p className="font-headline-md text-base text-text-primary mb-1">Save Secure Number</p>
                      <p className="font-body-sm text-body-sm text-on-surface-variant">
                        Add the TruthMates bot to your device contacts for immediate access during critical information
                        surges.
                      </p>
                    </div>
                  </li>
                  <li className="flex items-start gap-4">
                    <div className="w-6 h-6 shrink-0 bg-surface-elevated border border-outline-variant flex items-center justify-center font-data-num text-sm text-text-primary mt-0.5">
                      2
                    </div>
                    <div>
                      <p className="font-headline-md text-base text-text-primary mb-1">Forward Suspicious Data</p>
                      <p className="font-body-sm text-body-sm text-on-surface-variant">
                        Relay texts, images, or audio notes directly to the bot. Do not alter the original metadata.
                      </p>
                    </div>
                  </li>
                  <li className="flex items-start gap-4">
                    <div className="w-6 h-6 shrink-0 bg-accent-electric/20 border border-accent-electric flex items-center justify-center font-data-num text-sm text-accent-electric mt-0.5 shadow-[0_0_8px_rgba(94,43,255,0.4)]">
                      3
                    </div>
                    <div>
                      <p className="font-headline-md text-base text-text-primary mb-1">Receive Instant Verification</p>
                      <p className="font-body-sm text-body-sm text-on-surface-variant">
                        The engine will cross-reference databases and return a verdict, threat level, and
                        counter-statement within seconds.
                      </p>
                    </div>
                  </li>
                </ol>
              </div>
            </div>

            <div className="lg:col-span-7 flex justify-center items-center bg-[#05050A] border border-surface-elevated p-8 relative overflow-hidden">
              <div
                className="absolute inset-0 opacity-[0.03]"
                style={{ backgroundImage: "radial-gradient(#5E2BFF 1px, transparent 1px)", backgroundSize: "24px 24px" }}
              ></div>
              <div className="w-full max-w-[360px] h-[720px] bg-[#111B21] border border-[#2A2F32] rounded-[2rem] p-2 relative z-10 shadow-2xl">
                <div className="w-full h-full bg-[#0B141A] rounded-[1.75rem] overflow-hidden flex flex-col relative">
                  <div className="bg-[#202C33] h-16 flex items-center px-4 gap-3 border-b border-[#2A2F32] z-20">
                    <span className="text-[#AEBAC1]">←</span>
                    <div className="w-10 h-10 bg-accent-electric rounded-full flex items-center justify-center shrink-0">
                      <span className="text-white text-xl">◎</span>
                    </div>
                    <div className="flex-1 min-w-0">
                      <h5 className="text-[#E9EDEF] font-medium text-[15px] truncate">TruthMates Protocol</h5>
                      <p className="text-[#8696A0] text-[13px] truncate">bot • active</p>
                    </div>
                  </div>
                  <div
                    className="flex-1 overflow-y-auto p-4 flex flex-col gap-4"
                    style={{ backgroundColor: "#0B141A" }}
                  >
                    <div className="self-end max-w-[85%] bg-[#005C4B] rounded-lg rounded-tr-none p-2 shadow-sm">
                      <div className="bg-[#02493C] rounded p-2 mb-1 border-l-4 border-[#25D366]">
                        <p className="text-[#25D366] text-xs font-medium mb-1">Forwarded</p>
                        <p className="text-[#E9EDEF] text-[13px] italic">
                          "BREAKING: New virus variant found in city water supply. Boiling water doesn't work! Share
                          with your family ASAP!"
                        </p>
                      </div>
                      <div className="flex justify-end gap-1 items-center mt-1">
                        <span className="text-[#8696A0] text-[11px]">10:42 AM</span>
                        <span className="text-[#53BDEB] text-[14px]">✓✓</span>
                      </div>
                    </div>
                    <div className="self-start text-[#8696A0] font-terminal-log text-[10px] uppercase flex items-center gap-2">
                      <span className="animate-spin">◌</span>
                      Analyzing claim across 4,200 nodes...
                    </div>
                    <div className="self-start max-w-[90%] bg-[#202C33] rounded-lg rounded-tl-none overflow-hidden shadow-sm border border-[#2A2F32]">
                      <div className="bg-danger-bold/10 border-b border-danger-bold/20 p-3 flex items-center gap-2">
                        <span className="text-danger-bold text-lg">!</span>
                        <span className="font-badge-label text-[12px] text-danger-bold tracking-widest uppercase">
                          REFUTED / PANIC INDUCING
                        </span>
                      </div>
                      <div className="p-3">
                        <p className="text-[#E9EDEF] font-body-sm text-[14px] mb-3 leading-snug">
                          This message is a known fabrication designed to cause public panic. There is no active threat to
                          the municipal water supply.
                        </p>
                        <div className="bg-[#111B21] border border-[#2A2F32] rounded p-2 mb-2">
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-[#8696A0] font-terminal-log text-[10px] uppercase">Threat Score</span>
                            <span className="text-danger-bold font-data-num text-[12px]">88/100</span>
                          </div>
                          <div className="w-full bg-[#2A2F32] h-1 rounded-full overflow-hidden">
                            <div className="bg-danger-bold h-full w-[88%]"></div>
                          </div>
                        </div>
                        <div className="bg-[#111B21] border border-[#2A2F32] rounded p-2 text-[12px]">
                          <span className="text-[#8696A0] font-terminal-log text-[10px] uppercase block mb-1">
                            Counter-Statement:
                          </span>
                          <span className="text-[#E9EDEF]">
                            The EPA and local health boards tested the reservoir at 0800 HRS today. All parameters are
                            normal. Please do not forward the original message.
                          </span>
                        </div>
                      </div>
                      <div className="px-3 py-1.5 flex justify-end">
                        <span className="text-[#8696A0] text-[11px]">10:43 AM</span>
                      </div>
                    </div>
                  </div>
                  <div className="bg-[#202C33] p-2 flex items-center gap-2 border-t border-[#2A2F32] z-20">
                    <button className="w-10 h-10 rounded-full hover:bg-[#111B21] flex items-center justify-center text-[#8696A0] transition-colors">
                      +
                    </button>
                    <div className="flex-1 bg-[#2A2F32] rounded-full h-10 px-4 flex items-center">
                      <span className="text-[#8696A0] text-[15px]">Message</span>
                    </div>
                    <button className="w-10 h-10 rounded-full bg-[#00A884] flex items-center justify-center text-[#111B21] transition-colors shadow-md">
                      🎙️
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
      <Footer />
    </Navbar>
  )
}
