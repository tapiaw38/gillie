import { server } from '@/api/request/server'
import { CalendarService } from './calendarService'

const BASE_URL = import.meta.env.VITE_CALENDAR_BASE_URL || 'http://localhost:8000'

export const calendarService = new CalendarService(server({ baseURL: BASE_URL }))

export { CalendarService }
export type { ICalendarService } from './calendarService'
