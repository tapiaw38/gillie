from src.core.platform.appcontext.appcontext import Factory
from src.core.platform.logging.logger import logger
from typing import Optional, List, Dict


class ResponseMeliQuestionsUseCase:
    def __init__(self, context_factory: Factory):
        self.context_factory = context_factory

    async def _process_mercadolibre_integration(self, integration, profile, context):
        try:
            ml_config = integration.config
            access_token = ml_config.get("access_token")
            ml_user_id = ml_config.get("user_id")

            logger.info(
                f"MercadoLibre integration - Access token: {access_token[:20]}..."
            )
            logger.info(f"MercadoLibre integration - User ID: {ml_user_id}")

            if not access_token or not ml_user_id:
                logger.warning("MercadoLibre integration missing credentials")
                return

            context.integrations.initialize_mercadolibre(
                access_token, ml_user_id
            )
            ml_integration = context.integrations.mercadolibre

            if not ml_integration:
                logger.error("Failed to initialize MercadoLibre integration")
                return

            async with ml_integration:
                logger.info("Processing MercadoLibre integration...")
                logger.info("Getting user items from MercadoLibre...")
                items = await ml_integration.get_user_items(limit=10)
                logger.info(f"Found {len(items)} user items")

                if items:
                    for item in items[:3]:
                        logger.info(
                            f"- {item.title} ({item.price} {item.currency_id}) - Status: {item.status}"
                        )

                    auto_answer = True

                    logger.info("Processing MercadoLibre unanswered questions...")
                    results = await ml_integration.auto_answer_questions_with_ai(
                        context.integrations.openai,
                        profile,
                        auto_send=auto_answer,
                    )

                    logger.info(
                        f"MercadoLibre processing results: {results['total_questions']} questions, "
                        f"{results['answered']} answered, {results['failed']} failed"
                    )

                    if not auto_answer and results["responses"]:
                        for response in results["responses"][:3]:
                            logger.info(f"Q: {response['question_text'][:100]}...")
                            logger.info(f"A: {response['suggested_answer'][:200]}...")

                    if auto_answer and results["answered"] > 0:
                        for response in results["responses"]:
                            if response["answered"]:
                                logger.info(
                                    f"✅ Answered Q{response['question_id']}: {response['question_text'][:50]}..."
                                )

                    logger.info(
                        f"MercadoLibre integration successful - {len(items)} items, {results['total_questions']} questions processed"
                    )
                else:
                    logger.warning(
                        "Could not access user items - check token permissions or user has no active items"
                    )

        except Exception as e:
            logger.error(f"Error processing MercadoLibre integration: {e}")

    async def execute(self) -> Dict[str, any]:
        try:
            logger.info(
                "Starting MercadoLibre questions processing for all active integrations..."
            )

            context = self.context_factory()
            profiles = context.repositories.profile.find_all()
            logger.info(f"Found {len(profiles)} total profiles")

            processed_profiles = 0
            active_integrations = 0
            errors = []

            for profile in profiles:
                try:
                    if not hasattr(profile, "integrations") or not profile.integrations:
                        continue

                    meli_integrations = [
                        integration
                        for integration in profile.integrations
                        if integration.name == "meli"
                        and getattr(integration, "is_active", True)
                    ]

                    if meli_integrations:
                        active_integrations += len(meli_integrations)
                        logger.info(
                            f"Processing profile {profile.user_id} with {len(meli_integrations)} active MercadoLibre integrations"
                        )

                        for integration in meli_integrations:
                            try:
                                await self._process_mercadolibre_integration(
                                    integration, profile, context
                                )
                                processed_profiles += 1
                                logger.info(
                                    f"Successfully processed MercadoLibre integration for profile {profile.user_id}"
                                )
                            except Exception as e:
                                error_msg = (
                                    f"Error processing profile {profile.user_id}: {e}"
                                )
                                logger.error(error_msg)
                                errors.append(error_msg)
                    else:
                        logger.debug(
                            f"Profile {profile.user_id} has no active MercadoLibre integrations"
                        )

                except Exception as e:
                    error_msg = f"Error processing profile {getattr(profile, 'user_id', 'unknown')}: {e}"
                    logger.error(error_msg)
                    errors.append(error_msg)

            logger.info(
                f"MercadoLibre processing completed. Profiles processed: {processed_profiles}, Active integrations: {active_integrations}"
            )

            return {
                "status": "success",
                "message": f"MercadoLibre questions processed successfully for {processed_profiles} profiles",
                "total_profiles": len(profiles),
                "processed_profiles": processed_profiles,
                "active_integrations": active_integrations,
                "errors": errors,
            }

        except Exception as e:
            logger.error(f"Error executing ResponseMeliQuestionsUseCase: {e}")
            return {
                "status": "error",
                "message": f"Error processing MercadoLibre questions: {e}",
                "total_profiles": 0,
                "processed_profiles": 0,
                "active_integrations": 0,
                "errors": [str(e)],
            }
