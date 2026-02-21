export interface ApiErrorResponse {
  code: string
  message: string
}

export class ApplicationError extends Error {
  code: string
  originalMessage: string
  statusCode?: number

  constructor(errorResponse: ApiErrorResponse, statusCode?: number) {
    super(errorResponse.message)
    this.name = 'ApplicationError'
    this.code = errorResponse.code
    this.originalMessage = errorResponse.message
    this.statusCode = statusCode
  }

  is(code: string): boolean {
    return this.code === code
  }

  isDomain(domain: string): boolean {
    return this.code.startsWith(`${domain}:`)
  }

  getDomain(): string {
    return this.code.split(':')[0] || ''
  }

  getAction(): string {
    return this.code.split(':')[1] || ''
  }

  getErrorType(): string {
    const parts = this.code.split(':')
    return parts.slice(2).join(':') || ''
  }
}

export const ErrorCodes = {
  Common: {
    RequestBodyParsing: 'common:request-body-parsing-error',
    RequestBodyValidation: 'common:request-body-validation-error',
    DatabaseConnection: 'common:database-connection-error',
    DatabaseQuery: 'common:database-query-error',
    ExternalService: 'common:external-service-error',
    NotFound: 'common:not-found',
    Unauthorized: 'common:unauthorized',
    Forbidden: 'common:forbidden',
  },

  User: {
    LoginInvalidCredentials: 'user:login:invalid-credentials',
    LoginUserNotFound: 'user:login:user-not-found',
    LoginUserNotActive: 'user:login:user-not-active',
    LoginSSOAuthMethod: 'user:login:sso-auth-method',
    RegisterEmailExists: 'user:register:email-exists',
    RegisterValidation: 'user:register:validation-error',
    PasswordInvalid: 'user:password:invalid',
    PasswordWeak: 'user:password:weak',
    ResetTokenInvalid: 'user:reset-password:invalid-token',
    ResetTokenExpired: 'user:reset-password:token-expired',
  },

  Profile: {
    CreateNameRequired: 'profile:create:name-required',
    CreateBusinessNameRequired: 'profile:create:business-name-required',
    CreateQueryError: 'profile:create:query-error',
    CreateDuplicate: 'profile:create:duplicate',
    GetQueryError: 'profile:get:query-error',
    GetNotFound: 'profile:get:not-found',
    UpdateQueryError: 'profile:update:query-error',
    UpdateNotFound: 'profile:update:not-found',
    UpdateValidation: 'profile:update:validation-error',
    DeleteQueryError: 'profile:delete:query-error',
    DeleteNotFound: 'profile:delete:not-found',
    ListQueryError: 'profile:list:query-error',
    IterationLimitUpdateError: 'profile:iteration-limit:update-error',
    ApiKeyCreateError: 'profile:api-key:create-error',
    ApiKeyDeleteError: 'profile:api-key:delete-error',
    ApiKeyNotFound: 'profile:api-key:not-found',
    ApiKeyValidationError: 'profile:api-key:validation-error',
    ApiKeyLimitExceeded: 'profile:api-key:limit-exceeded',
    FileUploadError: 'profile:file:upload-error',
    FileDeleteError: 'profile:file:delete-error',
    FileNotFound: 'profile:file:not-found',
    FileSizeExceeded: 'profile:file:size-exceeded',
    IntegrationCreateError: 'profile:integration:create-error',
    IntegrationUpdateError: 'profile:integration:update-error',
    IntegrationNotFound: 'profile:integration:not-found',
  },

  Conversation: {
    CreateQueryError: 'conversation:create:query-error',
    CreateValidationError: 'conversation:create:validation-error',
    CreateTitleRequired: 'conversation:create:title-required',
    CreateProfileRequired: 'conversation:create:profile-required',
    CreateProfileNotFound: 'conversation:create:profile-not-found',
    CreateNotFoundAfterCreation: 'conversation:create:not-found-after-creation',
    GetQueryError: 'conversation:get:query-error',
    GetNotFound: 'conversation:get:not-found',
    UpdateQueryError: 'conversation:update:query-error',
    UpdateNotFound: 'conversation:update:not-found',
    UpdateValidationError: 'conversation:update:validation-error',
    DeleteQueryError: 'conversation:delete:query-error',
    DeleteNotFound: 'conversation:delete:not-found',
    ListQueryError: 'conversation:list:query-error',
    MessageAddError: 'conversation:message:add-error',
    MessageDeleteError: 'conversation:message:delete-error',
    MessageNotFound: 'conversation:message:not-found',
    MessageValidationError: 'conversation:message:validation-error',
    MessageContentRequired: 'conversation:message:content-required',
  },

  FAQ: {
    CreateQueryError: 'faq:create:query-error',
    CreateValidationError: 'faq:create:validation-error',
    CreateQuestionRequired: 'faq:create:question-required',
    CreateAnswerRequired: 'faq:create:answer-required',
    CreateCategoryRequired: 'faq:create:category-required',
    CreateDuplicate: 'faq:create:duplicate',
    CreateNotFoundAfterCreation: 'faq:create:not-found-after-creation',
    GetQueryError: 'faq:get:query-error',
    GetNotFound: 'faq:get:not-found',
    UpdateQueryError: 'faq:update:query-error',
    UpdateNotFound: 'faq:update:not-found',
    UpdateValidationError: 'faq:update:validation-error',
    DeleteQueryError: 'faq:delete:query-error',
    DeleteNotFound: 'faq:delete:not-found',
    ListQueryError: 'faq:list:query-error',
    ListByCategoryQueryError: 'faq:list-by-category:query-error',
    ListByCategoryNotFound: 'faq:list-by-category:not-found',
  },

  Role: {
    CreateNameRequired: 'role:create:name-required',
    CreateInvalidName: 'role:create:invalid-name',
    GetNotFound: 'role:get:not-found',
  },
} as const

