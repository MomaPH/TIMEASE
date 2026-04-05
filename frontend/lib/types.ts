export interface ChatMessage {
  role: 'user' | 'ai' | 'confirm'
  content: string
  quickReplies?: string[]
  toolCalls?: ToolCall[]
}

export interface ToolCall {
  name: string
  data: Record<string, any>
}

export interface SchoolData {
  name?: string
  city?: string
  academic_year?: string
  days?: string[]
  sessions?: { name: string; start_time: string; end_time: string }[]
  base_unit_minutes?: number
  teachers?: Record<string, any>[]
  classes?: Record<string, any>[]
  rooms?: Record<string, any>[]
  subjects?: Record<string, any>[]
  curriculum?: Record<string, any>[]
  constraints?: Record<string, any>[]
}

export interface TimetableAssignment {
  school_class: string
  subject: string
  teacher: string
  room: string
  day: string
  start_time: string
  end_time: string
  color: string
}
