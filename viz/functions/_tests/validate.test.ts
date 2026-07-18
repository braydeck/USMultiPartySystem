import { describe, it, expect } from 'vitest'
import { validateCreate, validateVibe } from '../api/_lib/validate'

const goodCreate = {
  id: '123e4567-e89b-12d3-a456-426614174000',
  result_party: 'LBR',
  answers: { CC24_321d: 1 },
  scores: [{ party: 'LBR', prob: 0.6 }],
  referrer: 'https://braydendecker.substack.com/',
  quiz_version: 'v1-2026-07',
}

describe('validateCreate', () => {
  it('accepts a well-formed payload', () => {
    const r = validateCreate(goodCreate)
    expect(r.ok).toBe(true)
  })
  it('rejects an unknown party', () => {
    expect(validateCreate({ ...goodCreate, result_party: 'ZZZ' }).ok).toBe(false)
  })
  it('rejects a non-uuid id', () => {
    expect(validateCreate({ ...goodCreate, id: 'nope' }).ok).toBe(false)
  })
  it('rejects empty answers', () => {
    expect(validateCreate({ ...goodCreate, answers: {} }).ok).toBe(false)
  })
  it('rejects a non-numeric answer value', () => {
    expect(validateCreate({ ...goodCreate, answers: { CC24_321d: 'x' } }).ok).toBe(false)
  })
  it('rejects too many answers', () => {
    const answers: Record<string, number> = {}
    for (let i = 0; i < 51; i++) answers['q' + i] = 1
    expect(validateCreate({ ...goodCreate, answers }).ok).toBe(false)
  })
  it('rejects a missing quiz_version', () => {
    const { quiz_version, ...rest } = goodCreate
    expect(validateCreate(rest).ok).toBe(false)
  })
  it('defaults a missing referrer to null', () => {
    const { referrer, ...rest } = goodCreate
    const r = validateCreate(rest)
    expect(r.ok && r.value.referrer).toBe(null)
  })
})

describe('validateVibe', () => {
  it('accepts fit', () => {
    expect(validateVibe({ id: goodCreate.id, vibe: 'fit' }).ok).toBe(true)
  })
  it('accepts miss', () => {
    expect(validateVibe({ id: goodCreate.id, vibe: 'miss' }).ok).toBe(true)
  })
  it('rejects any other vibe', () => {
    expect(validateVibe({ id: goodCreate.id, vibe: 'maybe' }).ok).toBe(false)
  })
  it('rejects a bad id', () => {
    expect(validateVibe({ id: 'nope', vibe: 'fit' }).ok).toBe(false)
  })
})
