"""
ML Data Service - Read training runs and metrics.

Scans the Machine Learning/models/ directory for training runs and extracts
metrics from evaluations.npz files.
"""

import logging
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

# Base path for ML models (relative to project root)
# __file__ is in src/recording_ui/services/ml_data.py
# Project root is 4 levels up: services -> recording_ui -> src -> VECTRA-PLAYER
PROJECT_ROOT = Path(__file__).parent.parent.parent.parent
ML_MODELS_DIR = PROJECT_ROOT / "Machine Learning" / "models"


class MLDataService:
    """Service for reading ML training run data."""

    def __init__(self, models_dir: Path | None = None):
        """Initialize the ML data service.

        Args:
            models_dir: Override path to models directory (for testing)
        """
        self.models_dir = models_dir or ML_MODELS_DIR
        logger.info(f"MLDataService initialized, models_dir: {self.models_dir}")

    def get_all_runs(self, model_name: str = "sidebet-v1") -> list[dict[str, Any]]:
        """Get list of all training runs for a model.

        Args:
            model_name: Name of the model (subdirectory under models/)

        Returns:
            List of run metadata dicts, sorted by date (newest first)
        """
        runs_dir = self.models_dir / model_name / "runs"
        if not runs_dir.exists():
            logger.warning(f"Runs directory not found: {runs_dir}")
            return []

        runs = []
        for run_path in runs_dir.iterdir():
            if run_path.is_dir() and run_path.name.startswith("run"):
                run_info = self._get_run_summary(run_path)
                if run_info:
                    runs.append(run_info)

        # Sort by timestamp in run name (newest first)
        runs.sort(key=lambda x: x.get("run_id", ""), reverse=True)
        return runs

    def _get_run_summary(self, run_path: Path) -> dict[str, Any] | None:
        """Get summary metadata for a single run.

        Args:
            run_path: Path to run directory

        Returns:
            Dict with run_id, steps, has_best_model, etc.
        """
        try:
            run_id = run_path.name

            # Count checkpoint files to estimate steps
            checkpoints_dir = run_path / "checkpoints"
            if checkpoints_dir.exists():
                checkpoint_files = list(checkpoints_dir.glob("*.zip"))
                num_checkpoints = len(checkpoint_files)
                # Extract max steps from checkpoint names
                max_steps = 0
                for cp in checkpoint_files:
                    # Format: sidebet_v1_50000_steps.zip
                    parts = cp.stem.split("_")
                    for i, part in enumerate(parts):
                        if part == "steps" and i > 0:
                            try:
                                steps = int(parts[i - 1])
                                max_steps = max(max_steps, steps)
                            except ValueError:
                                pass
            else:
                num_checkpoints = 0
                max_steps = 0

            # Check for final model
            has_final = (run_path / "sidebet_v1_final.zip").exists()
            has_best = (run_path / "best_model.zip").exists()

            # Try to get evaluation metrics
            eval_summary = self._get_eval_summary(run_path)

            return {
                "run_id": run_id,
                "path": str(run_path),
                "max_steps": max_steps,
                "num_checkpoints": num_checkpoints,
                "has_final_model": has_final,
                "has_best_model": has_best,
                **eval_summary,
            }
        except Exception as e:
            logger.error(f"Error reading run {run_path}: {e}")
            return None

    def _get_eval_summary(self, run_path: Path) -> dict[str, Any]:
        """Extract summary stats from evaluations.npz.

        Args:
            run_path: Path to run directory

        Returns:
            Dict with win_rate, bet_rate, avg_reward, etc.
        """
        eval_path = run_path / "logs" / "evaluations.npz"
        if not eval_path.exists():
            return {"has_evaluations": False}

        try:
            data = np.load(eval_path)
            results = data["results"]  # shape: (num_evals, episodes_per_eval)
            timesteps = data["timesteps"]

            # Flatten all results for aggregate stats
            all_results = results.flatten()

            # Count outcomes based on reward values:
            # 4 = win (5:1 payout - 1 stake)
            # -1 = loss (lost bet)
            # 0, -0.5, -0.75 = various skip penalties
            wins = np.sum(all_results > 0)  # Positive = win
            losses = np.sum(all_results == -1)  # -1 = loss
            skips = np.sum((all_results <= 0) & (all_results != -1))  # 0, -0.5, -0.75

            total_bets = wins + losses
            total_episodes = len(all_results)

            win_rate = (wins / total_bets * 100) if total_bets > 0 else 0
            bet_rate = (total_bets / total_episodes * 100) if total_episodes > 0 else 0
            avg_reward = float(np.mean(all_results))

            # Get final evaluation stats (last row)
            final_results = results[-1]
            final_avg = float(np.mean(final_results))
            final_std = float(np.std(final_results))

            return {
                "has_evaluations": True,
                "total_episodes": int(total_episodes),
                "wins": int(wins),
                "losses": int(losses),
                "skips": int(skips),
                "win_rate": round(win_rate, 2),
                "bet_rate": round(bet_rate, 2),
                "avg_reward": round(avg_reward, 4),
                "final_avg_reward": round(final_avg, 3),
                "final_std_reward": round(final_std, 3),
                "num_evaluations": len(timesteps),
                "final_timestep": int(timesteps[-1]),
            }
        except Exception as e:
            logger.error(f"Error reading evaluations from {eval_path}: {e}")
            return {"has_evaluations": False, "eval_error": str(e)}

    def get_run_details(self, run_id: str, model_name: str = "sidebet-v1") -> dict[str, Any] | None:
        """Get detailed data for a specific run including chart data.

        Args:
            run_id: Run directory name (e.g., 'run_20260111_114335')
            model_name: Model name

        Returns:
            Dict with full run details and chart-ready data
        """
        run_path = self.models_dir / model_name / "runs" / run_id
        if not run_path.exists():
            return None

        # Get basic summary
        summary = self._get_run_summary(run_path)
        if not summary:
            return None

        # Add chart data
        chart_data = self._get_chart_data(run_path)
        summary["chart_data"] = chart_data

        return summary

    def _get_chart_data(self, run_path: Path) -> dict[str, Any]:
        """Extract data formatted for Chart.js rendering.

        Args:
            run_path: Path to run directory

        Returns:
            Dict with labels and datasets for Chart.js
        """
        eval_path = run_path / "logs" / "evaluations.npz"
        if not eval_path.exists():
            return {"error": "No evaluations found"}

        try:
            data = np.load(eval_path)
            results = data["results"]
            timesteps = data["timesteps"]

            # Compute mean reward per evaluation checkpoint
            mean_rewards = np.mean(results, axis=1).tolist()

            # Compute rolling win rate per checkpoint
            win_rates = []
            for row in results:
                wins = np.sum(row > 0)
                losses = np.sum(row == -1)
                total = wins + losses
                rate = (wins / total * 100) if total > 0 else 0
                win_rates.append(round(rate, 2))

            # Compute bet rate per checkpoint
            bet_rates = []
            for row in results:
                bets = np.sum(row != 0)  # Non-zero = placed bet or skip penalty
                # Actually: wins (>0) + losses (==-1) = bets placed
                wins = np.sum(row > 0)
                losses = np.sum(row == -1)
                rate = (wins + losses) / len(row) * 100
                bet_rates.append(round(rate, 2))

            return {
                "labels": [f"{int(t / 1000)}k" for t in timesteps],
                "timesteps": timesteps.tolist(),
                "mean_rewards": mean_rewards,
                "win_rates": win_rates,
                "bet_rates": bet_rates,
            }
        except Exception as e:
            logger.error(f"Error getting chart data: {e}")
            return {"error": str(e)}


# Singleton instance
ml_data_service = MLDataService()


def get_all_runs(model_name: str = "sidebet-v1") -> list[dict[str, Any]]:
    """Get all training runs."""
    return ml_data_service.get_all_runs(model_name)


def get_run_details(run_id: str, model_name: str = "sidebet-v1") -> dict[str, Any] | None:
    """Get details for a specific run."""
    return ml_data_service.get_run_details(run_id, model_name)
