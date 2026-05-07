import { Navigate, Route, Routes } from "react-router-dom"
import IntroScreen from "./components/IntroScreen"
import About from "./pages/About"
import Analyze from "./pages/Analyze"
import CitizenReporter from "./pages/CitizenReporter"
import Dashboard from "./pages/Dashboard"
import Home from "./pages/Home"
import PropagationGraph from "./pages/PropagationGraph"
import RumorHeatmap from "./pages/RumorHeatmap"
import WhatsAppBot from "./pages/WhatsAppBot"

export default function App() {
  return (
    <IntroScreen>
      <Routes>
        <Route path="/" element={<Home />} />
        <Route path="/analyze" element={<Analyze />} />
        <Route path="/dashboard" element={<Dashboard />} />
        <Route path="/rumor-heatmap" element={<RumorHeatmap />} />
        <Route path="/propagation-graph" element={<PropagationGraph />} />
        <Route path="/citizen-reporter" element={<CitizenReporter />} />
        <Route path="/whatsapp-bot" element={<WhatsAppBot />} />
        <Route path="/about" element={<About />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </IntroScreen>
  )
}
