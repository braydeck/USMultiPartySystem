import { describe, it, expect } from 'vitest'
import { layoutSeatDots, type ParliamentSegment } from './parliamentLayout'

const seg = (code: string, seats: number, fVal: number): ParliamentSegment =>
  ({ code, seats, fVal })

const dotCounts = (segments: ParliamentSegment[]) => {
  const { groupedDots } = layoutSeatDots(segments)
  return Object.fromEntries(
    Object.entries(groupedDots).map(([code, dots]) => [code, dots.length]),
  )
}

describe('layoutSeatDots', () => {
  // The regression this guards: dots used to be assigned by the angle they landed at,
  // so the 102-seat senate drew 11 LIB and 5 POP for parties holding 8 and 2 seats.
  it('draws exactly one dot per seat for the 102-seat senate', () => {
    const senate = [
      seg('LIB_1', 8, -1.16), seg('LBR_1', 42, -0.5), seg('STY_1', 2, 0.0),
      seg('CON_1', 48, 0.8), seg('POP_1', 2, 1.51),
    ]
    expect(dotCounts(senate)).toEqual({
      LIB_1: 8, LBR_1: 42, STY_1: 2, CON_1: 48, POP_1: 2,
    })
  })

  it('draws exactly one dot per seat for a 435-seat house', () => {
    const house = [
      seg('PRG', 21, -2), seg('DSA', 34, -1.5), seg('LBR', 96, -1),
      seg('LIB', 58, -0.2), seg('STY', 40, 0.1), seg('CUP', 47, 0.6),
      seg('CON', 88, 1.2), seg('NAT', 30, 1.8), seg('POP', 21, 2.2),
    ]
    const counts = dotCounts(house)
    for (const s of house) expect(counts[s.code]).toBe(s.seats)
  })

  it('never drops a party holding a single seat', () => {
    const segments = [
      seg('A', 1, -2), seg('B', 99, 0), seg('C', 1, 2),
    ]
    expect(dotCounts(segments)).toEqual({ A: 1, B: 99, C: 1 })
  })

  it('totals dots to total seats across a range of chamber sizes', () => {
    for (const total of [3, 7, 51, 102, 200, 435]) {
      const segments = [seg('X', 1, -1), seg('Y', total - 2, 0), seg('Z', 1, 1)]
      const { groupedDots } = layoutSeatDots(segments)
      const sum = Object.values(groupedDots).reduce((n, d) => n + d.length, 0)
      expect(sum).toBe(total)
    }
  })

  it('keeps each party wedge contiguous in angular order', () => {
    const segments = [seg('L', 20, -1), seg('M', 30, 0), seg('R', 20, 1)]
    const { groupedDots } = layoutSeatDots(segments)
    // cx runs left (negative) to right (positive) as fVal ascends, so each party's
    // maximum cx must not exceed the next party's minimum by more than a ring's width.
    const maxCx = (c: string) => Math.max(...groupedDots[c].map(d => d.cx))
    const minCx = (c: string) => Math.min(...groupedDots[c].map(d => d.cx))
    expect(minCx('L')).toBeLessThan(minCx('M'))
    expect(maxCx('M')).toBeLessThan(maxCx('R'))
  })

  it('returns no dots for an empty chamber', () => {
    expect(layoutSeatDots([])).toEqual({ groupedDots: {}, nRings: 3, dotSize: 4 })
  })
})
