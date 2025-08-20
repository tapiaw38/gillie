import logging
import functools
import time
from typing import Callable, Any, Optional
from .logger import get_logger


def log_function_call(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)

        logger.debug(f"Entering {func.__name__} with args={args}, kwargs={kwargs}")

        try:
            result = func(*args, **kwargs)
            logger.debug(f"Exiting {func.__name__} with result={result}")
            return result
        except Exception as e:
            logger.error(f"Error in {func.__name__}: {e}", exc_info=True)
            raise

    return wrapper


def log_function_call_async(func: Callable) -> Callable:
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)

        logger.debug(
            f"Entering async {func.__name__} with args={args}, kwargs={kwargs}"
        )

        try:
            result = await func(*args, **kwargs)
            logger.debug(f"Exiting async {func.__name__} with result={result}")
            return result
        except Exception as e:
            logger.error(f"Error in async {func.__name__}: {e}", exc_info=True)
            raise

    return wrapper


def log_execution_time(func: Callable) -> Callable:
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        start_time = time.time()

        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(f"{func.__name__} executed in {execution_time:.4f} seconds")
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"{func.__name__} failed after {execution_time:.4f} seconds: {e}"
            )
            raise

    return wrapper


def log_execution_time_async(func: Callable) -> Callable:
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)
        start_time = time.time()

        try:
            result = await func(*args, **kwargs)
            execution_time = time.time() - start_time
            logger.info(
                f"Async {func.__name__} executed in {execution_time:.4f} seconds"
            )
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"Async {func.__name__} failed after {execution_time:.4f} seconds: {e}"
            )
            raise

    return wrapper


def log_deprecation_warning(func: Callable, message: Optional[str] = None) -> Callable:
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = get_logger(func.__module__)

        deprecation_msg = (
            message
            or f"{func.__name__} is deprecated and will be removed in a future version"
        )
        logger.warning(f"DEPRECATION WARNING: {deprecation_msg}")

        return func(*args, **kwargs)

    return wrapper


def log_context(context_name: str, **context_data):
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)

            context_str = ", ".join([f"{k}={v}" for k, v in context_data.items()])
            logger.debug(f"Context: {context_name} - {context_str}")

            return func(*args, **kwargs)

        return wrapper

    return decorator


def log_context_async(context_name: str, **context_data):
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            logger = get_logger(func.__module__)

            context_str = ", ".join([f"{k}={v}" for k, v in context_data.items()])
            logger.debug(f"Context: {context_name} - {context_str}")

            return await func(*args, **kwargs)

        return wrapper

    return decorator


def log_http_request(
    method: str, url: str, status_code: int, response_time: float, **kwargs
):
    logger = get_logger("http_requests")

    if status_code >= 500:
        log_level = logging.ERROR
    elif status_code >= 400:
        log_level = logging.WARNING
    else:
        log_level = logging.INFO

    message = f"{method} {url} - {status_code} ({response_time:.4f}s)"
    if kwargs:
        message += f" - {kwargs}"

    logger.log(log_level, message)


def log_database_operation(
    operation: str, collection: str, document_id: str = None, **kwargs
):
    logger = get_logger("database_operations")

    message = f"DB {operation} on {collection}"
    if document_id:
        message += f" (id: {document_id})"
    if kwargs:
        message += f" - {kwargs}"

    logger.debug(message)


def log_integration_call(
    integration_name: str, operation: str, success: bool, **kwargs
):
    logger = get_logger("integrations")

    status = "SUCCESS" if success else "FAILED"
    message = f"{integration_name} {operation} - {status}"
    if kwargs:
        message += f" - {kwargs}"

    if success:
        logger.info(message)
    else:
        logger.error(message)
