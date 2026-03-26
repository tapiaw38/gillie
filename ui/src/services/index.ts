import { assistantService } from './assistant'
import { conversationService } from './conversation'
import { sandboxService } from './sandbox'
import { whatsappService } from './whatsapp'
import { calendarService } from './calendar'

class Services {
  assistantService: typeof assistantService
  conversationService: typeof conversationService
  sandboxService: typeof sandboxService
  whatsappService: typeof whatsappService
  calendarService: typeof calendarService

  constructor() {
    this.assistantService = assistantService
    this.conversationService = conversationService
    this.sandboxService = sandboxService
    this.whatsappService = whatsappService
    this.calendarService = calendarService
  }
}

const services = new Services()
export default services
