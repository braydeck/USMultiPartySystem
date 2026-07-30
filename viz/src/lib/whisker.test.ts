import { describe, it, expect } from 'vitest'
import { whiskerGeometry } from './whisker'

describe('whiskerGeometry', () => {
  it('maps values onto percentages of the axis', () => {
    expect(whiskerGeometry(20, 40, 30, 100)).toEqual({ leftPct: 20, widthPct: 20, centrePct: 30 })
  })
  it('scales to a non-100 axis maximum', () => {
    expect(whiskerGeometry(10, 20, 15, 50)).toEqual({ leftPct: 20, widthPct: 20, centrePct: 30 })
  })
  it('returns null for a degenerate axis', () => {
    expect(whiskerGeometry(1, 2, 1.5, 0)).toBeNull()
  })
  it('returns null when the interval has no width', () => {
    expect(whiskerGeometry(5, 5, 5, 100)).toBeNull()
  })
  it('clamps to the axis so it cannot overflow the track', () => {
    const g = whiskerGeometry(-10, 120, 50, 100)!
    expect(g.leftPct).toBe(0)
    expect(g.leftPct + g.widthPct).toBeLessThanOrEqual(100)
  })
})
