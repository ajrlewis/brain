from pathlib import Path
from typing import Any

from hatchling.builders.hooks.plugin.interface import BuildHookInterface


class CustomBuildHook(BuildHookInterface):
    """Include repository-owned bundles in both direct and sdist-based wheels."""

    def initialize(self, version: str, build_data: dict[str, Any]) -> None:
        del version
        repository_root = Path(self.root).resolve().parents[1]
        sources = {
            repository_root / "content" / "default": "default",
            repository_root / "examples" / "northstar": "northstar",
        }
        destination_prefix = (
            "src/brain_db/_bundles" if self.target_name == "sdist" else "brain_db/_bundles"
        )
        force_include = build_data.setdefault("force_include", {})
        for source, destination in sources.items():
            if source.is_dir():
                force_include[str(source)] = f"{destination_prefix}/{destination}"
