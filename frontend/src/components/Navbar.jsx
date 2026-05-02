import { NavLink } from "react-router-dom"
import {
  Bell,
  Globe,
  Info,
  LayoutDashboard,
  Map,
  MessageCircle,
  Mic,
  Moon,
  Network,
  Search,
  SearchCheck,
  UserCircle
} from "lucide-react"

const navItems = [
  { label: "Analyze", to: "/analyze", icon: SearchCheck },
  { label: "Dashboard", to: "/dashboard", icon: LayoutDashboard },
  { label: "Rumor Heatmap", to: "/rumor-heatmap", icon: Map },
  { label: "Propagation Graph", to: "/propagation-graph", icon: Network },
  { label: "Citizen Reporter", to: "/citizen-reporter", icon: Mic },
  { label: "WhatsApp Bot", to: "/whatsapp-bot", icon: MessageCircle },
  { label: "About", to: "/about", icon: Info }
]

function classNames(...classes) {
  return classes.filter(Boolean).join(" ")
}

export default function Navbar({
  children,
  topSearchPlaceholder = "Search past claims...",
  showTopSearch = true,
  topNavLinks = []
}) {
  return (
    <div className="flex min-h-screen bg-background-deep text-text-primary">
      <aside className="hidden md:flex flex-col h-screen py-4 gap-2 bg-surface-base border-r border-surface-elevated w-sidebar-width flex-shrink-0 sticky top-0">
        <div className="px-6 mb-8 mt-2">
          <div className="text-lg font-black text-accent-electric font-hero-display tracking-tighter uppercase">
            Control Room
          </div>
          <div className="text-accent-electric/70 font-badge-label text-badge-label mt-1 flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-success-neon animate-pulse shadow-[0_0_8px_rgba(0,245,160,0.6)]"></span>
            System Active
          </div>
        </div>
        <nav className="flex-1 overflow-y-auto">
          {navItems.map((item) => {
            const Icon = item.icon
            return (
              <NavLink
                key={item.to}
                to={item.to}
                className={({ isActive }) =>
                  classNames(
                    "flex items-center gap-3 px-6 py-3 border-l-4 font-body-sm text-body-sm font-medium tracking-wide uppercase transition-all duration-150",
                    isActive
                      ? "bg-surface-elevated text-accent-electric border-accent-electric"
                      : "text-text-primary/40 hover:text-text-primary hover:bg-surface-elevated/50 border-transparent"
                  )
                }
              >
                {({ isActive }) => (
                  <>
                    <Icon className="h-4 w-4" aria-hidden="true" />
                    {item.label}
                    {isActive && (
                      <span className="ml-auto w-1.5 h-1.5 rounded-full bg-accent-electric animate-pulse"></span>
                    )}
                  </>
                )}
              </NavLink>
            )
          })}
        </nav>
        <div className="mt-auto px-6 pb-4">
          <div className="h-px w-full bg-surface-elevated mb-4"></div>
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-full bg-surface-elevated flex items-center justify-center">
              <UserCircle className="h-5 w-5 text-on-surface-variant" />
            </div>
            <div>
              <div className="text-sm font-medium text-text-primary">Ayesha Kumar</div>
              <div className="text-[10px] font-badge-label text-accent-electric uppercase tracking-widest">
                Citizen Reporter
              </div>
            </div>
          </div>
        </div>
      </aside>

      <div className="flex-1 flex flex-col min-w-0">
        <header className="bg-background-deep border-b border-surface-elevated flex justify-between items-center h-14 px-6 w-full z-50 flex-shrink-0">
          <div className="md:hidden text-xl font-black tracking-tighter text-text-primary font-hero-display">
            TruthMates
          </div>
          {topNavLinks.length > 0 && (
            <nav className="hidden md:flex gap-4 text-xs font-bold uppercase tracking-widest text-text-primary/60">
              {topNavLinks.map((link) => (
                <NavLink
                  key={link.to}
                  to={link.to}
                  className={({ isActive }) =>
                    classNames(
                      "px-2 py-1 transition-colors",
                      isActive
                        ? "text-accent-electric border-b-2 border-accent-electric"
                        : "hover:text-accent-electric hover:bg-surface-elevated/40"
                    )
                  }
                >
                  {link.label}
                </NavLink>
              ))}
            </nav>
          )}
          {showTopSearch && (
            <div className="hidden md:flex items-center bg-surface-base border border-surface-elevated rounded px-3 py-1.5 focus-within:border-accent-electric transition-colors">
              <Search className="h-4 w-4 text-text-primary/50 mr-2" />
              <input
                className="bg-transparent border-none outline-none text-body-sm font-body-sm text-text-primary placeholder:text-text-primary/30 w-56 focus:ring-0 p-0"
                placeholder={topSearchPlaceholder}
                type="text"
              />
            </div>
          )}
          <div className="flex items-center gap-3 text-text-primary/60">
            <button className="p-2 hover:bg-surface-elevated hover:text-accent-electric transition-colors rounded relative">
              <Bell className="h-4 w-4" />
              <span className="absolute top-1 right-1 w-2 h-2 bg-danger-bold rounded-full"></span>
            </button>
            <button className="p-2 hover:bg-surface-elevated hover:text-accent-electric transition-colors rounded">
              <Globe className="h-4 w-4" />
            </button>
            <div className="hidden lg:flex items-center gap-2 text-[10px] font-badge-label uppercase tracking-widest text-text-primary/60">
              <span className="text-text-primary">EN</span>
              <span>|</span>
              <span>HI</span>
              <span>|</span>
              <span>MR</span>
            </div>
            <button className="p-2 hover:bg-surface-elevated hover:text-accent-electric transition-colors rounded">
              <Moon className="h-4 w-4" />
            </button>
          </div>
        </header>
        {children}
      </div>
    </div>
  )
}
