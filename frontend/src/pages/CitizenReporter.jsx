import { UploadCloud, CheckCircle } from "lucide-react"
import Footer from "../components/Footer"
import Navbar from "../components/Navbar"

export default function CitizenReporter() {
  return (
    <Navbar>
      <main className="flex-1 overflow-y-auto bg-background-deep p-6">
        <div className="max-w-2xl mx-auto flex flex-col mt-4">
          
          <div className="text-center mb-8">
            <h1 className="text-4xl font-black text-text-primary mb-3 tracking-tight font-hero-display">Citizen Reporter</h1>
            <p className="text-on-surface-variant text-lg">Help us fight misinformation by submitting suspicious claims or tips.</p>
          </div>

          <div className="bg-surface-base border border-surface-elevated rounded-xl p-8 shadow-sm">
            <form className="space-y-6">
              
              <div className="space-y-2">
                <label className="block text-sm font-bold text-text-primary" htmlFor="report-content">
                  What did you see or hear?
                </label>
                <textarea
                  id="report-content"
                  className="w-full bg-background-deep border border-outline-variant rounded-lg p-4 text-text-primary font-body-base focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-colors resize-none"
                  placeholder="Describe the suspicious claim, rumor, or piece of news..."
                  rows="5"
                ></textarea>
              </div>

              <div className="space-y-2">
                <label className="block text-sm font-bold text-text-primary" htmlFor="source">
                  Where did you see this?
                </label>
                <input
                  id="source"
                  type="text"
                  className="w-full bg-background-deep border border-outline-variant rounded-lg p-3 text-text-primary font-body-base focus:outline-none focus:border-primary focus:ring-1 focus:ring-primary transition-colors"
                  placeholder="e.g., WhatsApp group, Facebook post, local news..."
                />
              </div>

              <div className="space-y-2">
                <label className="block text-sm font-bold text-text-primary">
                  Upload Media (Optional)
                </label>
                <div className="border-2 border-dashed border-outline-variant rounded-lg p-8 flex flex-col items-center justify-center text-center hover:border-primary/50 transition-colors bg-background-deep cursor-pointer">
                  <UploadCloud className="h-10 w-10 text-primary mb-3" />
                  <span className="font-bold text-text-primary mb-1">
                    Click to upload or drag and drop
                  </span>
                  <span className="text-sm text-on-surface-variant">
                    JPG, PNG, MP4, or MP3 (Max 50MB)
                  </span>
                </div>
              </div>

              <div className="pt-6">
                <button
                  className="w-full bg-primary hover:bg-primary-fixed text-white font-bold py-4 rounded-xl transition-colors shadow-md text-lg flex items-center justify-center gap-2"
                  type="button"
                >
                  <CheckCircle className="h-5 w-5" />
                  Submit Tip
                </button>
                <p className="text-xs text-center text-on-surface-variant mt-4">
                  Your submission is anonymous and will be reviewed by our AI agents and human analysts.
                </p>
              </div>
              
            </form>
          </div>

        </div>
      </main>
      <Footer />
    </Navbar>
  )
}
