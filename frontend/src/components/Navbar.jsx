import { NavLink } from "react-router-dom"
import { Shield, SearchCheck, Mic, Map, Radio, Info } from "lucide-react"

const navItems = [
  { label: "Analyze", to: "/analyze", icon: SearchCheck },
  { label: "Citizen Reporter", to: "/citizen-reporter", icon: Mic },
  { label: "Rumor Heatmap", to: "/rumor-heatmap", icon: Map },
  { label: "Social Monitor", to: "/social-monitor", icon: Radio },
  { label: "Trending", to: "/trending", icon: AlertTriangle },
  { label: "About", to: "/about", icon: Info }
]

function classNames(...classes) {
  return classes.filter(Boolean).join(" ")
}

export default function Navbar({ children }) {
  return (
    <div className="flex flex-col min-h-screen text-text-primary relative z-0">
      {/* Fixed honeycomb background layer to guarantee visibility */}
      <div 
        className="fixed inset-0 z-[-1]" 
        style={{
          backgroundColor: "#050508",
          backgroundImage: "url('/src/assets/honeycomb-bg.png')",
          backgroundRepeat: "repeat",
          backgroundAttachment: "fixed"
        }}
      ></div>

      <header className="bg-surface-base border-b border-surface-elevated flex justify-between items-center h-16 px-6 w-full z-50 flex-shrink-0 shadow-sm backdrop-blur-md">
        <NavLink to="/" className="flex items-center gap-2 text-2xl font-black tracking-tighter text-text-primary font-hero-display hover:text-accent-electric transition-colors">
          <Shield className="h-6 w-6 text-accent-electric" />
          TruthMates
        </NavLink>
        
        <nav className="hidden md:flex gap-6 text-sm font-medium tracking-wide">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                classNames(
                  "flex items-center gap-2 px-3 py-2 rounded-md transition-colors",
                  isActive
                    ? "bg-primary-container text-accent-electric"
                    : "text-on-surface-variant hover:text-accent-electric hover:bg-surface-elevated"
                )
              }
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="flex-1 flex flex-col min-w-0">
        {children}
      </main>
    </div>
  )
}
