#!/usr/bin/env python3
"""
Train Sidebet V1 Model

Trains a PPO agent to optimize sidebet timing in rugs.fun.
Uses the Sniper strategy (single bet per game, targeting tick 200+).

Usage:
    python scripts/train_sidebet_v1.py [--timesteps N] [--eval-freq N]

Author: Human + Claude
Date: 2026-01-10
"""

import argparse
import sys
from datetime import datetime
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import numpy as np

try:
    from stable_baselines3 import PPO
    from stable_baselines3.common.callbacks import (
        BaseCallback,
        CheckpointCallback,
        EvalCallback,
    )
    from stable_baselines3.common.monitor import Monitor
    from stable_baselines3.common.vec_env import DummyVecEnv, VecNormalize
except ImportError:
    print("ERROR: stable-baselines3 not installed.")
    print("Install with: pip install stable-baselines3[extra]")
    sys.exit(1)

from rl.envs import SidebetV1Env


class StatsCallback(BaseCallback):
    """Custom callback to log environment stats."""

    def __init__(self, verbose=0):
        super().__init__(verbose)
        self.episode_rewards = []
        self.episode_wins = []
        self.episode_zones = []

    def _on_step(self) -> bool:
        # Check for episode end
        for info in self.locals.get("infos", []):
            if "episode_reward" in info:
                self.episode_rewards.append(info["episode_reward"])
                self.episode_wins.append(info.get("bet_won"))
                self.episode_zones.append(info.get("zone", "unknown"))

                # Log every 100 episodes
                if len(self.episode_rewards) % 100 == 0:
                    recent = self.episode_rewards[-100:]
                    wins = [w for w in self.episode_wins[-100:] if w is True]
                    bets = [w for w in self.episode_wins[-100:] if w is not None]

                    print(f"\n--- Episode {len(self.episode_rewards)} ---")
                    print(f"Avg Reward (last 100): {np.mean(recent):.3f}")
                    print(
                        f"Win Rate: {len(wins)}/{len(bets)} = {len(wins) / max(len(bets), 1):.1%}"
                    )
                    print(f"Bet Rate: {len(bets)}/100 = {len(bets)}%")

                    # Zone distribution
                    zones = self.episode_zones[-100:]
                    zone_counts = {}
                    for z in zones:
                        zone_counts[z] = zone_counts.get(z, 0) + 1
                    print(f"Zones: {zone_counts}")

        return True


def make_env(data_path: str = None, seed: int = None):
    """Factory function for creating environments."""

    def _init():
        env = SidebetV1Env(data_path=data_path, shuffle=True)
        if seed is not None:
            env.reset(seed=seed)
        return Monitor(env)

    return _init