export const ErrorMessages: Record<string, string> = {
  [ErrorCodes.Common.RequestBodyParsing]: 'El formato de los datos es inválido',
  [ErrorCodes.Common.RequestBodyValidation]: 'Los datos proporcionados no son válidos',
  [ErrorCodes.Common.DatabaseConnection]: 'Error de conexión con la base de datos',
  [ErrorCodes.Common.DatabaseQuery]: 'Error al procesar la solicitud',
  [ErrorCodes.Common.ExternalService]: 'Servicio externo no disponible',
  [ErrorCodes.Common.NotFound]: 'Recurso no encontrado',
  [ErrorCodes.Common.Unauthorized]: 'No autorizado. Por favor inicia sesión',
  [ErrorCodes.Common.Forbidden]: 'No tienes permisos para realizar esta acción',
  [ErrorCodes.User.LoginInvalidCredentials]: 'Email o contraseña incorrectos',
  [ErrorCodes.User.LoginUserNotFound]: 'Usuario no encontrado',
  [ErrorCodes.User.LoginUserNotActive]: 'Tu cuenta no está activa. Verifica tu email',
  [ErrorCodes.User.LoginSSOAuthMethod]: 'Esta cuenta usa autenticación SSO',
  [ErrorCodes.User.RegisterEmailExists]: 'El email ya está registrado',
  [ErrorCodes.User.RegisterValidation]: 'Los datos de registro no son válidos',
  [ErrorCodes.User.PasswordInvalid]: 'Contraseña incorrecta',
  [ErrorCodes.User.PasswordWeak]: 'La contraseña es muy débil',
  [ErrorCodes.User.ResetTokenInvalid]: 'Token de recuperación inválido',
  [ErrorCodes.User.ResetTokenExpired]: 'El token de recuperación ha expirado',
  [ErrorCodes.Profile.CreateNameRequired]: 'El nombre del asistente es requerido',
  [ErrorCodes.Profile.CreateBusinessNameRequired]: 'El nombre del negocio es requerido',
  [ErrorCodes.Profile.CreateQueryError]: 'Error al crear el perfil',
  [ErrorCodes.Profile.CreateDuplicate]: 'Ya existe un perfil con este nombre',
  [ErrorCodes.Profile.GetQueryError]: 'Error al obtener el perfil',
  [ErrorCodes.Profile.GetNotFound]: 'Perfil no encontrado',
  [ErrorCodes.Profile.UpdateQueryError]: 'Error al actualizar el perfil',
  [ErrorCodes.Profile.UpdateNotFound]: 'Perfil no encontrado para actualizar',
  [ErrorCodes.Profile.UpdateValidation]: 'Datos de actualización inválidos',
  [ErrorCodes.Profile.DeleteQueryError]: 'Error al eliminar el perfil',
  [ErrorCodes.Profile.DeleteNotFound]: 'Perfil no encontrado para eliminar',
  [ErrorCodes.Profile.ListQueryError]: 'Error al listar los perfiles',
  [ErrorCodes.Profile.IterationLimitUpdateError]: 'Error al actualizar el límite de iteraciones',
  [ErrorCodes.Profile.ApiKeyCreateError]: 'Error al crear la API key',
  [ErrorCodes.Profile.ApiKeyDeleteError]: 'Error al eliminar la API key',
  [ErrorCodes.Profile.ApiKeyNotFound]: 'API key no encontrada',
  [ErrorCodes.Profile.ApiKeyValidationError]: 'La API key no es válida',
  [ErrorCodes.Profile.ApiKeyLimitExceeded]: 'Has alcanzado el límite de API keys',
  [ErrorCodes.Profile.FileUploadError]: 'Error al subir el archivo',
  [ErrorCodes.Profile.FileDeleteError]: 'Error al eliminar el archivo',
  [ErrorCodes.Profile.FileNotFound]: 'Archivo no encontrado',
  [ErrorCodes.Profile.FileSizeExceeded]: 'El archivo es demasiado grande',
  [ErrorCodes.Profile.IntegrationCreateError]: 'Error al crear la integración',
  [ErrorCodes.Profile.IntegrationUpdateError]: 'Error al actualizar la integración',
  [ErrorCodes.Profile.IntegrationNotFound]: 'Integración no encontrada',
  [ErrorCodes.Conversation.CreateQueryError]: 'Error al crear la conversación',
  [ErrorCodes.Conversation.CreateValidationError]: 'Datos de conversación inválidos',
  [ErrorCodes.Conversation.CreateTitleRequired]: 'El título de la conversación es requerido',
  [ErrorCodes.Conversation.CreateProfileRequired]: 'El perfil es requerido para crear la conversación',
  [ErrorCodes.Conversation.CreateProfileNotFound]: 'Perfil no encontrado para la conversación',
  [ErrorCodes.Conversation.CreateNotFoundAfterCreation]: 'Conversación no encontrada después de crearla',
  [ErrorCodes.Conversation.GetQueryError]: 'Error al obtener la conversación',
  [ErrorCodes.Conversation.GetNotFound]: 'Conversación no encontrada',
  [ErrorCodes.Conversation.UpdateQueryError]: 'Error al actualizar la conversación',
  [ErrorCodes.Conversation.UpdateNotFound]: 'Conversación no encontrada para actualizar',
  [ErrorCodes.Conversation.UpdateValidationError]: 'Datos de actualización inválidos',
  [ErrorCodes.Conversation.DeleteQueryError]: 'Error al eliminar la conversación',
  [ErrorCodes.Conversation.DeleteNotFound]: 'Conversación no encontrada para eliminar',
  [ErrorCodes.Conversation.ListQueryError]: 'Error al listar las conversaciones',
  [ErrorCodes.Conversation.MessageAddError]: 'Error al agregar el mensaje',
  [ErrorCodes.Conversation.MessageDeleteError]: 'Error al eliminar el mensaje',
  [ErrorCodes.Conversation.MessageNotFound]: 'Mensaje no encontrado',
  [ErrorCodes.Conversation.MessageValidationError]: 'El mensaje no es válido',
  [ErrorCodes.Conversation.MessageContentRequired]: 'El contenido del mensaje es requerido',
  [ErrorCodes.FAQ.CreateQueryError]: 'Error al crear la FAQ',
  [ErrorCodes.FAQ.CreateValidationError]: 'Datos de FAQ inválidos',
  [ErrorCodes.FAQ.CreateQuestionRequired]: 'La pregunta es requerida',
  [ErrorCodes.FAQ.CreateAnswerRequired]: 'La respuesta es requerida',
  [ErrorCodes.FAQ.CreateCategoryRequired]: 'La categoría es requerida',
  [ErrorCodes.FAQ.CreateDuplicate]: 'Ya existe una FAQ con esta pregunta',
  [ErrorCodes.FAQ.CreateNotFoundAfterCreation]: 'FAQ no encontrada después de crearla',
  [ErrorCodes.FAQ.GetQueryError]: 'Error al obtener la FAQ',
  [ErrorCodes.FAQ.GetNotFound]: 'FAQ no encontrada',
  [ErrorCodes.FAQ.UpdateQueryError]: 'Error al actualizar la FAQ',
  [ErrorCodes.FAQ.UpdateNotFound]: 'FAQ no encontrada para actualizar',
  [ErrorCodes.FAQ.UpdateValidationError]: 'Datos de actualización inválidos',
  [ErrorCodes.FAQ.DeleteQueryError]: 'Error al eliminar la FAQ',
  [ErrorCodes.FAQ.DeleteNotFound]: 'FAQ no encontrada para eliminar',
  [ErrorCodes.FAQ.ListQueryError]: 'Error al listar las FAQs',
  [ErrorCodes.FAQ.ListByCategoryQueryError]: 'Error al listar las FAQs por categoría',
  [ErrorCodes.FAQ.ListByCategoryNotFound]: 'No se encontraron FAQs para esta categoría',
  [ErrorCodes.Role.CreateNameRequired]: 'El nombre del rol es requerido',
  [ErrorCodes.Role.CreateInvalidName]: 'Nombre de rol inválido',
  [ErrorCodes.Role.GetNotFound]: 'Rol no encontrado',
}

export const getErrorMessage = (error: ApplicationError): string => {
  return ErrorMessages[error.code] || error.originalMessage || 'Ha ocurrido un error'
}

export const isValidationError = (error: ApplicationError): boolean => {
  return error.statusCode === 400
}

export const isAuthError = (error: ApplicationError): boolean => {
  return error.statusCode === 401 || error.is(ErrorCodes.Common.Unauthorized)
}

export const isNotFoundError = (error: ApplicationError): boolean => {
  return error.statusCode === 404 || error.code.includes(':not-found')
}

export const isServerError = (error: ApplicationError): boolean => {
  return error.statusCode !== undefined && error.statusCode >= 500
}
