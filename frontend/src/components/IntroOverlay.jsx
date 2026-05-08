import { AnimatePresence, motion } from "framer-motion"
import { useEffect, useState } from "react"

const OPEN_MS = 600
const WORD_FADE_MS = 500
const WORD_HOLD_MS = 1500
const WORD_OUT_MS = 500
const TYPE1_MS = 2200
const HINDI_FADE_MS = 500
const LINES_HOLD_MS = 2000
const GLITCH_MS = 500
const SHATTER_MS = 700
const TYPE2_MS = 1800
const FINAL_HOLD_MS = 1500

const FIRST_LINE = "Every 15 minutes, a lie goes viral."
const FIRST_LINE_HI = "हर 15 मिनट में, एक झूठ वायरल होता है।"
const FINAL_LINE = "We built something to fight back."

export default function IntroOverlay({ onComplete }) {
  const [showWord, setShowWord] = useState(false)
  const [showFirstLines, setShowFirstLines] = useState(false)
  const [showHindi, setShowHindi] = useState(false)
  const [glitchActive, setGlitchActive] = useState(false)
  const [shatterActive, setShatterActive] = useState(false)
  const [showFinalLine, setShowFinalLine] = useState(false)

  useEffect(() => {
    const timeouts = []
    let elapsed = 0
    const schedule = (callback, delay) => {
      const id = window.setTimeout(callback, delay)
      timeouts.push(id)
    }

    elapsed += OPEN_MS
    schedule(() => setShowWord(true), elapsed)

    elapsed += WORD_FADE_MS + WORD_HOLD_MS
    schedule(() => setShowWord(false), elapsed)

    elapsed += WORD_OUT_MS
    schedule(() => setShowFirstLines(true), elapsed)

    elapsed += TYPE1_MS
    schedule(() => setShowHindi(true), elapsed)

    elapsed += HINDI_FADE_MS + LINES_HOLD_MS
    schedule(() => setGlitchActive(true), elapsed)

    elapsed += GLITCH_MS
    schedule(() => {
      setGlitchActive(false)
      setShatterActive(true)
    }, elapsed)

    elapsed += SHATTER_MS
    schedule(() => {
      setShowFirstLines(false)
      setShowHindi(false)
      setShatterActive(false)
      setShowFinalLine(true)
    }, elapsed)

    elapsed += TYPE2_MS + FINAL_HOLD_MS
    schedule(() => {
      setShowFinalLine(false)
    }, elapsed)

    elapsed += 500
    schedule(() => {
      onComplete()
    }, elapsed)

    return () => {
      timeouts.forEach((id) => window.clearTimeout(id))
    }
  }, [onComplete])

  return (
    <div className="absolute inset-0 z-50 flex items-center justify-center pointer-events-none">
      {/* Pitch black background specifically for the intro text to stand out */}
      <div className="absolute inset-0 bg-black"></div>

      <div className="absolute inset-0 flex items-center justify-center px-6 z-10">
        <AnimatePresence>
          {showWord && (
            <motion.div
              key="word"
              className="text-5xl sm:text-6xl lg:text-7xl font-headline-lg text-white"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: WORD_FADE_MS / 1000 }}
            >
              सच?
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <div className="absolute inset-0 flex items-center justify-center px-6 z-10">
        {showFirstLines && (
          <motion.div
            key="first-lines"
            className={`flex flex-col items-center gap-4 text-center max-w-[90vw] ${
              glitchActive ? "intro-glitch-active" : ""
            } ${shatterActive ? "intro-shatter-active" : ""}`}
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.4 }}
          >
            <div
              className="intro-typing intro-glitch-text intro-shatter-text text-3xl sm:text-4xl lg:text-5xl font-headline-lg text-white"
              style={{
                "--typing-steps": FIRST_LINE.length,
                "--typing-duration": `${TYPE1_MS}ms`,
                "--typing-width": `${FIRST_LINE.length}ch`
              }}
              data-text={FIRST_LINE}
            >
              {FIRST_LINE}
            </div>
            {showHindi && (
              <motion.div
                key="first-line-hi"
                className="intro-glitch-text intro-shatter-text text-base sm:text-lg font-body-base text-white/70"
                data-text={FIRST_LINE_HI}
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ duration: HINDI_FADE_MS / 1000 }}
              >
                {FIRST_LINE_HI}
              </motion.div>
            )}
          </motion.div>
        )}
      </div>

      <div className="absolute inset-0 flex items-center justify-center px-6 z-10">
        <AnimatePresence>
          {showFinalLine && (
            <motion.div
              key="final-line"
              className="text-center max-w-[90vw]"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              transition={{ duration: 0.4 }}
            >
              <div
                className="intro-typing intro-glitch-text text-3xl sm:text-4xl lg:text-5xl font-headline-lg text-white"
                style={{
                  "--typing-steps": FINAL_LINE.length,
                  "--typing-duration": `${TYPE2_MS}ms`,
                  "--typing-width": `${FINAL_LINE.length}ch`
                }}
                data-text={FINAL_LINE}
              >
                {FINAL_LINE}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  )
}
