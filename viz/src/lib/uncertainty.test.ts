import { describe, it, expect } from 'vitest'
import { uncertaintyAt, chamberTotal, UNCERTAINTY_STOPS, SHARE_RANGES, VOTE_STOP_KEYS, populationShares, voteSharesAt } from './uncertainty'

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
    let checked = 0
    for (const s of Object.values(u.senate.irv.states)) {
      if (!s.substituted || !s.repRounds) continue
      checked++
      const last = s.repRounds[s.repRounds.length - 1].candidates
      const top = [...last].sort((a, b) => b.pct - a.pct)[0]
      expect(top.code.split('_')[0]).toBe(s.modal.split('_')[0])
      for (const rd of s.repRounds) {
        const total = rd.candidates.reduce((a, c) => a + c.pct, 0)
        expect(total).toBeCloseTo(100, 0)
      }
    }
    // Without this the loop would pass vacuously if a data regeneration ever produced
    // no substituted states, silently dropping all coverage here.
    expect(checked).toBe(u.senate.irv.nSubstituted)
    expect(checked).toBeGreaterThan(0)
  })

  it('every payload carries the fields the types promise', () => {
    // The JSON is loaded through `as unknown as`, so tsc cannot catch a regeneration that
    // drops or renames a field. This is the only guard against that drift.
    for (let gi = 0; gi < 7; gi++) {
      const u = uncertaintyAt(gi)!
      expect(typeof u.nDraws).toBe('number')
      expect(typeof u.seed).toBe('number')
      for (const m of ['cond', 'irv'] as const) {
        const mu = u.senate[m]
        expect(typeof mu.nSubstituted).toBe('number')
        expect(typeof mu.nBelow50).toBe('number')
        for (const v of Object.values(mu.seats)) {
          for (const k of ['modal', 'expected', 'lo', 'hi', 'observed'] as const) {
            expect(typeof v[k]).toBe('number')
          }
        }
        for (const s of Object.values(mu.states)) {
          expect(typeof s.observed).toBe('string')
          expect(typeof s.modal).toBe('string')
          expect(typeof s.pModal).toBe('number')
          expect(typeof s.pObserved).toBe('number')
          expect(typeof s.substituted).toBe('boolean')
        }
      }
      for (const m of ['irv', 'cond'] as const) {
        expect(typeof u.president[m].nResolved).toBe('number')
        expect(typeof u.president[m].modal).toBe('string')
      }
      expect(Array.isArray(u.primary.observedSlate)).toBe(true)
    }
  })
})

describe('share ranges', () => {
  // One population block plus one vote block per turnout stop.
  const blocks = () => [
    ['population', populationShares()] as const,
    ...VOTE_STOP_KEYS.map((k, gi) => [`votes.${k}`, voteSharesAt(gi)!] as const),
  ]

  it('carries eight blocks: one population, seven vote stops', () => {
    expect(blocks()).toHaveLength(8)
    expect(Object.keys(SHARE_RANGES.votes)).toHaveLength(7)
    expect(voteSharesAt(-1)).toBeUndefined()
    expect(voteSharesAt(7)).toBeUndefined()
  })

  it('covers all ten parties and totals 100% in every block', () => {
    for (const [label, shares] of blocks()) {
      expect(Object.keys(shares), label).toHaveLength(10)
      for (const k of ['point', 'expected'] as const) {
        const sum = Object.values(shares).reduce((s, v) => s + v[k], 0)
        expect(sum, `${label}.${k}`).toBeCloseTo(100, 1)
      }
    }
  })

  it('brackets every expected share inside its own bounds', () => {
    for (const [label, shares] of blocks()) {
      for (const [code, iv] of Object.entries(shares)) {
        expect(iv.lo, `${label}.${code}`).toBeLessThanOrEqual(iv.expected)
        expect(iv.expected, `${label}.${code}`).toBeLessThanOrEqual(iv.hi)
        for (const k of ['point', 'expected', 'lo', 'hi'] as const) {
          expect(typeof iv[k], `${label}.${code}.${k}`).toBe('number')
        }
      }
    }
  })

  it('keeps population stop-invariant while votes are keyed by stop', () => {
    expect(SHARE_RANGES.population.stopInvariant).toBe(true)
    expect(SHARE_RANGES.nDraws).toBe(1000)
    // Turnout weighting has to bite somewhere, or the votes blocks are silently population.
    const first = voteSharesAt(0)!, last = voteSharesAt(6)!
    expect(first.STY.point).not.toBeCloseTo(last.STY.point, 2)
    expect(first.STY.point).not.toBeCloseTo(populationShares().STY.point, 2)
  })
})
