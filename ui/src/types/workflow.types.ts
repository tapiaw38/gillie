// workflow.types.ts
export interface WorkflowStep {
  name: string
  description: string
  url: string
  method: 'GET' | 'POST' | 'PUT' | 'DELETE'
  required_params: string[]
  body_template?: string
  response_mapping?: Record<string, string>
  condition?: string
}

export interface WorkflowFunction {
  type: 'simple' | 'workflow'
  name: string
  description: string
  input_params?: string[]
  steps?: WorkflowStep[]
  url_template?: string
  method?: 'GET' | 'POST' | 'PUT' | 'DELETE'
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
    bodyTemplate?: string
    responseMapping?: Record<string, string>
    condition?: string
  }
}

export interface WorkflowEdge {
  id: string
  source: string
  target: string
  label?: string
  animated?: boolean
}
