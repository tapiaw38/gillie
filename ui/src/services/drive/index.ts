import { server } from '@/api/request/server'
import { DriveService } from './driveService'

const BASE_URL = import.meta.env.VITE_DRIVE_BASE_URL || 'http://localhost:8000'

export const driveService = new DriveService(server({ baseURL: BASE_URL }))

export { DriveService }
export type { IDriveService, DriveAuthorizationResponse, DriveStatusResponse } from './driveService'
