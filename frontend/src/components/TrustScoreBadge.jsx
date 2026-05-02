const badgeStyles = {
  TRUE: "bg-success-neon/15 text-success-neon border-success-neon",
  FALSE: "bg-danger-bold/15 text-danger-bold border-danger-bold",
  UNVERIFIED: "bg-accent-warm/15 text-accent-warm border-accent-warm",
  MISLEADING: "bg-accent-warm/15 text-accent-warm border-accent-warm",
  INVESTIGATING: "bg-surface-variant text-outline border-outline"
}

export default function TrustScoreBadge({ verdict = "UNVERIFIED", className = "" }) {
  const style = badgeStyles[verdict] || badgeStyles.UNVERIFIED

  return (
    <span
      className={`inline-flex items-center gap-1 px-2 py-1 rounded border font-badge-label text-badge-label uppercase tracking-widest ${style} ${className}`}
    >
      {verdict}
    </span>
  )
}
