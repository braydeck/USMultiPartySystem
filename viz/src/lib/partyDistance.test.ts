import { describe, it, expect } from 'vitest'
import { factorDistance, policyDivergence, DISTANCE_FACTORS } from './partyDistance'

const eta = { F1: 0.25, F2: 0.20, F3: 0.10, F4: 0.15, F5: 0.40 }

describe('factorDistance', () => {
  it('is zero for identical vectors', () => {
    const a = { z_F1: 1, z_F2: -1, z_F4: 0.5, z_F5: 2 }
    expect(factorDistance(a, a, eta)).toBe(0)
  })
  it('ignores F3 (not in DISTANCE_FACTORS)', () => {
    const a = { z_F1: 0, z_F2: 0, z_F3: 0, z_F4: 0, z_F5: 0 }
    const b = { z_F1: 0, z_F2: 0, z_F3: 99, z_F4: 0, z_F5: 0 }
    expect(factorDistance(a, b, eta)).toBe(0)
    expect(DISTANCE_FACTORS).not.toContain('F3')
  })
  it('returns a weighted RMS in sigma units', () => {
    const a = { z_F1: 0, z_F2: 0, z_F4: 0, z_F5: 0 }
    const b = { z_F1: 0, z_F2: 0, z_F4: 0, z_F5: 1 }
    // only F5 differs by 1sigma; weighted RMS = sqrt(w5*1 / (w1+w2+w4+w5))
    const w = eta.F5 / (eta.F1 + eta.F2 + eta.F4 + eta.F5)
    expect(factorDistance(a, b, eta)).toBeCloseTo(Math.sqrt(w), 6)
  })
})

describe('policyDivergence', () => {
  it('averages per-item distances', () => {
    expect(policyDivergence([10, 20, 30])).toBeCloseTo(20, 6)
  })
  it('is zero for no items', () => {
    expect(policyDivergence([])).toBe(0)
  })
})
