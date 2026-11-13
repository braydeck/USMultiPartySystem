import { describe, it, expect } from 'vitest'
import { parseDissolve, dissolveKey, partyList } from './dissolve'

describe('dissolve selection', () => {
  it('normalizes order, accepts either separator, drops unknown codes', () => {
    expect(parseDissolve('NAT,dsa,XYZ')).toEqual(['DSA', 'NAT'])
    expect(dissolveKey(parseDissolve('LP-NAT'))).toBe('LP-NAT')
  })

  it('refuses to dissolve every party', () => {
    expect(parseDissolve('DSA-PRG-LBR-CUP-STY-OAO-CON-LP-NAT')).toEqual([])
  })

  it('names parties with the serial comma', () => {
    expect(partyList(['LBR', 'LP', 'NAT'])).toBe('Labor, Libertarian, and Nationalist')
  })
})
