"""Azure cost estimation for Cosmos DB and Blob Storage."""

from typing import Any, Dict, Optional

from src.utils.logger import get_logger

logger = get_logger(__name__)


class AzureCostEstimator:
    """Estimate costs for Azure Cosmos DB and Blob Storage."""

    # Azure pricing (approximate, as of 2026-04)
    COSMOS_DB_RU_COST_PER_MILLION = 0.25  # USD per million RUs
    BLOB_STORAGE_COSTS = {
        "Hot": {"per_gb_month": 0.024, "access_per_10k": 0.01},
        "Cool": {"per_gb_month": 0.013, "access_per_10k": 0.10},
        "Archive": {"per_gb_month": 0.002, "access_per_10k": 0.02},
    }

    def __init__(self):
        """Initialize cost estimator."""
        self.cost_breakdown: Dict[str, Any] = {}

    def estimate_cosmos_db_costs(
        self,
        estimated_docs_per_month: int,
        avg_doc_size_kb: float,
        estimated_query_rate_per_day: int,
        consistency_level: str = "Strong",
        multi_region: bool = False,
    ) -> Dict[str, Any]:
        """Estimate Cosmos DB costs based on usage patterns.

        Args:
            estimated_docs_per_month: Expected documents per month
            avg_doc_size_kb: Average document size in KB
            estimated_query_rate_per_day: Expected queries per day
            consistency_level: Consistency level (Strong, BoundedStaleness, Session, etc.)
            multi_region: Whether multi-region replication is enabled

        Returns:
            Cost estimation breakdown
        """
        # Estimate RU consumption
        # Write RU = doc_size_kb / 1
        # Read RU = 1
        writes_per_month = estimated_docs_per_month
        reads_per_month = (estimated_query_rate_per_day * 30) * 10  # Assume avg query touches 10 docs

        write_rus_per_month = writes_per_month * avg_doc_size_kb
        read_rus_per_month = reads_per_month * 1

        total_rus_per_month = write_rus_per_month + read_rus_per_month

        # Account for consistency level impact
        consistency_multiplier = {
            "Strong": 1.0,
            "BoundedStaleness": 1.0,
            "Session": 1.0,
            "Consistent Prefix": 0.9,
            "Eventual": 0.9,
        }
        multiplier = consistency_multiplier.get(consistency_level, 1.0)
        adjusted_rus = total_rus_per_month * multiplier

        # Account for multi-region
        if multi_region:
            adjusted_rus *= 1.5  # Approximate cost increase for replication

        # Calculate monthly cost
        rus_per_hour = adjusted_rus / (30 * 24)
        required_provisioned_rus = max(400, int(rus_per_hour * 1.3))  # Add 30% buffer

        monthly_cost = (
            (adjusted_rus / 1_000_000) * self.COSMOS_DB_RU_COST_PER_MILLION
        )

        return {
            "estimated_docs_per_month": estimated_docs_per_month,
            "avg_doc_size_kb": avg_doc_size_kb,
            "estimated_query_rate_per_day": estimated_query_rate_per_day,
            "consistency_level": consistency_level,
            "consistency_multiplier": multiplier,
            "multi_region": multi_region,
            "estimated_rus_per_month": int(adjusted_rus),
            "required_provisioned_rus": required_provisioned_rus,
            "estimated_monthly_cost_usd": round(monthly_cost, 2),
            "estimated_annual_cost_usd": round(monthly_cost * 12, 2),
            "breakdown": {
                "write_rus": int(write_rus_per_month),
                "read_rus": int(read_rus_per_month),
                "total_base_rus": int(total_rus_per_month),
            },
        }

    def estimate_blob_storage_costs(
        self,
        total_data_gb: float,
        access_tier: str = "Hot",
        access_frequency: str = "high",
        expected_transfers_gb_per_month: float = 0,
    ) -> Dict[str, Any]:
        """Estimate Blob Storage costs based on data volume and access patterns.

        Args:
            total_data_gb: Total data to store in GB
            access_tier: Access tier (Hot, Cool, Archive)
            access_frequency: Access frequency (high, medium, low)
            expected_transfers_gb_per_month: Expected data transfer in GB

        Returns:
            Cost estimation breakdown
        """
        if access_tier not in self.BLOB_STORAGE_COSTS:
            logger.warning(f"Unknown access tier {access_tier}, using Hot")
            access_tier = "Hot"

        tier_costs = self.BLOB_STORAGE_COSTS[access_tier]

        # Storage cost
        storage_cost_monthly = total_data_gb * tier_costs["per_gb_month"]

        # Access cost (operations per 10k)
        # High frequency = 1M operations/month
        # Medium frequency = 100k operations/month
        # Low frequency = 10k operations/month
        access_ops_per_month = {
            "high": 1_000_000,
            "medium": 100_000,
            "low": 10_000,
        }

        operations = access_ops_per_month.get(access_frequency, 100_000)
        access_cost_monthly = (operations / 10_000) * tier_costs["access_per_10k"]

        # Data transfer cost (egress only, intra-Azure is free)
        # Assume $0.02 per GB for egress
        egress_cost_monthly = expected_transfers_gb_per_month * 0.02

        total_monthly_cost = storage_cost_monthly + access_cost_monthly + egress_cost_monthly

        return {
            "total_data_gb": total_data_gb,
            "access_tier": access_tier,
            "access_frequency": access_frequency,
            "expected_transfers_gb_per_month": expected_transfers_gb_per_month,
            "storage_cost_monthly": round(storage_cost_monthly, 2),
            "access_cost_monthly": round(access_cost_monthly, 2),
            "egress_cost_monthly": round(egress_cost_monthly, 2),
            "total_monthly_cost_usd": round(total_monthly_cost, 2),
            "total_annual_cost_usd": round(total_monthly_cost * 12, 2),
            "breakdown": {
                "storage": round(storage_cost_monthly, 2),
                "operations": round(access_cost_monthly, 2),
                "egress": round(egress_cost_monthly, 2),
            },
        }

    def estimate_total_migration_cost(
        self,
        cosmos_estimate: Dict[str, Any],
        blob_estimate: Dict[str, Any],
        migration_duration_hours: int = 24,
    ) -> Dict[str, Any]:
        """Estimate total migration cost combining Cosmos DB and Blob Storage.

        Args:
            cosmos_estimate: Cosmos DB cost estimate
            blob_estimate: Blob Storage cost estimate
            migration_duration_hours: Expected migration duration in hours

        Returns:
            Total cost estimation
        """
        # Migration itself typically runs on autoscale, estimate temp RU usage
        # Assume 30% higher throughput during migration
        cosmos_monthly = cosmos_estimate["estimated_monthly_cost_usd"]
        blob_monthly = blob_estimate["total_monthly_cost_usd"]

        # Migration temp cost (for migration period only)
        migration_temp_cost = (cosmos_monthly / 30 / 24) * migration_duration_hours * 1.3

        total_monthly = cosmos_monthly + blob_monthly
        total_annual = total_monthly * 12

        return {
            "cosmos_db_monthly": cosmos_monthly,
            "blob_storage_monthly": blob_monthly,
            "total_monthly_usd": round(total_monthly, 2),
            "total_annual_usd": round(total_annual, 2),
            "migration_temp_cost": round(migration_temp_cost, 2),
            "total_first_month_usd": round(total_monthly + migration_temp_cost, 2),
            "breakdown": {
                "cosmos_db": {
                    "monthly": cosmos_monthly,
                    "annual": round(cosmos_monthly * 12, 2),
                },
                "blob_storage": {
                    "monthly": blob_monthly,
                    "annual": round(blob_monthly * 12, 2),
                },
            },
        }

    def recommend_cost_optimization(
        self,
        cosmos_estimate: Dict[str, Any],
        blob_estimate: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Recommend cost optimization strategies.

        Args:
            cosmos_estimate: Cosmos DB cost estimate
            blob_estimate: Blob Storage cost estimate

        Returns:
            Cost optimization recommendations
        """
        recommendations = []

        # Cosmos DB optimizations
        provisioned_rus = cosmos_estimate.get("required_provisioned_rus", 400)
        if provisioned_rus > 4000:
            recommendations.append({
                "service": "Cosmos DB",
                "issue": "High RU/s requirement",
                "recommendation": "Consider autoscale provisioning",
                "potential_savings": "15-20%",
            })

        if cosmos_estimate.get("multi_region"):
            recommendations.append({
                "service": "Cosmos DB",
                "issue": "Multi-region enabled",
                "recommendation": "Use single-region with eventual consistency if acceptable",
                "potential_savings": "33%",
            })

        # Blob Storage optimizations
        storage_tier = blob_estimate.get("access_tier", "Hot")
        if storage_tier == "Hot":
            total_data = blob_estimate.get("total_data_gb", 0)
            if total_data > 100:
                recommendations.append({
                    "service": "Blob Storage",
                    "issue": f"Large volume ({total_data}GB) in Hot tier",
                    "recommendation": "Move infrequently accessed data to Cool/Archive tier",
                    "potential_savings": "40-90%",
                })

        access_freq = blob_estimate.get("access_frequency", "medium")
        if access_freq == "high":
            recommendations.append({
                "service": "Blob Storage",
                "issue": "High access frequency assumed",
                "recommendation": "Implement caching layer (Azure Cache for Redis)",
                "potential_savings": "20-30%",
            })

        return {
            "recommendations": recommendations,
            "total_potential_savings": sum(
                float(r.get("potential_savings", "0%").strip("%").split("-")[0]) / 100
                for r in recommendations
            ) if recommendations else 0.0,
        }
