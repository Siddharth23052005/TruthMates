const defaultLinks = [
  { label: "Architecture", href: "#" },
  { label: "Governance", href: "#" },
  { label: "API Docs", href: "#" },
  { label: "Privacy", href: "#" }
]

const homeLinks = [
  { label: "About", href: "/about" },
  { label: "API Docs", href: "#" },
  { label: "Contact", href: "#" },
  { label: "Privacy", href: "#" }
]

export default function Footer({ variant = "app", links = defaultLinks }) {
  if (variant === "home") {
    return (
      <footer className="w-full py-4 px-8 flex flex-col md:flex-row justify-between items-center gap-3 bg-background-deep border-t border-surface-elevated">
        <div className="text-text-primary/40 font-terminal-log text-[10px] uppercase tracking-widest">
          © 2024 TruthMates. Civic truth infrastructure for India.
        </div>
        <nav className="flex gap-4 font-terminal-log text-[10px] uppercase tracking-widest">
          {homeLinks.map((link) => (
            <a
              key={link.label}
              className="text-text-primary/40 hover:text-accent-electric transition-opacity"
              href={link.href}
            >
              {link.label}
            </a>
          ))}
        </nav>
      </footer>
    )
  }

  return (
    <footer className="flex justify-between items-center px-8 py-3 w-full bg-background-deep border-t border-surface-elevated flex-shrink-0">
      <div className="font-terminal-log text-terminal-log text-text-primary/30 uppercase tracking-widest">
        © 2024 TruthMates. National Security Protocol Active.
      </div>
      <div className="flex gap-6">
        {links.map((link) => (
          <a
            key={link.label}
            className="font-terminal-log text-terminal-log text-text-primary/30 hover:text-text-primary transition-opacity uppercase tracking-widest hover:underline decoration-success-neon underline-offset-4"
            href={link.href}
          >
            {link.label}
          </a>
        ))}
      </div>
    </footer>
  )
}
