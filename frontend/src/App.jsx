import { Navigate, Route, Routes } from "react-router-dom"
import About from "./pages/About"
import Analyze from "./pages/Analyze"
import CitizenReporter from "./pages/CitizenReporter"
import Home from "./pages/Home"
import MonitorDashboard from "./pages/MonitorDashboard"
import SocialMonitor from "./pages/SocialMonitor"
import Trending from "./pages/Trending"

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/analyze" element={<Analyze />} />
      <Route path="/trending" element={<Trending />} />
      <Route path="/citizen-reporter" element={<CitizenReporter />} />
      <Route path="/social-monitor" element={<SocialMonitor />} />
      <Route path="/monitor" element={<MonitorDashboard />} />
      <Route path="/about" element={<About />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
