import Navbar from "../components/Navbar"
import Footer from "../components/Footer"
import { Heart, ShieldCheck, Users, CheckCircle2 } from "lucide-react"

export default function About() {
  return (
    <Navbar>
      <main className="flex-1 overflow-y-auto p-6 md:p-12 relative z-10">
        <div className="max-w-4xl mx-auto flex flex-col items-center gap-10 mt-4 pb-12">
          
          <div className="text-center flex flex-col items-center">
            <div className="inline-flex items-center justify-center gap-2 px-4 py-1.5 rounded-full border border-danger-bold/30 bg-danger-bold/5 mb-6 text-danger-bold text-sm font-medium">
              <Heart className="h-4 w-4" />
              Our Purpose
            </div>
            <h1 className="text-5xl md:text-6xl font-black text-text-primary tracking-tight font-hero-display">
              Our Mission
            </h1>
          </div>

          <div className="w-full bg-surface-base border border-surface-elevated rounded-2xl p-8 md:p-12 shadow-sm text-center">
            <div className="mb-8 space-y-3">
              <h2 className="text-xl md:text-2xl font-bold text-danger-bold mb-2">Misinformation is not harmless.</h2>
              <p className="text-xl md:text-2xl text-text-primary font-medium mb-4">It creates fear, panic, and wrong actions.</p>
              <p className="text-lg text-on-surface-variant">During emergencies, even a single false message can cause chaos.</p>
            </div>
            
            <div className="pt-8 mt-4 border-t border-surface-elevated/50">
              <p className="text-lg text-text-primary">
                TruthMates exists to slow the spread of misinformation and help people <span className="text-danger-bold font-bold">think before they share</span>.
              </p>
            </div>
          </div>

          <div className="w-full mt-10">
            <h2 className="text-2xl font-bold text-text-primary text-center mb-8">When people verify before sharing:</h2>
            
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              
              <div className="bg-surface-base border border-surface-elevated rounded-2xl p-6 shadow-sm flex flex-col items-center text-center hover:border-[#10B981]/50 transition-colors">
                <div className="p-4 rounded-2xl bg-[#10B981]/10 mb-5 border border-[#10B981]/20">
                  <ShieldCheck className="h-8 w-8 text-[#10B981]" />
                </div>
                <h3 className="text-lg font-bold text-text-primary mb-3">Peace of mind</h3>
                <p className="text-sm text-on-surface-variant leading-relaxed">Less anxiety from fake news meant to cause emotional panic.</p>
              </div>

              <div className="bg-surface-base border border-surface-elevated rounded-2xl p-6 shadow-sm flex flex-col items-center text-center hover:border-primary/50 transition-colors">
                <div className="p-4 rounded-2xl bg-primary/10 mb-5 border border-primary/20">
                  <Users className="h-8 w-8 text-primary" />
                </div>
                <h3 className="text-lg font-bold text-text-primary mb-3">Trust Returns</h3>
                <p className="text-sm text-on-surface-variant leading-relaxed">Communities start relying on real facts instead of rumors.</p>
              </div>

              <div className="bg-surface-base border border-surface-elevated rounded-2xl p-6 shadow-sm flex flex-col items-center text-center hover:border-danger-bold/50 transition-colors">
                <div className="p-4 rounded-2xl bg-danger-bold/10 mb-5 border border-danger-bold/20">
                  <CheckCircle2 className="h-8 w-8 text-danger-bold" />
                </div>
                <h3 className="text-lg font-bold text-text-primary mb-3">Lives are Saved</h3>
                <p className="text-sm text-on-surface-variant leading-relaxed">During crisis, exact information leads to better decisions.</p>
              </div>

            </div>
          </div>

          <div className="w-full mt-10 bg-surface-base border border-surface-elevated rounded-2xl p-10 md:p-14 shadow-sm text-center">
            <h2 className="text-2xl md:text-3xl font-bold text-text-primary leading-relaxed">
              "In the right moment, the right information<br />
              <span className="text-danger-bold">can save lives.</span>"
            </h2>
          </div>

        </div>
      </main>
      <Footer />
    </Navbar>
  )
}
