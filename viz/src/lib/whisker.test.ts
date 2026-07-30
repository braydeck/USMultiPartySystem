import { describe, it, expect } from 'vitest'
import { whiskerGeometry, rangeAxisMax } from './whisker'

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

describe('rangeAxisMax', () => {
  it('uses an explicit shared max when one is given', () => {
    expect(rangeAxisMax([4, 9], 40)).toBe(40)
  })
  it('honours a shared max below the largest hi, so siblings stay on one scale', () => {
    expect(rangeAxisMax([4, 60], 40)).toBe(40)
  })
  it('falls back to the largest hi when no max is given', () => {
    expect(rangeAxisMax([4, 9, 2])).toBe(9)
  })
  it('floors the fallback at 1 for an all-zero or empty strip', () => {
    expect(rangeAxisMax([0, 0])).toBe(1)
    expect(rangeAxisMax([])).toBe(1)
  })
})
