import { ChevronDown } from "lucide-react"
import { useEffect, useRef, useState } from "react"
import { useNavigate } from "react-router-dom"
import IntroOverlay from "../components/IntroOverlay"

export default function Home() {
  const videoRef = useRef(null)
  const [opacity, setOpacity] = useState(0)
  const [introFinished, setIntroFinished] = useState(false)
  const navigate = useNavigate()

  useEffect(() => {
    // Check if intro was already seen this session
    const seen = sessionStorage.getItem("intro_seen")
    if (seen) {
      setIntroFinished(true)
    }
  }, [])

  const handleIntroComplete = () => {
    setIntroFinished(true)
    sessionStorage.setItem("intro_seen", "1")
  }

  useEffect(() => {
    const video = videoRef.current
    if (!video) return

    let frameId

    const checkTime = () => {
      if (!video) return
      const t = video.currentTime
      const d = video.duration || 10 // fallback if duration isn't loaded yet
      const fadeTime = 0.5

      if (t < fadeTime) {
        setOpacity(t / fadeTime)
      } else if (d - t < fadeTime) {
        setOpacity(Math.max(0, (d - t) / fadeTime))
      } else {
        setOpacity(1)
      }

      frameId = requestAnimationFrame(checkTime)
    }

    const startLoop = () => {
      frameId = requestAnimationFrame(checkTime)
    }

    const handleEnded = () => {
      setOpacity(0)
      setTimeout(() => {
        if (video) {
          video.currentTime = 0
          video.play().catch(console.error)
        }
      }, 100)
    }

    video.addEventListener("loadedmetadata", startLoop)
    video.addEventListener("ended", handleEnded)

    if (video.readyState >= 1) {
      startLoop()
    }

    video.play().catch(console.error)

    return () => {
      cancelAnimationFrame(frameId)
      if (video) {
        video.removeEventListener("loadedmetadata", startLoop)
        video.removeEventListener("ended", handleEnded)
      }
    }
  }, [])

  const logos = ["Vortex", "Nimbus", "Prysma", "Cirrus", "Kynder", "Halcyn"]
  const marqueeLogos = [...logos, ...logos] // Duplicated for seamless loop

  return (
    <div
      className="min-h-screen flex flex-col font-geist-sans relative overflow-hidden"
      style={{ backgroundColor: "hsl(var(--background))", color: "hsl(var(--foreground))" }}
    >
      {/* Background Video */}
      <div className="absolute inset-0 w-full h-full z-0 overflow-hidden bg-black">
        <video
          ref={videoRef}
          src="https://d8j0ntlcm91z4.cloudfront.net/user_38xzZboKViGWJOttwIXH07lWA1P/hf_20260328_065045_c44942da-53c6-4804-b734-f9e07fc22e08.mp4"
          className="absolute inset-0 w-full h-full object-cover"
          muted
          playsInline
          style={{ opacity, transition: "opacity 0.1s linear" }}
        />
      </div>

      {/* Blurred Overlay Shape */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[984px] h-[527px] opacity-90 bg-gray-950 blur-[82px] pointer-events-none z-0"></div>

      {!introFinished && <IntroOverlay onComplete={handleIntroComplete} />}

      {/* Content wrapper */}
      <div className={`relative z-10 flex flex-col min-h-screen transition-opacity duration-1000 ${introFinished ? "opacity-100" : "opacity-0 pointer-events-none"}`}>
        {/* Hero Main Content */}
        <main className="flex-1 flex flex-col items-center justify-center text-center px-4">
          <h1 className="font-general-sans font-normal text-[120px] md:text-[220px] leading-[1.02] tracking-[-0.024em] whitespace-nowrap">
            <span style={{ color: "hsl(var(--foreground))" }}>Truth </span>
            <span
              className="bg-clip-text text-transparent"
              style={{ backgroundImage: "linear-gradient(to left, #5052e0ff, #5555f7ff, #4dcdfcff)" }}
            >
              Mates 
            </span>
          </h1>
          <p
            className="text-lg leading-8 max-w-md mt-[9px] opacity-80 whitespace-pre-line"
            style={{ color: "hsl(var(--hero-sub))" }}
          >
            {"The most powerful AI ever deployed\nin talent acquisition"}
          </p>
          <button 
            onClick={() => navigate("/analyze")}
            className="bg-[hsl(var(--foreground))]/10 hover:bg-[hsl(var(--foreground))]/20 text-[hsl(var(--foreground))] backdrop-blur-md border border-[hsl(var(--foreground))]/10 transition-colors rounded-full px-[29px] py-[24px] mt-[25px] font-medium text-lg flex items-center justify-center"
          >
            Try it out
          </button>
        </main>
      </div>
    </div>
  )
}
