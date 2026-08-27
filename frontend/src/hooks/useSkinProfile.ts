import { useCallback, useEffect, useState } from 'react'
import type { SkinProfile } from '../api/types'

const STORAGE_KEY = 'xlb.skin-profile'

export const emptyProfile: SkinProfile = {
  skin_type: 'normal',
  concerns: [],
  sensitive: false,
  acne_prone: false,
  fragrance_free: false,
  budget_max: null,
  categories: [],
}

function read(): SkinProfile | null {
  // Storage can throw outright in private windows and embedded contexts, so
  // every access is guarded rather than merely null-checked.
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY)
    return raw ? ({ ...emptyProfile, ...JSON.parse(raw) } as SkinProfile) : null
  } catch {
    return null
  }
}

/** The skin profile lives in localStorage - there are no user accounts in v1. */
export function useSkinProfile() {
  const [profile, setProfileState] = useState<SkinProfile | null>(() => read())

  useEffect(() => {
    // Keep tabs in sync if the quiz is retaken in another one.
    const onStorage = (event: StorageEvent) => {
      if (event.key === STORAGE_KEY) setProfileState(read())
    }
    window.addEventListener('storage', onStorage)
    return () => window.removeEventListener('storage', onStorage)
  }, [])

  const setProfile = useCallback((next: SkinProfile) => {
    setProfileState(next)
    try {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
    } catch {
      // Non-fatal: the quiz still works for this session.
    }
  }, [])

  const clearProfile = useCallback(() => {
    setProfileState(null)
    try {
      window.localStorage.removeItem(STORAGE_KEY)
    } catch {
      /* ignore */
    }
  }, [])

  return { profile, setProfile, clearProfile, hasProfile: profile !== null }
}
