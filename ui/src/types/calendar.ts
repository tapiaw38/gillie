export interface CalendarAttendee {
  email: string
  name?: string
}

export interface CalendarReminder {
  method: string // 'email' | 'popup'
  minutes: number
}

export interface CalendarEvent {
  id: string
  user_id: string
  profile_id: string
  google_id?: string
  title: string
  description?: string
  location?: string
  start_time: string
  end_time: string
  time_zone: string
  attendees?: CalendarAttendee[]
  reminders?: CalendarReminder[]
  status: string
  created_at: string
  updated_at: string
}

export interface CalendarEventInput {
  title: string
  start_time: string
  end_time: string
  description?: string
  location?: string
  attendees?: CalendarAttendee[]
  reminders?: CalendarReminder[]
}

export interface CalendarEventResponse {
  data: CalendarEvent
}

export interface CalendarEventListResponse {
  data: CalendarEvent[]
}

export interface CalendarAuthorizationResponse {
  authorization_url: string
  user_id: string
  profile_id: string
}

export interface CalendarStatusResponse {
  is_active: boolean
  user_id: string
  profile_id: string
}
