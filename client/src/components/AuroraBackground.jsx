import { useEffect, useRef } from 'react'

export function AuroraBackground() {
  const canvasRef = useRef(null)

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    let animId
    let t = 0

    // Stars/dust particles
    const stars = Array.from({ length: 60 }).map(() => ({
      x: Math.random(),
      y: Math.random(),
      radius: Math.random() * 1.2 + 0.3,
      alpha: Math.random() * 0.7 + 0.2,
      speed: Math.random() * 0.0005 + 0.0002,
    }))

    const resize = () => {
      canvas.width = window.innerWidth
      canvas.height = window.innerHeight
    }

    resize()
    window.addEventListener('resize', resize)

    const render = () => {
      ctx.clearRect(0, 0, canvas.width, canvas.height)
      const w = canvas.width
      const h = canvas.height

      // Deep celestial gradient base
      const bgGrad = ctx.createLinearGradient(0, 0, 0, h)
      bgGrad.addColorStop(0, '#030812')
      bgGrad.addColorStop(0.5, '#061224')
      bgGrad.addColorStop(1, '#02050b')
      ctx.fillStyle = bgGrad
      ctx.fillRect(0, 0, w, h)

      // Render stars
      for (const s of stars) {
        ctx.beginPath()
        ctx.arc(s.x * w, s.y * h, s.radius, 0, Math.PI * 2)
        const twinkle = Math.sin(t * 1.5 + s.x * 100) * 0.3 + 0.7
        ctx.fillStyle = `rgba(224, 242, 254, ${s.alpha * twinkle})`
        ctx.fill()
        s.y -= s.speed
        if (s.y < 0) s.y = 1
      }

      // Draw multi-layered Aurora ribbons
      const drawAuroraWave = (baseY, amplitude, freq, speed, colorStops) => {
        ctx.save()
        ctx.beginPath()
        ctx.moveTo(0, h)

        for (let x = 0; x <= w; x += 12) {
          const wave1 = Math.sin((x * freq) + (t * speed)) * amplitude
          const wave2 = Math.cos((x * freq * 0.6) - (t * speed * 0.7)) * (amplitude * 0.5)
          const wave3 = Math.sin((x * 0.002) + (t * 0.001)) * 30
          const y = baseY + wave1 + wave2 + wave3
          ctx.lineTo(x, y)
        }

        ctx.lineTo(w, h)
        ctx.closePath()

        const grad = ctx.createLinearGradient(0, baseY - amplitude * 1.5, 0, h)
        for (const [stop, color] of colorStops) {
          grad.addColorStop(stop, color)
        }

        ctx.fillStyle = grad
        ctx.fill()
        ctx.restore()
      }

      // Layer 1: Deep Indigo / Violet Backing
      drawAuroraWave(h * 0.38, 90, 0.0018, 0.0008, [
        [0, 'rgba(99, 102, 241, 0.22)'],
        [0.4, 'rgba(139, 92, 246, 0.15)'],
        [0.8, 'rgba(15, 23, 42, 0.05)'],
        [1, 'transparent']
      ])

      // Layer 2: Emerald Green Mid Ribbon (Classic Aurora)
      drawAuroraWave(h * 0.28, 110, 0.0022, 0.0012, [
        [0, 'rgba(16, 185, 129, 0.28)'],
        [0.3, 'rgba(52, 211, 153, 0.22)'],
        [0.7, 'rgba(6, 182, 212, 0.12)'],
        [1, 'transparent']
      ])

      // Layer 3: Electric Cyan Foreground Wave
      drawAuroraWave(h * 0.22, 80, 0.003, 0.0016, [
        [0, 'rgba(6, 182, 212, 0.35)'],
        [0.35, 'rgba(56, 189, 248, 0.25)'],
        [0.75, 'rgba(16, 185, 129, 0.08)'],
        [1, 'transparent']
      ])

      t += 1
      animId = requestAnimationFrame(render)
    }

    render()

    return () => {
      window.removeEventListener('resize', resize)
      cancelAnimationFrame(animId)
    }
  }, [])

  return (
    <canvas
      ref={canvasRef}
      style={{
        position: 'fixed',
        top: 0,
        left: 0,
        width: '100vw',
        height: '100vh',
        pointerEvents: 'none',
        zIndex: 0,
      }}
    />
  )
}
