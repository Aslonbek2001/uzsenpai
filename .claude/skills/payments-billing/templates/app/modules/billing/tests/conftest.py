import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.testing import create_product


@pytest.fixture
async def product(db_session: AsyncSession) -> str:
    return await create_product(
        db_session,
        "mock-3",
        prices={"UZS": 9_900_000, "JPY": 1200},
        grants=[{"key": "interview.mock_session", "quantity": 3, "days": 90}],
    )
