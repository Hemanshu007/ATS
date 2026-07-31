import type { ApplicationStatus } from '../types/application'

// Mirrors app/core/constants.py ALLOWED_STATUS_TRANSITIONS — kept in sync manually.
export const ALLOWED_STATUS_TRANSITIONS: Record<ApplicationStatus, ApplicationStatus[]> = {
  applied: ['screening', 'rejected'],
  screening: ['interview', 'rejected'],
  interview: ['offer', 'rejected'],
  offer: ['hired', 'rejected'],
  hired: [],
  rejected: [],
}
