"""MongoDB connector for discovering and streaming data."""

from typing import Any, Dict, Generator, List, Optional

from pymongo import MongoClient
from pymongo.errors import PyMongoError
from src.utils.logger import get_logger

logger = get_logger(__name__)


class MongoDBConnector:
    """Discover and stream data from MongoDB."""

    def __init__(self, uri: str):
        """Initialize MongoDB connector.

        Args:
            uri: MongoDB connection URI

        Raises:
            PyMongoError: If connection fails
        """
        self.uri = uri
        self.client: Optional[MongoClient] = None
        self._connect()

    def _connect(self) -> None:
        """Establish MongoDB connection."""
        try:
            self.client = MongoClient(self.uri, serverSelectionTimeoutMS=5000)
            # Test connection
            self.client.admin.command("ping")
            logger.info("Connected to MongoDB")
        except PyMongoError as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    def list_databases(self) -> List[str]:
        """List all databases in MongoDB instance.

        Returns:
            List of database names
        """
        if not self.client:
            raise RuntimeError("Not connected to MongoDB")

        try:
            return self.client.list_database_names()
        except PyMongoError as e:
            logger.error(f"Failed to list databases: {e}")
            raise

    def list_collections(self, database: str) -> List[str]:
        """List collections in a database.

        Args:
            database: Database name

        Returns:
            List of collection names
        """
        if not self.client:
            raise RuntimeError("Not connected to MongoDB")

        try:
            db = self.client[database]
            return db.list_collection_names()
        except PyMongoError as e:
            logger.error(f"Failed to list collections in {database}: {e}")
            raise

    def get_collection_stats(self, database: str, collection: str) -> Dict[str, Any]:
        """Get statistics for a collection.

        Args:
            database: Database name
            collection: Collection name

        Returns:
            Collection statistics
        """
        if not self.client:
            raise RuntimeError("Not connected to MongoDB")

        try:
            db = self.client[database]
            coll = db[collection]

            count = coll.count_documents({})
            if count == 0:
                return {
                    "database": database,
                    "collection": collection,
                    "document_count": 0,
                    "avg_document_size_bytes": 0,
                }

            # Estimate average document size
            pipeline = [
                {"$sample": {"size": min(100, count)}},
                {
                    "$project": {
                        "size": {"$bsonSize": "$$ROOT"},
                    }
                },
                {
                    "$group": {
                        "_id": None,
                        "avg_size": {"$avg": "$size"},
                    }
                },
            ]

            result = list(coll.aggregate(pipeline))
            avg_size = result[0]["avg_size"] if result else 0

            return {
                "database": database,
                "collection": collection,
                "document_count": count,
                "avg_document_size_bytes": int(avg_size),
                "estimated_size_mb": int((count * avg_size) / (1024 * 1024)),
            }

        except PyMongoError as e:
            logger.error(
                f"Failed to get stats for {database}.{collection}: {e}"
            )
            raise

    def sample_documents(
        self, database: str, collection: str, sample_size: int = 100
    ) -> List[Dict[str, Any]]:
        """Sample documents from a collection.

        Args:
            database: Database name
            collection: Collection name
            sample_size: Number of documents to sample

        Returns:
            List of sample documents
        """
        if not self.client:
            raise RuntimeError("Not connected to MongoDB")

        try:
            db = self.client[database]
            coll = db[collection]

            # Use aggregation pipeline for efficient sampling
            pipeline = [{"$sample": {"size": sample_size}}]
            samples = list(coll.aggregate(pipeline))

            # Remove _id field for cleaner analysis
            for doc in samples:
                doc.pop("_id", None)

            return samples

        except PyMongoError as e:
            logger.error(
                f"Failed to sample from {database}.{collection}: {e}"
            )
            raise

    def stream_documents(
        self,
        database: str,
        collection: str,
        batch_size: int = 1000,
        query: Optional[Dict[str, Any]] = None,
    ) -> Generator[List[Dict[str, Any]], None, None]:
        """Stream all documents from a collection in batches.

        Args:
            database: Database name
            collection: Collection name
            batch_size: Number of documents per batch
            query: Optional MongoDB query filter

        Yields:
            Batches of documents
        """
        if not self.client:
            raise RuntimeError("Not connected to MongoDB")

        try:
            db = self.client[database]
            coll = db[collection]

            query = query or {}
            cursor = coll.find(query).batch_size(batch_size)

            batch = []
            for doc in cursor:
                doc.pop("_id", None)
                batch.append(doc)

                if len(batch) >= batch_size:
                    yield batch
                    batch = []

            # Yield remaining documents
            if batch:
                yield batch

        except PyMongoError as e:
            logger.error(
                f"Error streaming from {database}.{collection}: {e}"
            )
            raise

    def close(self) -> None:
        """Close MongoDB connection."""
        if self.client:
            self.client.close()
            logger.info("MongoDB connection closed")
