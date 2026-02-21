from src.core.platform.nosql.client import Client

class Datasources:
    def __init__(
        self,
        no_sql_conversations_client: Client,
        no_sql_profiles_client: Client,
        no_sql_faqs_client: Client,
        no_sql_calendar_sessions_client: Client = None,
        no_sql_calendar_events_client: Client = None,
    ):
        self.no_sql_conversations_client = no_sql_conversations_client
        self.no_sql_profiles_client = no_sql_profiles_client
        self.no_sql_faqs_client = no_sql_faqs_client
        self.no_sql_calendar_sessions_client = no_sql_calendar_sessions_client
        self.no_sql_calendar_events_client = no_sql_calendar_events_client

    @classmethod
    def create_datasources(
        cls,
        no_sql_conversations_client: Client,
        no_sql_profiles_client: Client,
        no_sql_faqs_client: Client,
        no_sql_calendar_sessions_client: Client = None,
        no_sql_calendar_events_client: Client = None,
    ) -> "Datasources":
        return cls(
            no_sql_conversations_client=no_sql_conversations_client,
            no_sql_profiles_client=no_sql_profiles_client,
            no_sql_faqs_client=no_sql_faqs_client,
            no_sql_calendar_sessions_client=no_sql_calendar_sessions_client,
            no_sql_calendar_events_client=no_sql_calendar_events_client,
        )