import logging

from pymilvus import MilvusClient

logger = logging.getLogger(__name__)


def list_all(client: MilvusClient):
    """List all databases and their details."""
    databases = client.list_databases()
    logger.info(f"Found {len(databases)} databases:")
    for db in databases:
        logger.info(f"\nDatabase: {db}")
        try:
            collections = client.list_collections()
            logger.info(f"  Collections: {collections}")
        except Exception as _:
            logger.info("  Collections: Unable to list (insufficient privileges)")