def main():
    parser = argparse.ArgumentParser(description="Train Sidebet V1 Model")
    parser.add_argument(
        "--timesteps", type=int, default=500_000, help="Total training timesteps (default: 500000)"
    )
    parser.add_argument(
        "--eval-freq",
        type=int,
        default=10_000,
        help="Evaluation frequency in timesteps (default: 10000)",
    )
    parser.add_argument(
        "--checkpoint-freq",
        type=int,
        default=50_000,
        help="Checkpoint frequency in timesteps (default: 50000)",
    )
    parser.add_argument("--seed", type=int, default=42, help="Random seed (default: 42)")
    parser.add_argument(
        "--data-path", type=str, default=None, help="Path to games_with_prices.parquet"
    )
    parser.add_argument(
        "--output-dir", type=str, default=None, help="Output directory for models and logs"
    )
    args = parser.parse_args()

    # Set up paths
    project_root = Path(__file__).parent.parent
    ml_dir = project_root / "Machine Learning" / "models" / "sidebet-v1"

    if args.output_dir:
        output_dir = Path(args.output_dir)
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_dir = ml_dir / "runs" / f"run_{timestamp}"

    output_dir.mkdir(parents=True, exist_ok=True)
    checkpoints_dir = output_dir / "checkpoints"
    checkpoints_dir.mkdir(exist_ok=True)
    logs_dir = output_dir / "logs"
    logs_dir.mkdir(exist_ok=True)

    print("=" * 60)
    print("SIDEBET V1 TRAINING")
    print("=" * 60)
    print(f"Output directory: {output_dir}")
    print(f"Timesteps: {args.timesteps:,}")
    print(f"Seed: {args.seed}")
    print()

    # Create training environment
    print("Creating training environment...")
    train_env = DummyVecEnv([make_env(args.data_path, args.seed)])
    train_env = VecNormalize(
        train_env,
        norm_obs=True,
        norm_reward=True,
        clip_obs=10.0,
        clip_reward=10.0,
    )

    # Create evaluation environment
    print("Creating evaluation environment...")
    eval_env = DummyVecEnv([make_env(args.data_path, args.seed + 1000)])
    eval_env = VecNormalize(
        eval_env,
        norm_obs=True,
        norm_reward=False,  # Don't normalize reward for eval
        training=False,
        clip_obs=10.0,
    )

    # Create model
    print("Creating PPO model...")
    model = PPO(
        "MlpPolicy",
        train_env,
        learning_rate=3e-4,
        n_steps=2048,
        batch_size=64,
        n_epochs=10,
        gamma=0.99,
        gae_lambda=0.95,
        clip_range=0.2,
        ent_coef=0.01,  # Encourage exploration
        vf_coef=0.5,
        max_grad_norm=0.5,
        verbose=1,
        seed=args.seed,
        device="cpu",  # MLP policy runs better on CPU (GPU unsupported for sm_61)
        tensorboard_log=str(logs_dir),
        policy_kwargs={
            "net_arch": {
                "pi": [128, 128, 64],  # Policy network
                "vf": [128, 128, 64],  # Value network
            },
        },
    )

    # Set up callbacks
    callbacks = [
        StatsCallback(),
        CheckpointCallback(
            save_freq=args.checkpoint_freq,
            save_path=str(checkpoints_dir),
            name_prefix="sidebet_v1",
        ),
        EvalCallback(
            eval_env,
            best_model_save_path=str(output_dir),
            log_path=str(logs_dir),
            eval_freq=args.eval_freq,
            n_eval_episodes=50,
            deterministic=True,
        ),
    ]

    # Train
    print()
    print("=" * 60)
    print("STARTING TRAINING")
    print("=" * 60)
    print()

    try:
        model.learn(
            total_timesteps=args.timesteps,
            callback=callbacks,
            progress_bar=True,
        )
    except KeyboardInterrupt:
        print("\n\nTraining interrupted by user.")

    # Save final model
    print()
    print("Saving final model...")
    model.save(str(output_dir / "sidebet_v1_final"))
    train_env.save(str(output_dir / "vecnorm_sidebet_v1.pkl"))

    # Print final stats
    print()
    print("=" * 60)
    print("TRAINING COMPLETE")
    print("=" * 60)
    print(f"Model saved to: {output_dir / 'sidebet_v1_final.zip'}")
    print(f"VecNormalize saved to: {output_dir / 'vecnorm_sidebet_v1.pkl'}")
    print(f"Checkpoints in: {checkpoints_dir}")
    print(f"TensorBoard logs in: {logs_dir}")
    print()
    print("To view TensorBoard:")
    print(f"  tensorboard --logdir {logs_dir}")
    print()

    # Evaluate final model
    print("Running final evaluation...")
    from stable_baselines3.common.evaluation import evaluate_policy

    mean_reward, std_reward = evaluate_policy(
        model, eval_env, n_eval_episodes=100, deterministic=True
    )
    print(f"Final evaluation: {mean_reward:.3f} +/- {std_reward:.3f}")

    # Get environment stats
    base_env = train_env.envs[0].unwrapped
    if hasattr(base_env, "get_stats"):
        stats = base_env.get_stats()
        print()
        print("Environment Stats:")
        for k, v in stats.items():
            if isinstance(v, float):
                print(f"  {k}: {v:.4f}")
            else:
                print(f"  {k}: {v}")


if __name__ == "__main__":
    main()
