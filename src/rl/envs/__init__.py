"""
RL Environments for rugs.fun

Available environments:
- SidebetV1Env: Sidebet timing optimization (Sniper strategy)
"""

from .sidebet_v1_env import SidebetV1Env

__all__ = ["SidebetV1Env"]
