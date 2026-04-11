import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Optional

from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.errors import NewApplicationError
from src.core.platform.errors.mappings.job import JobGetNotFoundError
from src.schemas.job import JobRunOutput

logger = logging.getLogger(__name__)


class RunJobUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def execute(self, job_id: str) -> JobRunOutput:
        context = self.context_factory()
        job = context.repositories.job.find_by_id(job_id)
        if not job:
            raise NewApplicationError(JobGetNotFoundError)

        job.status = "running"
        job.updated_at = datetime.now(timezone.utc)
        context.repositories.job.update(job)

        output = ""
        try:
            output = await self._execute_source(job, context)
        except Exception as e:
            logger.error(f"[job:{job_id}] Source execution failed: {e}", exc_info=True)
            job.status = "failed"
            job.last_run_at = datetime.now(timezone.utc)
            job.last_result = str(e)[:500]
            job.updated_at = datetime.now(timezone.utc)
            context.repositories.job.update(job)
            return JobRunOutput(status="failed", result=str(e)[:500])

        formatted_message = job.message_template.replace("{{output}}", output)

        try:
            await self._send_to_destination(job, formatted_message, context)
        except Exception as e:
            logger.error(f"[job:{job_id}] Destination delivery failed: {e}", exc_info=True)
            job.status = "failed"
            job.last_run_at = datetime.now(timezone.utc)
            job.last_result = f"Source OK, destination failed: {e}"[:500]
            job.updated_at = datetime.now(timezone.utc)
            context.repositories.job.update(job)
            return JobRunOutput(status="failed", result=job.last_result)

        job.status = "idle"
        job.last_run_at = datetime.now(timezone.utc)
        job.last_result = output[:500]
        job.updated_at = datetime.now(timezone.utc)
        context.repositories.job.update(job)

        return JobRunOutput(status="success", result=output[:500])

    async def _execute_source(self, job, context) -> str:
        source_type = job.source_type
        params = job.source_params

        if source_type == "system_command":
            return await self._run_system_command(params.get("command", ""))
        elif source_type == "http_get":
            return await self._run_http_get(params)
        elif source_type == "db_query":
            return await self._run_db_query(params, job.profile_id, context)
        elif source_type == "static":
            return params.get("text", "")
        else:
            raise ValueError(f"Unknown source_type: {source_type}")

    async def _run_system_command(self, command: str) -> str:
        if not command:
            raise ValueError("system_command source requires 'command' param")

        try:
            from src.core.platform.tools.system_monitor import _get_blacklist, _is_blacklisted
            blacklist = _get_blacklist(None)
            blocked = _is_blacklisted(command, blacklist)
            if blocked:
                raise ValueError(f"Command blocked by blacklist: {blocked}")
        except ImportError:
            logger.warning("[job] system_monitor not available, skipping blacklist check")

        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=30)
            return stdout.decode("utf-8", errors="replace").strip()
        except asyncio.TimeoutError:
            raise ValueError(f"Command timed out after 30s: {command}")

    async def _run_http_get(self, params: dict) -> str:
        url = params.get("url")
        if not url:
            raise ValueError("http_get source requires 'url' param")

        headers = params.get("headers", {})

        import aiohttp
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                text = await resp.text()
                return text[:2000]

    async def _run_db_query(self, params: dict, profile_id: str, context) -> str:
        profile = context.repositories.profile.find_by_user_id(profile_id)
        if not profile:
            raise ValueError(f"Profile not found for profile_id={profile_id}")

        columns = params.get("columns", ["*"])
        filters = params.get("filters")
        limit = params.get("limit", 20)

        sql_integration = self._get_sql_integration(profile, context)
        if sql_integration is None:
            raise ValueError("No active sqldatabase integration found on profile")

        result = await sql_integration.query(columns=columns, filters=filters, limit=limit)
        return json.dumps(result, ensure_ascii=False, default=str)

    def _get_sql_integration(self, profile, context):
        if not profile or not profile.integrations:
            return None
        for integration in profile.integrations:
            if integration.name == "sqldatabase" and integration.activated:
                config = integration.config or {}
                connection_string = config.get("connection_string")
                allowed_table = config.get("allowed_table")
                if not connection_string or not allowed_table:
                    return None
                return context.integrations.make_sqldatabase_client(
                    connection_string=connection_string,
                    allowed_table=allowed_table,
                    table_description=config.get("table_description", ""),
                )
        return None

    async def _send_to_destination(self, job, message: str, context) -> None:
        dest_type = job.destination_type
        dest_params = job.destination_params

        if dest_type == "none":
            return

        profile = context.repositories.profile.find_by_user_id(job.profile_id)
        if not profile:
            logger.warning(f"[job:{job.id}] Profile not found, skipping destination delivery")
            return

        if dest_type == "whatsapp":
            await self._send_whatsapp(profile, dest_params, message, context)
        elif dest_type == "telegram":
            await self._send_telegram(profile, dest_params, message, context)
        elif dest_type == "slack":
            await self._send_slack(profile, dest_params, message, context)
        else:
            raise ValueError(f"Unknown destination_type: {dest_type}")

    async def _send_whatsapp(self, profile, params: dict, message: str, context) -> None:
        phone = params.get("phone")
        if not phone:
            raise ValueError("whatsapp destination requires 'phone' param")

        integration_config = self._find_integration(profile, "whatsapp")
        if not integration_config:
            raise ValueError("No active whatsapp integration found on profile")

        wa = context.integrations.make_whatsapp_client(
            access_token=integration_config.get("access_token", ""),
            phone_number_id=integration_config.get("phone_number_id", ""),
        )
        success = wa.send_message(phone, message)
        if not success:
            raise ValueError("WhatsApp message delivery failed")

    async def _send_telegram(self, profile, params: dict, message: str, context) -> None:
        chat_id = params.get("chat_id")
        if not chat_id:
            raise ValueError("telegram destination requires 'chat_id' param")

        integration_config = self._find_integration(profile, "telegram")
        if not integration_config:
            raise ValueError("No active telegram integration found on profile")

        tg = context.integrations.make_telegram_client(
            bot_token=integration_config.get("bot_token", ""),
        )
        success = tg.send_message(chat_id, message)
        if not success:
            raise ValueError("Telegram message delivery failed")

    async def _send_slack(self, profile, params: dict, message: str, context) -> None:
        channel = params.get("channel")
        if not channel:
            raise ValueError("slack destination requires 'channel' param")

        integration_config = self._find_integration(profile, "slack")
        if not integration_config:
            raise ValueError("No active slack integration found on profile")

        slack = context.integrations.make_slack_client(
            bot_token=integration_config.get("bot_token", ""),
        )
        success = slack.send_message(channel, message)
        if not success:
            raise ValueError("Slack message delivery failed")

    def _find_integration(self, profile, name: str) -> Optional[dict]:
        if not profile or not profile.integrations:
            return None
        for integration in profile.integrations:
            if integration.name == name and integration.activated:
                return integration.config or {}
        return None
