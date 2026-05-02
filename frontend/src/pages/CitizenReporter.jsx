import { ChevronDown, Crosshair, Gavel, Lock, MapPin, UploadCloud } from "lucide-react"
import Footer from "../components/Footer"
import Navbar from "../components/Navbar"

export default function CitizenReporter() {
  return (
    <Navbar showTopSearch={false}>
      <main className="flex-1 overflow-y-auto p-container-padding">
        <div className="max-w-7xl mx-auto">
          <div className="mb-8">
            <h1 className="font-headline-lg text-headline-lg text-text-primary">Intel Submission Portal</h1>
            <p className="font-body-sm text-body-sm text-text-primary/60 mt-1">
              Provide unverified ground reports for systemic analysis.
            </p>
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-12 gap-gutter items-start">
            <div className="xl:col-span-8 bg-surface-base border border-surface-elevated rounded p-6 shadow-2xl relative overflow-hidden">
              <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-accent-electric to-transparent"></div>
              <div className="flex items-center gap-3 mb-6 pb-4 border-b border-surface-elevated">
                <div className="w-10 h-10 rounded-full bg-surface-elevated flex items-center justify-center text-accent-electric">
                  <Gavel className="h-5 w-5" />
                </div>
                <div>
                  <h2 className="font-headline-md text-headline-md text-text-primary leading-tight">Lodge Report</h2>
                  <span className="font-terminal-log text-terminal-log text-text-primary/50 uppercase tracking-widest">
                    ID: TX-9942-A
                  </span>
                </div>
              </div>
              <form className="space-y-6">
                <div className="space-y-2">
                  <label className="block font-badge-label text-badge-label text-text-primary/70 uppercase" htmlFor="report-content">
                    What did you hear?
                  </label>
                  <textarea
                    id="report-content"
                    className="w-full bg-surface-container border border-outline-variant rounded p-4 text-text-primary font-body-base focus:outline-none focus:border-accent-electric focus:ring-1 focus:ring-accent-electric transition-colors resize-none"
                    placeholder="Detail the claim, actors involved, and context..."
                    rows="6"
                  ></textarea>
                </div>
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <label className="block font-badge-label text-badge-label text-text-primary/70 uppercase" htmlFor="location">
                      Origin Location
                    </label>
                    <div className="relative">
                      <MapPin className="absolute inset-y-0 left-3 my-auto h-4 w-4 text-text-primary/50" />
                      <input
                        id="location"
                        className="w-full bg-surface-container border border-outline-variant rounded py-3 pl-10 pr-10 text-text-primary font-body-sm focus:outline-none focus:border-accent-electric focus:ring-1 focus:ring-accent-electric transition-colors"
                        placeholder="City, Region, or coordinates"
                        type="text"
                      />
                      <button
                        className="absolute inset-y-0 right-0 pr-3 flex items-center text-accent-electric hover:text-accent-warm transition-colors"
                        type="button"
                      >
                        <Crosshair className="h-4 w-4" />
                      </button>
                    </div>
                  </div>
                  <div className="space-y-2">
                    <label className="block font-badge-label text-badge-label text-text-primary/70 uppercase" htmlFor="language">
                      Source Language
                    </label>
                    <div className="relative">
                      <select
                        id="language"
                        className="w-full bg-surface-container border border-outline-variant rounded py-3 pl-4 pr-10 text-text-primary font-body-sm appearance-none focus:outline-none focus:border-accent-electric focus:ring-1 focus:ring-accent-electric transition-colors"
                      >
                        <option value="en">English</option>
                        <option value="hi">Hindi</option>
                        <option value="mr">Marathi</option>
                        <option value="other">Other / Unknown</option>
                      </select>
                      <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none text-text-primary/50">
                        <ChevronDown className="h-4 w-4" />
                      </div>
                    </div>
                  </div>
                </div>
                <div className="border border-dashed border-outline-variant rounded p-6 flex flex-col items-center justify-center text-center hover:border-accent-electric/50 transition-colors bg-surface-container/30 cursor-pointer">
                  <UploadCloud className="h-8 w-8 text-text-primary/40 mb-2" />
                  <span className="font-body-sm text-body-sm text-text-primary/80">
                    Drop media files here or click to browse
                  </span>
                  <span className="font-terminal-log text-terminal-log text-text-primary/40 mt-1">
                    Supported: JPG, PNG, MP4, MP3 (Max 50MB)
                  </span>
                </div>
                <div className="pt-4 flex items-center justify-between border-t border-surface-elevated">
                  <div className="flex items-center gap-2 text-success-neon font-terminal-log text-terminal-log">
                    <Lock className="h-4 w-4" /> End-to-End Encrypted
                  </div>
                  <button
                    className="bg-accent-electric hover:bg-primary-container text-white font-body-sm font-semibold py-3 px-8 rounded transition-all duration-200 shadow-[0_0_15px_rgba(94,43,255,0.3)] hover:shadow-[0_0_20px_rgba(94,43,255,0.5)] flex items-center gap-2"
                    type="submit"
                  >
                    Submit Report
                    <span aria-hidden="true">→</span>
                  </button>
                </div>
              </form>
            </div>

            <div className="xl:col-span-4 space-y-gutter">
              <div className="bg-surface-base border border-surface-elevated rounded p-5">
                <div className="flex items-center justify-between mb-4">
                  <span className="font-badge-label text-badge-label text-text-primary/50 uppercase tracking-widest">
                    System Status
                  </span>
                  <span className="font-badge-label text-badge-label text-success-neon bg-success-neon/10 border border-success-neon/30 px-2 py-0.5 rounded-sm">
                    ONLINE
                  </span>
                </div>
                <div className="flex items-center gap-4">
                  <div className="relative w-16 h-16 flex items-center justify-center">
                    <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
                      <path
                        className="text-surface-elevated"
                        d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="3"
                      ></path>
                      <path
                        className="text-accent-electric"
                        d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
                        fill="none"
                        stroke="currentColor"
                        strokeDasharray="85, 100"
                        strokeWidth="3"
                      ></path>
                    </svg>
                    <div className="absolute inset-0 flex items-center justify-center">
                      <span className="font-data-num text-data-num text-text-primary">85%</span>
                    </div>
                  </div>
                  <div>
                    <div className="font-body-sm text-body-sm text-text-primary">Current Network Reliability</div>
                    <div className="font-terminal-log text-terminal-log text-text-primary/50">Processing queue: Optimal</div>
                  </div>
                </div>
              </div>

              <div className="bg-background-deep border border-surface-elevated rounded flex flex-col h-[400px]">
                <div className="bg-surface-elevated px-4 py-2 border-b border-surface-container flex items-center gap-2">
                  <span className="font-terminal-log text-terminal-log text-text-primary uppercase">
                    Protocol_Guidelines.txt
                  </span>
                </div>
                <div className="p-4 flex-1 overflow-y-auto terminal-scroll font-terminal-log text-terminal-log text-text-primary/70 leading-relaxed space-y-4">
                  <p className="text-success-neon">&gt; INITIALIZING REPORTER PROTOCOLS...</p>
                  <div>
                    <span className="text-accent-warm">[!] CRITICAL DIRECTIVES</span>
                    <br />
                    To ensure maximal utility for the TruthMates analysis engine, adhere to the following data
                    structures:
                  </div>
                  <ul className="space-y-3 pl-2 border-l border-surface-elevated">
                    <li>
                      <strong className="text-text-primary">1. Specificity over Volume</strong>
                      <br />
                      Names, dates, and exact quotes hold higher weight than generalized summaries.
                    </li>
                    <li>
                      <strong className="text-text-primary">2. Distinguish Source Types</strong>
                      <br />
                      Clearly state if information is first-hand (witnessed) vs. second-hand (heard from another).
                    </li>
                    <li>
                      <strong className="text-text-primary">3. Media Integrity</strong>
                      <br />
                      Do not alter or compress audio/video files prior to upload. Metadata is crucial for the pipeline.
                    </li>
                    <li>
                      <strong className="text-text-primary">4. Contextual Anchors</strong>
                      <br />
                      Provide the environmental context (e.g., "heard at a local market meeting", "broadcast on a pirate
                      radio station").
                    </li>
                  </ul>
                  <p className="text-text-primary/40 pt-4 border-t border-surface-elevated">&gt; AWAITING INPUT...</p>
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
