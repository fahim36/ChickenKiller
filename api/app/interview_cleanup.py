"""Periodic expiry deletes private text even when learners never return."""

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy.exc import SQLAlchemyError

from app.db import SessionLocal
from app.interviews import expire


def cleanup() -> None:
    with SessionLocal() as session:
        expire(session, datetime.now(UTC))
        session.commit()


async def run_cleanup() -> None:
    while True:
        try:
            await asyncio.to_thread(cleanup)
        except SQLAlchemyError:
            logging.getLogger(__name__).error("Interview expiry cleanup unavailable.")
        await asyncio.sleep(60)
