import { CheckCircle, Loader2, PauseCircle } from "lucide-react"

const statusStyles = {
  complete: {
    row: "bg-surface-elevated/30 border-surface-elevated",
    label: "text-text-primary/80",
    icon: "text-success-neon"
  },
  active: {
    row: "bg-surface-elevated border-accent-electric/50 shadow-[0_0_12px_rgba(94,43,255,0.4)]",
    label: "text-accent-electric font-bold",
    icon: "text-accent-electric"
  },
  waiting: {
    row: "bg-transparent border-surface-elevated",
    label: "text-text-primary/60",
    icon: "text-text-primary/40"
  }
}

export default function AgentPipeline({ title = "Pipeline Execution Matrix", steps = [] }) {
  return (
    <div className="bg-surface-base border border-surface-elevated rounded p-4 flex flex-col">
      <div className="flex items-center justify-between mb-4 pb-2 border-b border-surface-elevated">
        <h3 className="font-headline-md text-headline-md text-text-primary">{title}</h3>
        <span className="font-badge-label text-badge-label px-2 py-1 bg-surface-elevated text-success-neon border border-success-neon/30 rounded uppercase flex items-center gap-1">
          <span className="w-1.5 h-1.5 bg-success-neon rounded-full animate-pulse"></span>
          Processing
        </span>
      </div>
      <div className="flex flex-col relative pl-4">
        <div className="absolute left-[7px] top-4 bottom-4 w-[2px] bg-surface-elevated z-0"></div>
        <div className="absolute left-[7px] top-4 h-[45%] w-[2px] bg-accent-electric z-10 shadow-[0_0_12px_rgba(94,43,255,0.5)]"></div>
        <div className="flex flex-col gap-3 relative z-20">
          {steps.map((step) => {
            const styles = statusStyles[step.status] || statusStyles.waiting
            return (
              <div key={step.id} className={`flex items-center gap-4 ${step.status === "waiting" ? "opacity-40" : ""}`}>
                <div className="w-4 h-4 rounded-full bg-background-deep border-2 border-accent-electric flex items-center justify-center relative">
                  {step.status === "active" && (
                    <span className="absolute w-full h-full bg-accent-electric rounded-full opacity-50 animate-ping"></span>
                  )}
                  {step.status !== "waiting" && <span className="w-2 h-2 bg-accent-electric rounded-full"></span>}
                </div>
                <div className={`flex-1 flex justify-between items-center border p-2 rounded ${styles.row}`}>
                  <span className={`font-terminal-log text-terminal-log ${styles.label}`}>{step.label}</span>
                  {step.status === "complete" && <CheckCircle className={`h-4 w-4 ${styles.icon}`} />}
                  {step.status === "active" && <Loader2 className={`h-4 w-4 ${styles.icon} animate-spin`} />}
                  {step.status === "waiting" && <PauseCircle className={`h-4 w-4 ${styles.icon}`} />}
                </div>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
