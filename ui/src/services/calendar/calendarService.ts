import type { AxiosInstance } from 'axios'
import type {
  CalendarEventInput,
  CalendarEventResponse,
  CalendarEventListResponse,
  CalendarAuthorizationResponse,
  CalendarStatusResponse,
} from '@/types/calendar'

export interface ICalendarService {
  getAuthorizationUrl(profileId?: string): Promise<CalendarAuthorizationResponse>
  checkStatus(profileId?: string): Promise<CalendarStatusResponse>
  createEvent(event: CalendarEventInput, profileId?: string): Promise<CalendarEventResponse>
  listEvents(
    profileId?: string,
    startDate?: string,
    endDate?: string,
    limit?: number,
  ): Promise<CalendarEventListResponse>
  updateEvent(
    eventId: string,
    event: CalendarEventInput,
    profileId?: string,
  ): Promise<CalendarEventResponse>
  deleteEvent(eventId: string, profileId?: string): Promise<void>
}

export class CalendarService implements ICalendarService {
  constructor(private readonly api: AxiosInstance) {
    this.api = api
  }

  async getAuthorizationUrl(profileId?: string): Promise<CalendarAuthorizationResponse> {
    const params = profileId ? { profile_id: profileId } : {}
    const { data } = await this.api.get<CalendarAuthorizationResponse>(
      '/calendar/authorize',
      { params },
    )
    return data
  }

  async checkStatus(profileId?: string): Promise<CalendarStatusResponse> {
    const params = profileId ? { profile_id: profileId } : {}
    const { data } = await this.api.get<CalendarStatusResponse>('/calendar/status', { params })
    return data
  }

  async createEvent(
    event: CalendarEventInput,
    profileId?: string,
  ): Promise<CalendarEventResponse> {
    const params = profileId ? { profile_id: profileId } : {}
    const { data } = await this.api.post<CalendarEventResponse>('/calendar/events', event, {
      params,
    })
    return data
  }

  async listEvents(
    profileId?: string,
    startDate?: string,
    endDate?: string,
    limit: number = 50,
  ): Promise<CalendarEventListResponse> {
    const params: Record<string, string | number> = { limit }
    if (profileId) params.profile_id = profileId
    if (startDate) params.start_date = startDate
    if (endDate) params.end_date = endDate

    const { data } = await this.api.get<CalendarEventListResponse>('/calendar/events', {
      params,
    })
    return data
  }

  async updateEvent(
    eventId: string,
    event: CalendarEventInput,
    profileId?: string,
  ): Promise<CalendarEventResponse> {
    const params = profileId ? { profile_id: profileId } : {}
    const { data } = await this.api.put<CalendarEventResponse>(
      `/calendar/events/${eventId}`,
      event,
      { params },
    )
    return data
  }

  async deleteEvent(eventId: string, profileId?: string): Promise<void> {
    const params = profileId ? { profile_id: profileId } : {}
    await this.api.delete(`/calendar/events/${eventId}`, { params })
  }
}
