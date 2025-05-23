import pytest
import asyncio

@pytest.fixture(scope="session")
def event_loop():
    """Creates event loop for the entire test session"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close() 