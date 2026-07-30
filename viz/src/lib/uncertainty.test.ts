import { describe, it, expect } from 'vitest'
import { uncertaintyAt, chamberTotal, UNCERTAINTY_STOPS } from './uncertainty'

describe('uncertainty accessor', () => {
  it('exposes one payload per turnout stop', () => {
    expect(UNCERTAINTY_STOPS).toHaveLength(7)
  })

  it('returns undefined outside the stop range', () => {
    expect(uncertaintyAt(-1)).toBeUndefined()
    expect(uncertaintyAt(7)).toBeUndefined()
  })

  it('senate modal and observed chambers both total 102 at every stop', () => {
    for (let gi = 0; gi < 7; gi++) {
      const u = uncertaintyAt(gi)!
      for (const m of ['cond', 'irv'] as const) {
        expect(chamberTotal(u.senate[m].seats, 'modal')).toBe(102)
        expect(chamberTotal(u.senate[m].seats, 'observed')).toBe(102)
      }
    }
  })

  it('house modal totals 873 at every stop', () => {
    for (let gi = 0; gi < 7; gi++) {
      expect(chamberTotal(uncertaintyAt(gi)!.house.seats, 'modal')).toBe(873)
    }
  })

  it('expected seats sum to the chamber size', () => {
    const u = uncertaintyAt(1)!
    const sum = Object.values(u.senate.irv.seats).reduce((s, v) => s + v.expected, 0)
    expect(sum).toBeCloseTo(102, 4)
  })

  it('every state distribution sums to 1', () => {
    const u = uncertaintyAt(1)!
    for (const s of Object.values(u.senate.irv.states)) {
      const sum = Object.values(s.dist).reduce((a, b) => a + b, 0)
      expect(sum).toBeCloseTo(1, 3)
    }
  })

  it('substituted states carry a representative run whose winner is the modal party', () => {
    const u = uncertaintyAt(1)!
    for (const s of Object.values(u.senate.irv.states)) {
      if (!s.substituted || !s.repRounds) continue
      const last = s.repRounds[s.repRounds.length - 1].candidates
      const top = [...last].sort((a, b) => b.pct - a.pct)[0]
      expect(top.code.split('_')[0]).toBe(s.modal.split('_')[0])
      for (const rd of s.repRounds) {
        const total = rd.candidates.reduce((a, c) => a + c.pct, 0)
        expect(total).toBeCloseTo(100, 0)
      }
    }
  })
})
