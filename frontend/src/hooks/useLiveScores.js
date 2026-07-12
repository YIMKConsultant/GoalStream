import { useEffect, useState, useRef } from 'react'

export function useLiveScores() {
  const [matches, setMatches] = useState([])
  const wsRef = useRef(null)

  useEffect(() => {
    const protocol = location.protocol === 'https:' ? 'wss' : 'ws'
    const ws = new WebSocket(`${protocol}://${location.host}/ws/live`)
    wsRef.current = ws

    ws.onmessage = (e) => {
      const msg = JSON.parse(e.data)
      if (msg.event === 'live_scores') setMatches(msg.data)
    }

    const ping = setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) ws.send('ping')
    }, 25000)

    return () => {
      clearInterval(ping)
      ws.close()
    }
  }, [])

  return matches
}
