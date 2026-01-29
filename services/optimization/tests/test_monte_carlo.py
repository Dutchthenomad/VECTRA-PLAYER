"""Tests for Monte Carlo simulation module."""


class TestMonteCarlo:
    """Tests for Monte Carlo simulator."""

    def test_config_defaults(self):
        """Config should have sensible defaults."""
        from src.analyzers.monte_carlo import MonteCarloConfig

        config = MonteCarloConfig()

        assert config.initial_bankroll == 0.1
        assert config.base_bet_size == 0.001
        assert config.drawdown_halt == 0.15

    def test_simulator_runs(self):
        """Simulator should complete without error."""
        from src.analyzers.monte_carlo import MonteCarloConfig, MonteCarloSimulator

        config = MonteCarloConfig()
        sim = MonteCarloSimulator(config, seed=42)

        # Small run for speed
        results = sim.run(num_iterations=100, num_games=50, win_rate=0.185)

        assert isinstance(results, dict)
        assert "summary" in results
        assert "risk_metrics" in results

    def test_results_have_required_metrics(self):
        """Results should include all required metrics."""
        from src.analyzers.monte_carlo import MonteCarloConfig, MonteCarloSimulator

        config = MonteCarloConfig()
        sim = MonteCarloSimulator(config, seed=42)
        results = sim.run(num_iterations=100, num_games=50, win_rate=0.185)

        # Summary metrics
        assert "mean_final_bankroll" in results["summary"]
        assert "median_final_bankroll" in results["summary"]

        # Risk metrics
        assert "probability_profit" in results["risk_metrics"]
        assert "probability_ruin" in results["risk_metrics"]

        # Performance metrics
        assert "sharpe_ratio" in results["performance"]

    def test_seeded_runs_are_reproducible(self):
        """Same seed should produce same results."""
        from src.analyzers.monte_carlo import MonteCarloConfig, MonteCarloSimulator

        config = MonteCarloConfig()
        sim1 = MonteCarloSimulator(config, seed=42)
        sim2 = MonteCarloSimulator(config, seed=42)

        results1 = sim1.run(num_iterations=50, num_games=20, win_rate=0.185)
        results2 = sim2.run(num_iterations=50, num_games=20, win_rate=0.185)

        assert (
            results1["summary"]["mean_final_bankroll"] == results2["summary"]["mean_final_bankroll"]
        )
