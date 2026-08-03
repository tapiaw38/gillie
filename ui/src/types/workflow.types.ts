// workflow.types.ts
export type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'

export interface WorkflowStep {
  name: string
  description: string
  url: string
  method: HttpMethod
  required_params: string[]
  headers?: Record<string, string>
  body_template?: string
  response_mapping?: Record<string, string>
  condition?: string
  continue_on_error?: boolean
}

export interface WorkflowFunction {
  type: 'simple' | 'workflow'
  name: string
  description: string
  input_params?: string[]
  steps?: WorkflowStep[]
  url_template?: string
  method?: HttpMethod
  required_params?: string[]
  optional_params?: string[]
  param_types?: Record<string, string>
  param_descriptions?: Record<string, string>
  examples?: string[]
  keywords?: string[]
}

export interface WorkflowNodeData {
  label: string
  type: 'start' | 'http_request' | 'condition' | 'mapping'
  config?: {
    url?: string
    method?: string
    params?: string[]
    headers?: Record<string, string>
    bodyTemplate?: string
    responseMapping?: Record<string, string>
    condition?: string
    continueOnError?: boolean
  }
}

export interface WorkflowEdge {
  id: string
  source: string
  target: string
  label?: string
  animated?: boolean
}

export interface WorkflowStepTestParams {
  step: Omit<WorkflowStep, 'description' | 'required_params'> & {
    description?: string
    required_params?: string[]
  }
  context: Record<string, string>
}

export interface WorkflowStepTestResponse {
  ok: boolean
  response?: unknown
  /** Dot-paths found in the response, ready to paste into response_mapping. */
  paths?: string[]
  error?: string
  elapsed_ms: number
}
