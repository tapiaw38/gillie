import { assistantService } from './assistant'
import { conversationService } from './conversation'
import { sandboxService } from './sandbox'
import { whatsappService } from './whatsapp'
import { calendarService } from './calendar'
import { driveService } from './drive'

class Services {
  assistantService: typeof assistantService
  conversationService: typeof conversationService
  sandboxService: typeof sandboxService
  whatsappService: typeof whatsappService
  calendarService: typeof calendarService
  driveService: typeof driveService

  constructor() {
    this.assistantService = assistantService
    this.conversationService = conversationService
    this.sandboxService = sandboxService
    this.whatsappService = whatsappService
    this.calendarService = calendarService
    this.driveService = driveService
  }
}

const services = new Services()
export default services
