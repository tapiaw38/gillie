export interface GmailAuthorizationResponse {
  authorization_url: string
  user_id: string
}

export interface GmailStatusResponse {
  is_active: boolean
  user_id: string
  email?: string
}
