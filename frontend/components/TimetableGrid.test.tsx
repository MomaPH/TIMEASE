import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'

import TimetableGrid from '@/components/TimetableGrid'
import type { TimetableAssignment } from '@/lib/types'

const ASSIGNMENTS: TimetableAssignment[] = [
  {
    school_class: '6e',
    subject: 'MATH',
    teacher: 'T_DIAW_YAHYA',
    room: 'R_CLASS_1',
    day: 'lundi',
    start_time: '08:00',
    end_time: '08:30',
    color: '#0d9488',
  },
  {
    school_class: '6e',
    subject: 'FR',
    teacher: 'T_BA',
    room: 'R_CLASS_1',
    day: 'mardi',
    start_time: '08:00',
    end_time: '08:30',
    color: '#2563eb',
  },
]

describe('TimetableGrid break rendering', () => {
  it('renders breaks only on the days where they exist', () => {
    render(
      <TimetableGrid
        assignments={ASSIGNMENTS}
        days={['lundi', 'mardi']}
        view="class"
        breaks={[
          { type: 'break', day: 'lundi', start_time: '10:00', end_time: '10:10', label: 'Récréation' },
        ]}
      />
    )

    const breakCells = screen.getAllByText('Récréation')
    expect(breakCells).toHaveLength(1)
  })
})

