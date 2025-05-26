"""Anomaly detection algorithms package."""

from typing import Any, Dict, List


class AlgorithmRegistry:
    """Registry for managing anomaly detection algorithms."""

    def __init__(self):
        self._algorithms = {}

    def register(self, name: str, algorithm_class):
        """Register an algorithm."""
        self._algorithms[name] = algorithm_class

    def get(self, name: str):
        """Get an algorithm by name."""
        return self._algorithms.get(name)

    def list_algorithms(self) -> List[str]:
        """List all registered algorithms."""
        return list(self._algorithms.keys())

    def get_algorithm_info(self, name: str) -> Dict[str, Any]:
        """Get information about an algorithm."""
        algorithm = self._algorithms.get(name)
        if algorithm:
            return {
                "name": name,
                "class": algorithm.__name__,
                "description": getattr(
                    algorithm, "__doc__", "No description available"
                ),
            }
        return {}


# Global registry instance
algorithm_registry = AlgorithmRegistry()


__all__ = ["AlgorithmRegistry", "algorithm_registry"]
