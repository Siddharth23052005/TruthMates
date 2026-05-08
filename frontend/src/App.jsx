import { Navigate, Route, Routes } from "react-router-dom"
import About from "./pages/About"
import Analyze from "./pages/Analyze"
import CitizenReporter from "./pages/CitizenReporter"
import Home from "./pages/Home"
import RumorHeatmap from "./pages/RumorHeatmap"

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/analyze" element={<Analyze />} />
      <Route path="/rumor-heatmap" element={<RumorHeatmap />} />
      <Route path="/citizen-reporter" element={<CitizenReporter />} />
      <Route path="/about" element={<About />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
