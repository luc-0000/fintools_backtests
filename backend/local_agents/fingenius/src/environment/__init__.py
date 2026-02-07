"""Environment module for different execution environments."""

from local_agents.fingenius.src.environment.base import BaseEnvironment
from local_agents.fingenius.src.environment.battle import BattleEnvironment
from local_agents.fingenius.src.environment.research import ResearchEnvironment


__all__ = ["BaseEnvironment", "ResearchEnvironment", "BattleEnvironment"]
