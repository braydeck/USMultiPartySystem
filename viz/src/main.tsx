import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'
import { initAnalytics, mountViewStateTracking, trackShareLanding } from './utils/analytics'

initAnalytics()
mountViewStateTracking()
trackShareLanding()

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
