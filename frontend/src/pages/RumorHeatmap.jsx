import Footer from "../components/Footer"
import Navbar from "../components/Navbar"
import { Flame, AlertCircle, Info, TrendingUp } from "lucide-react"

const categories = [
  {
    name: "Election Fraud",
    description: "Claims regarding voting machines, ballot counting, and voter suppression.",
    severity: "High",
    color: "text-danger-bold",
    bgColor: "bg-danger-bold/10",
    borderColor: "border-danger-bold/20",
    icon: Flame,
    volume: "24.5k mentions"
  },
  {
    name: "Public Health & Vaccines",
    description: "Misinformation about unverified cures, vaccine side effects, and disease origins.",
    severity: "High",
    color: "text-danger-bold",
    bgColor: "bg-danger-bold/10",
    borderColor: "border-danger-bold/20",
    icon: Flame,
    volume: "18.2k mentions"
  },
  {
    name: "Economic Policies",
    description: "Rumors about tax hikes, bank runs, and currency devaluation.",
    severity: "Medium",
    color: "text-accent-warm",
    bgColor: "bg-accent-warm/10",
    borderColor: "border-accent-warm/20",
    icon: AlertCircle,
    volume: "8.4k mentions"
  },
  {
    name: "Infrastructure & Transport",
    description: "Fake alerts about highway closures, bridge collapses, and train schedules.",
    severity: "Medium",
    color: "text-accent-warm",
    bgColor: "bg-accent-warm/10",
    borderColor: "border-accent-warm/20",
    icon: AlertCircle,
    volume: "5.1k mentions"
  },
  {
    name: "Celebrity Hoaxes",
    description: "Fabricated quotes, fake endorsements, and AI-generated celebrity images.",
    severity: "Low",
    color: "text-success-neon",
    bgColor: "bg-success-neon/10",
    borderColor: "border-success-neon/20",
    icon: Info,
    volume: "2.3k mentions"
  },
  {
    name: "Weather & Climate",
    description: "Exaggerated storm warnings, fake disaster footage, and climate denial.",
    severity: "Low",
    color: "text-success-neon",
    bgColor: "bg-success-neon/10",
    borderColor: "border-success-neon/20",
    icon: Info,
    volume: "1.8k mentions"
  }
]

export default function RumorHeatmap() {
  return (
    <Navbar>
      <main className="flex-1 overflow-y-auto bg-background-deep p-6">
        <div className="max-w-5xl mx-auto flex flex-col mt-4">
          
          <div className="text-center mb-10">
            <h1 className="text-4xl md:text-5xl font-black text-text-primary mb-3 tracking-tight font-hero-display flex items-center justify-center gap-3">
              <TrendingUp className="h-10 w-10 text-primary" />
              Trending Rumor Categories
            </h1>
            <p className="text-on-surface-variant text-lg">Currently tracking and categorizing active misinformation campaigns.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
            {categories.map((category) => {
              const Icon = category.icon;
              return (
                <div key={category.name} className="bg-surface-base border border-surface-elevated rounded-xl p-6 shadow-sm flex flex-col hover:border-primary/50 transition-colors">
                  <div className="flex justify-between items-start mb-4">
                    <div className={`p-3 rounded-lg ${category.bgColor}`}>
                      <Icon className={`h-6 w-6 ${category.color}`} />
                    </div>
                    <span className={`px-3 py-1 rounded-full text-xs font-bold border ${category.color} ${category.bgColor} ${category.borderColor}`}>
                      {category.severity} Severity
                    </span>
                  </div>
                  
                  <h3 className="text-xl font-bold text-text-primary mb-2">{category.name}</h3>
                  <p className="text-sm text-on-surface-variant flex-1 mb-4">
                    {category.description}
                  </p>
                  
                  <div className="pt-4 border-t border-surface-elevated flex justify-between items-center text-sm font-medium">
                    <span className="text-on-surface-variant">24h Volume</span>
                    <span className="text-text-primary">{category.volume}</span>
                  </div>
                </div>
              );
            })}
          </div>

        </div>
      </main>
      <Footer />
    </Navbar>
  )
}
