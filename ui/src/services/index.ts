import { assistantService } from './assistant'
import { conversationService } from './conversation'
import { sandboxService } from './sandbox'
import { whatsappService } from './whatsapp'
import { calendarService } from './calendar'
import { driveService } from './drive'
import { gmailService } from './gmail'
import { notionService } from './notion'
import { cronJobsService } from './cronJobs'
import { telegramService } from './telegram'
import { clickupService } from './clickup'
import { jiraService } from './jira'
import { slackService } from './slack'

class Services {
  assistantService: typeof assistantService
  conversationService: typeof conversationService
  sandboxService: typeof sandboxService
  whatsappService: typeof whatsappService
  calendarService: typeof calendarService
  driveService: typeof driveService
  gmailService: typeof gmailService
  notionService: typeof notionService
  cronJobsService: typeof cronJobsService
  telegramService: typeof telegramService
  clickupService: typeof clickupService
  jiraService: typeof jiraService
  slackService: typeof slackService

  constructor() {
    this.assistantService = assistantService
    this.conversationService = conversationService
    this.sandboxService = sandboxService
    this.whatsappService = whatsappService
    this.calendarService = calendarService
    this.driveService = driveService
    this.gmailService = gmailService
    this.notionService = notionService
    this.cronJobsService = cronJobsService
    this.telegramService = telegramService
    this.clickupService = clickupService
    this.jiraService = jiraService
    this.slackService = slackService
  }
}

const services = new Services()
export default services
