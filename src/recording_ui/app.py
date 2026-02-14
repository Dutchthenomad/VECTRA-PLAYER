"""
Recording Dashboard - Flask Application.

Browser-based dashboard for monitoring and controlling game recording.

Opens as a new tab in the existing Chrome browser (if running), keeping
all VECTRA-PLAYER UIs in one window.

Startup: python -m recording_ui.app
         ./scripts/record.sh
"""

import argparse
import logging
import os
import threading
import time

from flask import Flask, jsonify, render_template, request
from flask_socketio import SocketIO, emit, join_room, leave_room

from recording_ui.services import explorer_data, ml_data, position_sizing
from recording_ui.services.backtest_service import get_backtest_service
from recording_ui.services.browser_service import get_browser_service
from recording_ui.services.chrome_tab import is_chrome_running, open_dashboard_tab
from recording_ui.services.control_service import ControlService
from recording_ui.services.data_service import DataService
from recording_ui.services.live_backtest_service import get_live_backtest_service
from recording_ui.services.profile_service import (
    MonteCarloMetrics,
    TradingProfile,
    get_profile_service,
)
from recording_ui.services.session_tracker import SessionTracker
from services.event_bus import event_bus
from services.event_store.service import EventStoreService

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Initialize Flask-SocketIO for live mode
# Restrict CORS to localhost origins only for security (trading application)
ALLOWED_ORIGINS = "*"  # Allow all for debugging
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# Initialize services
data_service = DataService()
control_service = ControlService()
session_tracker = SessionTracker()

# Initialize live backtest service with SocketIO
live_backtest_service = get_live_backtest_service(socketio)

# Initialize browser service for Chrome/trading integration
browser_service = get_browser_service(socketio)

# Guard against duplicate startup in Flask reloader/multi-worker setups
# Only start services if this is the main process (not a reloader child)
_services_started = False


def _start_background_services():
    """Start background services once (guard against reloader duplicates)."""
    global _services_started
    if _services_started:
        return

    # Check for Flask reloader - don't start in the reloader parent process
    # WERKZEUG_RUN_MAIN is set to 'true' in the child process
    if os.environ.get("WERKZEUG_RUN_MAIN") == "true" or not app.debug:
        event_bus.start()
        logger.info("EventBus processing thread started")

        global event_store_service
        event_store_service = EventStoreService(event_bus)
        event_store_service.start()
        logger.info("EventStoreService started for recording")

        _services_started = True
    else:
        logger.info("Skipping service startup in reloader parent process")


# Initialize EventStoreService placeholder (started in _start_background_services)
event_store_service = None

# Start services (with reloader guard)
_start_background_services()


# =============================================================================
# HTML ROUTES
# =============================================================================


@app.route("/")
def dashboard():
    """Render main dashboard page."""
    return render_template("dashboard.html")


@app.route("/debug")
def ws_debug():
    """WebSocket debug page - direct connection to rugs.fun."""
    return render_template("ws_debug.html")


@app.route("/stats")
def stats():
    """Server stats page - live WebSocket connection to rugs.fun."""
    return render_template("stats.html")


@app.route("/models")
def models():
    """ML Models dashboard - training run metrics and charts."""
    return render_template("models.html")


@app.route("/explorer")
def explorer():
    """Game Explorer - visualize games and multi-bet strategies."""
    return render_template("explorer.html")


@app.route("/backtest")
def backtest():
    """Backtest Viewer - visual strategy backtesting."""
    return render_template("backtest.html")


@app.route("/profiles")
def profiles():
    """Trading Profiles - unified profile manager with live testing."""
    return render_template("profiles.html")


# =============================================================================
# REST API - BACKTEST VIEWER
# =============================================================================


@app.route("/api/backtest/strategies")
def api_list_strategies():
    """List all saved strategies."""
    service = get_backtest_service()
    strategies = service.list_strategies()
    return jsonify({"strategies": strategies})


@app.route("/api/backtest/strategies/<name>")
def api_get_strategy(name: str):
    """Load a strategy by name."""
    service = get_backtest_service()
    strategy = service.load_strategy(name)
    if not strategy:
        return jsonify({"error": "Strategy not found"}), 404
    return jsonify(strategy)


@app.route("/api/backtest/strategies", methods=["POST"])
def api_save_strategy():
    """Save a strategy."""
    service = get_backtest_service()
    data = request.get_json() or {}
    try:
        name = service.save_strategy(data)
        return jsonify({"success": True, "name": name})
    except Exception as e:
        return jsonify({"error": str(e)}), 400


@app.route("/api/backtest/strategies/<name>", methods=["DELETE"])
def api_delete_strategy(name: str):
    """Delete a strategy."""
    service = get_backtest_service()
    success = service.delete_strategy(name)
    return jsonify({"success": success})


# =============================================================================
# PROFILE API ENDPOINTS (v2 Unified Trading Profiles)
# =============================================================================


@app.route("/api/profiles")
def api_list_profiles():
    """List all trading profiles with MC metrics summary."""
    service = get_profile_service()
    profiles = service.list_profiles()
    return jsonify({"profiles": profiles})


@app.route("/api/profiles/<name>")
def api_get_profile(name: str):
    """Load a trading profile by name."""
    service = get_profile_service()
    profile = service.load_profile(name)
    if not profile:
        return jsonify({"error": "Profile not found"}), 404
    return jsonify(profile.to_dict())


@app.route("/api/profiles", methods=["POST"])
def api_save_profile():
    """Save a trading profile."""
    service = get_profile_service()
    data = request.get_json() or {}

    try:
        profile = TradingProfile.from_dict(data)
        name = service.save_profile(profile)
        return jsonify({"success": True, "name": name})
    except Exception as e:
        logger.error(f"Failed to save profile: {e}")
        return jsonify({"error": str(e)}), 400


@app.route("/api/profiles/<name>", methods=["DELETE"])
def api_delete_profile(name: str):
    """Delete a trading profile."""
    service = get_profile_service()
    success = service.delete_profile(name)
    return jsonify({"success": success})


@app.route("/api/profiles/<name>/legacy")
def api_get_profile_legacy(name: str):
    """Get profile in legacy v1 format for backward compatibility."""
    service = get_profile_service()
    profile = service.load_profile(name)
    if not profile:
        return jsonify({"error": "Profile not found"}), 404
    return jsonify(profile.to_legacy_format())


@app.route("/api/profiles/import-mc/<strategy_key>", methods=["POST"])
def api_import_mc_strategy(strategy_key: str):
    """
    Import a Monte Carlo strategy as a trading profile.

    strategy_key: One of the 8 MC strategies (e.g., 'theta_bayesian_conservative')
    Request body can include:
      - name: Custom profile name (optional, defaults to strategy_key)
      - entry_tick: Override entry tick (optional, defaults to 219)
    """
    from recording_ui.services.monte_carlo_service import (
        STRATEGY_DESCRIPTIONS,
        create_strategy_configs,
        run_strategy_comparison,
    )

    if strategy_key not in STRATEGY_DESCRIPTIONS:
        valid_keys = list(STRATEGY_DESCRIPTIONS.keys())
        return jsonify(
            {
                "error": f"Unknown strategy: {strategy_key}",
                "valid_strategies": valid_keys,
            }
        ), 400

    data = request.get_json() or {}
    profile_name = data.get("name", strategy_key)
    entry_tick = data.get("entry_tick", 219)

    # Get the MC strategy config
    configs = create_strategy_configs(num_iterations=1000)
    mc_config = configs[strategy_key]
    meta = STRATEGY_DESCRIPTIONS[strategy_key]

    # Convert MC config to TradingProfile
    from recording_ui.services.monte_carlo import ScalingMode

    mode_map = {
        ScalingMode.FIXED: "fixed",
        ScalingMode.KELLY: "kelly",
        ScalingMode.ANTI_MARTINGALE: "anti_martingale",
        ScalingMode.THETA_BAYESIAN: "theta_bayesian",
        ScalingMode.VOLATILITY_ADJUSTED: "volatility_adjusted",
        ScalingMode.AGGRESSIVE_KELLY: "kelly",
    }

    profile = TradingProfile(
        name=profile_name,
        source="monte_carlo",
    )
    profile.execution.entry_tick = entry_tick
    profile.execution.num_bets = mc_config.num_bets_per_game
    profile.execution.bet_sizes = [mc_config.base_bet_size] * 4
    profile.execution.initial_balance = mc_config.initial_bankroll

    profile.scaling.mode = mode_map.get(mc_config.scaling_mode, "fixed")
    profile.scaling.kelly_fraction = mc_config.kelly_fraction
    profile.scaling.win_streak_multiplier = mc_config.win_streak_multiplier
    profile.scaling.max_streak_multiplier = mc_config.max_streak_multiplier
    profile.scaling.theta_base = mc_config.theta_base
    profile.scaling.theta_max = mc_config.theta_max
    profile.scaling.use_volatility_scaling = mc_config.use_volatility_scaling

    profile.risk_controls.max_drawdown_pct = mc_config.drawdown_halt
    profile.risk_controls.take_profit_target = mc_config.take_profit_target

    # Run quick MC simulation to get metrics
    try:
        results = run_strategy_comparison(num_iterations=1000)
        if strategy_key in results.get("strategies", {}):
            strat_results = results["strategies"][strategy_key]
            profile.monte_carlo_metrics = MonteCarloMetrics(
                computed_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                iterations=1000,
                win_rate_assumption=0.185,
                mean_final_bankroll=strat_results.get("summary", {}).get("mean_final_bankroll", 0),
                median_final_bankroll=strat_results.get("summary", {}).get(
                    "median_final_bankroll", 0
                ),
                probability_profit=strat_results.get("risk_metrics", {}).get(
                    "probability_profit", 0
                ),
                probability_2x=strat_results.get("risk_metrics", {}).get("probability_2x", 0),
                mean_max_drawdown=strat_results.get("drawdown", {}).get("mean_max_drawdown", 0),
                sortino_ratio=strat_results.get("performance", {}).get("sortino_ratio", 0),
                sharpe_ratio=strat_results.get("performance", {}).get("sharpe_ratio", 0),
                calmar_ratio=strat_results.get("performance", {}).get("calmar_ratio", 0),
                var_95=strat_results.get("var_metrics", {}).get("var_95", 0),
                cvar_95=strat_results.get("var_metrics", {}).get("cvar_95", 0),
                risk_level=meta.get("risk_level", "Unknown"),
            )
    except Exception as e:
        logger.warning(f"Failed to run MC for import: {e}")

    # Save the profile
    service = get_profile_service()
    saved_name = service.save_profile(profile)

    return jsonify(
        {
            "success": True,
            "name": saved_name,
            "profile": profile.to_dict(),
        }
    )


@app.route("/api/live/status")
def api_live_status():
    """Get current WebSocket connection status."""
    service = get_live_backtest_service(socketio)
    return jsonify(
        {
            "connected": service.is_connected,  # Use public property
            "active_sessions": len(service.sessions),
            "session_ids": list(service.sessions.keys()),
        }
    )


@app.route("/api/backtest/start", methods=["POST"])
def api_start_backtest():
    """Start a new backtest playback session."""
    service = get_backtest_service()
    data = request.get_json() or {}

    # Can pass strategy by name or inline
    if "strategy_name" in data:
        strategy = service.load_strategy(data["strategy_name"])
        if not strategy:
            return jsonify({"error": "Strategy not found"}), 404
    else:
        strategy = data.get("strategy", data)

    try:
        session_id = service.start_playback(strategy)
        state = service.get_state(session_id)
        return jsonify(
            {
                "success": True,
                "session_id": session_id,
                "state": state.to_dict() if state else None,
            }
        )
    except Exception as e:
        logger.error(f"Backtest start error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/backtest/state/<session_id>")
def api_get_backtest_state(session_id: str):
    """Get current state of a backtest session."""
    service = get_backtest_service()
    state = service.get_state(session_id)
    if not state:
        return jsonify({"error": "Session not found"}), 404
    return jsonify(state.to_dict())


@app.route("/api/backtest/tick/<session_id>", methods=["POST"])
def api_backtest_tick(session_id: str):
    """Advance one tick in the backtest."""
    service = get_backtest_service()
    state = service.get_state(session_id)
    if not state:
        return jsonify({"error": "Session not found"}), 404

    result = service.tick(session_id)
    return jsonify(result)


@app.route("/api/backtest/control/<session_id>", methods=["POST"])
def api_backtest_control(session_id: str):
    """Control backtest playback (pause/resume/speed/next)."""
    service = get_backtest_service()
    state = service.get_state(session_id)
    if not state:
        return jsonify({"error": "Session not found"}), 404

    data = request.get_json() or {}
    action = data.get("action")

    if action == "pause":
        service.pause(session_id)
    elif action == "resume":
        service.resume(session_id)
    elif action == "speed":
        service.set_speed(session_id, float(data.get("value", 1.0)))
    elif action in ("next", "next_game"):
        service.next_game(session_id)
    elif action == "stop":
        service.stop_session(session_id)
        return jsonify({"success": True, "stopped": True})

    state = service.get_state(session_id)
    return jsonify(state.to_dict() if state else {"stopped": True})


@app.route("/api/backtest/validation-info")
def api_validation_info():
    """Get info about the validation dataset."""
    service = get_backtest_service()
    try:
        games = service.get_validation_games()
        return jsonify(
            {
                "total_games": len(games),
                "sample_game_ids": [g["game_id"] for g in games[:5]],
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =============================================================================
# SOCKETIO - LIVE BACKTEST MODE
# =============================================================================


@socketio.on("join_live")
def handle_join_live(data):
    """
    Frontend joins live feed with strategy.

    Expected data:
        session_id: Unique session identifier
        strategy: Strategy configuration dict

    Emits:
        live_tick: {tick, session} on each game tick
    """
    session_id = data.get("session_id")
    strategy = data.get("strategy", {})

    if not session_id:
        emit("error", {"message": "session_id required"})
        return

    # Join the room for this session
    join_room(session_id)

    # Start the live session
    session = live_backtest_service.start_session(session_id, strategy)

    # Ensure WebSocket is connected
    live_backtest_service.ensure_ws_connected()

    # Send initial state - frontend expects 'live_joined' event
    emit(
        "live_joined",
        {
            "session_id": session_id,
            "session": session.to_dict(),
        },
    )

    logger.info(f"Client joined live session {session_id}")


@socketio.on("leave_live")
def handle_leave_live(data):
    """Frontend leaves live feed."""
    session_id = data.get("session_id")
    if session_id:
        leave_room(session_id)
        live_backtest_service.stop_session(session_id)
        logger.info(f"Client left live session {session_id}")


@socketio.on("get_live_state")
def handle_get_live_state(data):
    """Get current state of a live session."""
    session_id = data.get("session_id")
    session = live_backtest_service.get_session(session_id)
    if session:
        emit("live_state", {"session": session.to_dict()})
    else:
        emit("error", {"message": f"Session {session_id} not found"})


@socketio.on("connect")
def handle_connect():
    """Handle client connection."""
    logger.debug("SocketIO client connected")


@socketio.on("disconnect")
def handle_disconnect():
    """Handle client disconnection."""
    logger.debug("SocketIO client disconnected")


# =============================================================================
# REST API - GAME EXPLORER
# =============================================================================


@app.route("/api/explorer/data")
def api_explorer_data():
    """Get complete data for Game Explorer visualization.

    Query params:
        entry_tick: Tick to place first bet (default: 200)
        num_bets: Number of consecutive bets 1-4 (default: 4)
        limit: Max games for price curves (default: 50)

    Returns:
        JSON with strategy stats, games, histogram
    """
    entry_tick = request.args.get("entry_tick", 200, type=int)
    num_bets = request.args.get("num_bets", 4, type=int)
    limit = request.args.get("limit", 50, type=int)

    # Clamp values
    entry_tick = max(0, min(entry_tick, 1000))
    num_bets = max(1, min(num_bets, 4))
    limit = max(10, min(limit, 200))

    try:
        data = explorer_data.get_explorer_data(entry_tick, num_bets, limit)
        return jsonify(data)
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.error(f"Explorer data error: {e}")
        return jsonify({"error": "Failed to load data"}), 500


@app.route("/api/explorer/strategy")
def api_explorer_strategy():
    """Get strategy stats only (lightweight).

    Query params:
        entry_tick: Tick to place first bet (default: 200)
        num_bets: Number of consecutive bets 1-4 (default: 4)

    Returns:
        JSON with strategy statistics
    """
    entry_tick = request.args.get("entry_tick", 200, type=int)
    num_bets = request.args.get("num_bets", 4, type=int)

    entry_tick = max(0, min(entry_tick, 1000))
    num_bets = max(1, min(num_bets, 4))

    try:
        games_df = explorer_data.load_games_df()
        stats = explorer_data.calculate_strategy_stats(games_df, entry_tick, num_bets)
        return jsonify(stats)
    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404


@app.route("/api/explorer/simulate", methods=["POST"])
def api_explorer_simulate():
    """Run bankroll simulation with position sizing.

    POST body (JSON):
        initial_balance: Starting SOL (default: 0.1)
        entry_tick: Entry tick (default: 200)
        bet_sizes: Array of 4 bet sizes in SOL (default: [0.001, 0.001, 0.001, 0.001])
        max_drawdown_pct: Max drawdown before halt (default: 0.50)

        # Dynamic sizing options
        use_dynamic_sizing: Enable probability-based sizing (default: false)
        high_confidence_threshold: Probability threshold for larger bets (default: 60%)
        high_confidence_multiplier: Bet multiplier above threshold (default: 2.0)
        reduce_on_drawdown: Reduce bets when in drawdown (default: false)
        take_profit_target: Wallet multiplier to stop (e.g., 1.5 = +50% gain)

    Returns:
        JSON with simulation results, equity curve, risk metrics
    """
    try:
        data = request.get_json() or {}

        # Parse basic config
        initial_balance = float(data.get("initial_balance", 0.1))
        entry_tick = int(data.get("entry_tick", 200))
        bet_sizes = data.get("bet_sizes", [0.001, 0.001, 0.001, 0.001])
        max_drawdown = float(data.get("max_drawdown_pct", 0.50))

        # Parse dynamic sizing config
        use_dynamic_sizing = bool(data.get("use_dynamic_sizing", False))
        high_confidence_threshold = float(data.get("high_confidence_threshold", 60)) / 100
        high_confidence_multiplier = float(data.get("high_confidence_multiplier", 2.0))
        reduce_on_drawdown = bool(data.get("reduce_on_drawdown", False))
        take_profit_raw = data.get("take_profit_target")
        take_profit_target = float(take_profit_raw) if take_profit_raw else None

        # Parse Kelly sizing config
        use_kelly_sizing = bool(data.get("use_kelly_sizing", False))
        kelly_fraction = float(data.get("kelly_fraction", 0.25))

        # Validate basic params
        initial_balance = max(0.001, min(initial_balance, 100.0))
        entry_tick = max(0, min(entry_tick, 1000))
        bet_sizes = [max(0.0001, min(b, 1.0)) for b in bet_sizes[:4]]
        while len(bet_sizes) < 4:
            bet_sizes.append(0.001)
        max_drawdown = max(0.05, min(max_drawdown, 1.0))  # 5-100%

        # Validate dynamic sizing params
        high_confidence_threshold = max(0.20, min(high_confidence_threshold, 0.95))
        high_confidence_multiplier = max(1.0, min(high_confidence_multiplier, 10.0))
        if take_profit_target is not None:
            take_profit_target = max(1.01, min(take_profit_target, 100.0))

        # Validate Kelly sizing params
        kelly_fraction = max(0.05, min(kelly_fraction, 1.0))  # 5% to 100% of full Kelly

        # Create config
        config = position_sizing.WalletConfig(
            initial_balance=initial_balance,
            bet_sizes=bet_sizes,
            entry_tick=entry_tick,
            max_drawdown_pct=max_drawdown,
            use_dynamic_sizing=use_dynamic_sizing,
            high_confidence_threshold=high_confidence_threshold,
            high_confidence_multiplier=high_confidence_multiplier,
            reduce_on_drawdown=reduce_on_drawdown,
            take_profit_target=take_profit_target,
            use_kelly_sizing=use_kelly_sizing,
            kelly_fraction=kelly_fraction,
        )

        # Load games and run simulation
        games_df = explorer_data.load_games_df()
        result = position_sizing.run_simulation(games_df, config)

        return jsonify(position_sizing.simulation_to_dict(result))

    except FileNotFoundError as e:
        return jsonify({"error": str(e)}), 404
    except Exception as e:
        logger.error(f"Simulation error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/explorer/save-strategy", methods=["POST"])
def api_explorer_save_strategy():
    """Save current simulation config as a backtest strategy.

    POST body (JSON):
        name: Strategy name (required)
        initial_balance: Starting SOL
        entry_tick: Entry tick for first bet
        bet_sizes: Array of 4 bet sizes
        max_drawdown_pct: Max drawdown before halt
        take_profit_target: Target multiplier to exit
        use_kelly_sizing: Enable Kelly sizing
        kelly_fraction: Kelly fraction (0-1)
        use_dynamic_sizing: Enable dynamic sizing
        high_confidence_threshold: % threshold
        high_confidence_multiplier: Multiplier
        reduce_on_drawdown: Reduce bets on drawdown

    Returns:
        JSON with success status and saved name
    """
    data = request.get_json() or {}
    name = data.get("name")
    if not name:
        return jsonify({"error": "Strategy name required"}), 400

    # Map simulation config to backtest strategy format
    bet_sizes = data.get("bet_sizes", [0.001, 0.001, 0.001, 0.001])
    strategy = {
        "name": name,
        "initial_balance": data.get("initial_balance", 0.1),
        "params": {
            "entry_tick": data.get("entry_tick", 200),
            "num_bets": len(bet_sizes),
            "bet_sizes": bet_sizes,
            "use_kelly_sizing": data.get("use_kelly_sizing", False),
            "kelly_fraction": data.get("kelly_fraction", 0.25),
            "use_dynamic_sizing": data.get("use_dynamic_sizing", False),
            "high_confidence_threshold": data.get("high_confidence_threshold", 60),
            "high_confidence_multiplier": data.get("high_confidence_multiplier", 2.0),
            "reduce_on_drawdown": data.get("reduce_on_drawdown", False),
            "max_drawdown_pct": data.get("max_drawdown_pct", 0.50),
            "take_profit_target": data.get("take_profit_target"),
        },
    }

    try:
        service = get_backtest_service()
        saved_name = service.save_strategy(strategy)
        return jsonify({"success": True, "name": saved_name})
    except Exception as e:
        logger.error(f"Save strategy error: {e}")
        return jsonify({"error": str(e)}), 500


@app.route("/api/explorer/kelly")
def api_explorer_kelly():
    """Get Kelly Criterion bet size suggestions.

    Query params:
        win_rate: Win rate percentage (default: 20)
        initial_balance: Starting SOL (default: 0.1)
        num_bets: Number of bets (default: 4)

    Returns:
        JSON with Kelly calculations and suggested bet sizes
    """
    win_rate = request.args.get("win_rate", 20.0, type=float)
    initial_balance = request.args.get("initial_balance", 0.1, type=float)
    num_bets = request.args.get("num_bets", 4, type=int)

    win_rate = max(0, min(win_rate, 100))
    initial_balance = max(0.001, min(initial_balance, 100.0))
    num_bets = max(1, min(num_bets, 4))

    # Calculate Kelly
    kelly_full = position_sizing.kelly_criterion(win_rate / 100)
    kelly_quarter = position_sizing.fractional_kelly(win_rate / 100, fraction=0.25)
    kelly_half = position_sizing.fractional_kelly(win_rate / 100, fraction=0.5)

    # Suggested sizes
    suggested = position_sizing.suggest_kelly_sizing(
        win_rate, initial_balance, num_bets, kelly_fraction=0.25
    )

    # Progressive sizing suggestion
    progressive = position_sizing.calculate_progressive_sizes(
        base_size=0.001, num_bets=num_bets, multiplier=2.0
    )

    return jsonify(
        {
            "win_rate": win_rate,
            "initial_balance": initial_balance,
            "kelly": {
                "full": round(kelly_full, 4),
                "half": round(kelly_half, 4),
                "quarter": round(kelly_quarter, 4),
            },
            "suggested_sizes": {
                "kelly_quarter": suggested,
                "fixed_small": [0.001] * num_bets,
                "progressive_2x": progressive,
            },
            "analysis": {
                "edge_exists": kelly_full > 0,
                "recommended_strategy": "kelly_quarter" if kelly_full > 0 else "skip",
                "total_risk_kelly": round(sum(suggested), 4),
                "total_risk_progressive": round(sum(progressive), 4),
            },
        }
    )


@app.route("/api/explorer/monte-carlo", methods=["POST"])
def api_explorer_monte_carlo():
    """Run Monte Carlo comparison across all 8 scaling strategies.

    Request body:
        num_iterations: 1000, 10000, or 100000 (default: 10000)
        win_rate: Win rate as decimal (default: 0.185)
        initial_bankroll: Starting balance (default: 0.1)
        num_games: Games per simulation (default: 500)

    Returns:
        JSON with all strategy results, best performers, computation time
    """
    from .services.monte_carlo_service import run_strategy_comparison

    data = request.get_json() or {}

    # Validate iterations (only allow 1k, 10k, 100k)
    num_iterations = data.get("num_iterations", 10000)
    if num_iterations not in [1000, 10000, 100000]:
        num_iterations = 10000

    win_rate = data.get("win_rate", 0.185)
    initial_bankroll = data.get("initial_bankroll", 0.1)
    num_games = data.get("num_games", 500)

    try:
        results = run_strategy_comparison(
            num_iterations=num_iterations,
            initial_bankroll=initial_bankroll,
            win_rate=win_rate,
            num_games=num_games,
        )
        return jsonify(results)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# =============================================================================
# REST API - ML MODELS
# =============================================================================


@app.route("/api/models/runs")
def api_list_runs():
    """List all training runs.

    Query params:
        model: Model name (default: sidebet-v1)

    Returns:
        JSON with list of runs and their summary metrics
    """
    model_name = request.args.get("model", "sidebet-v1")
    runs = ml_data.get_all_runs(model_name)
    return jsonify(
        {
            "model": model_name,
            "runs": runs,
            "count": len(runs),
        }
    )


@app.route("/api/models/runs/<run_id>")
def api_run_details(run_id: str):
    """Get detailed data for a specific run including chart data.

    Args:
        run_id: Run directory name (e.g., 'run_20260111_114335')

    Query params:
        model: Model name (default: sidebet-v1)

    Returns:
        JSON with full run details and chart-ready data
    """
    model_name = request.args.get("model", "sidebet-v1")
    details = ml_data.get_run_details(run_id, model_name)
    if not details:
        return jsonify({"error": f"Run not found: {run_id}"}), 404
    return jsonify(details)


# =============================================================================
# REST API - STATUS
# =============================================================================


@app.route("/api/status")
def get_status():
    """Get current recording status and statistics.

    Returns session-specific stats (games recorded THIS session) plus totals.

    Per rugs-expert knowledge:
    - gameHistory is a 10-game rolling window (same game appears ~10x)
    - Must deduplicate by gameId for accurate counting
    - Session stats show unique games recorded since dashboard started
    """
    # Use EventStoreService directly for accurate recording status
    is_recording = event_store_service.is_recording
    event_count = event_store_service.event_count
    game_count = len(event_store_service.recorded_game_ids)

    session_stats = session_tracker.get_session_stats()
    total_stats = session_tracker.get_total_stats()

    return jsonify(
        {
            # Recording control status (from EventStoreService)
            "is_recording": is_recording,
            "uptime_seconds": 0,  # TODO: track uptime in EventStoreService
            "started_at": None,
            # SESSION stats from EventStoreService (this session, deduplicated)
            "session_game_count": game_count,
            "session_event_count": event_count,
            "session_start": session_stats["session_start"],
            "session_duration_seconds": session_stats["session_duration_seconds"],
            # TOTAL stats (all sessions ever, for context)
            "total_game_count": total_stats["total_game_count"],
            "total_event_count": total_stats["total_event_count"],
            "storage_mb": total_stats["storage_mb"],
            # Legacy fields (for backwards compatibility)
            "game_count": game_count,
            "event_count": event_count,
        }
    )


@app.route("/api/stats")
def get_stats():
    """Get data statistics (session + total).

    Returns:
        JSON with session and total stats
    """
    session_stats = session_tracker.get_session_stats()
    total_stats = session_tracker.get_total_stats()
    return jsonify(
        {
            **session_stats,
            **total_stats,
        }
    )


@app.route("/api/live/sessions")
def get_live_sessions():
    """Get list of active live paper trading sessions.

    Used by external clients (like alpha test) to discover active sessions
    and join them for mirroring.

    Returns:
        JSON with list of active session IDs and details
    """
    sessions = []
    for session_id, session in live_backtest_service.sessions.items():
        if session.is_active:
            sessions.append(
                {
                    "session_id": session_id,
                    "strategy_name": session.strategy.get("name", "unknown"),
                    "games_played": session.games_played,
                    "wallet": session.wallet,
                    "is_active": session.is_active,
                }
            )

    return jsonify(
        {
            "sessions": sessions,
            "count": len(sessions),
        }
    )


# =============================================================================
# REST API - RECORDING CONTROL
# =============================================================================


@app.route("/api/recording/start", methods=["POST"])
def start_recording():
    """Start recording.

    Returns:
        JSON with success status and new recording state
    """
    success = control_service.start_recording()
    return jsonify(
        {
            "success": success,
            "is_recording": control_service.is_recording(),
        }
    )


@app.route("/api/recording/stop", methods=["POST"])
def stop_recording():
    """Stop recording.

    Returns:
        JSON with success status and new recording state
    """
    success = control_service.stop_recording()
    return jsonify(
        {
            "success": success,
            "is_recording": control_service.is_recording(),
        }
    )


@app.route("/api/recording/toggle", methods=["POST"])
def toggle_recording():
    """Toggle recording state.

    Returns:
        JSON with new recording state
    """
    # Use EventStoreService directly since it's in the same process
    is_recording = event_store_service.toggle_recording()
    logger.info(f"Recording toggled: is_recording={is_recording}")
    return jsonify(
        {
            "success": True,
            "is_recording": is_recording,
        }
    )


# =============================================================================
# REST API - BROWSER CONTROL
# =============================================================================


@app.route("/api/browser/connect", methods=["POST"])
def browser_connect():
    """Connect to Chrome browser via CDP.

    Connects to the rugs_bot Chrome profile on port 9222.

    Returns:
        JSON with connection status
    """
    result = browser_service.connect()
    return jsonify(result)


@app.route("/api/browser/disconnect", methods=["POST"])
def browser_disconnect():
    """Disconnect from Chrome browser (keeps Chrome running).

    Returns:
        JSON with disconnection status
    """
    result = browser_service.disconnect()
    return jsonify(result)


@app.route("/api/browser/status")
def browser_status():
    """Get browser connection status and game state.

    Returns:
        JSON with connection status and current game state
    """
    result = browser_service.get_status()
    return jsonify(result)


# =============================================================================
# REST API - TRADING ACTIONS
# =============================================================================


@app.route("/api/trade/buy", methods=["POST"])
def trade_buy():
    """Execute BUY action in browser.

    Returns:
        JSON with action result
    """
    result = browser_service.click_buy()
    return jsonify(result)


@app.route("/api/trade/sell", methods=["POST"])
def trade_sell():
    """Execute SELL action in browser.

    Returns:
        JSON with action result
    """
    result = browser_service.click_sell()
    return jsonify(result)


@app.route("/api/trade/sidebet", methods=["POST"])
def trade_sidebet():
    """Execute SIDEBET action in browser.

    Returns:
        JSON with action result
    """
    result = browser_service.click_sidebet()
    return jsonify(result)


@app.route("/api/trade/increment", methods=["POST"])
def trade_increment():
    """Increment bet amount.

    Request body:
        {"amount": 0.001|0.01|0.1|1.0}

    Returns:
        JSON with action result
    """
    data = request.get_json() or {}
    amount = data.get("amount", 0.01)
    result = browser_service.click_increment(amount)
    return jsonify(result)


@app.route("/api/trade/percentage", methods=["POST"])
def trade_percentage():
    """Set sell percentage.

    Request body:
        {"pct": 10|25|50|100}

    Returns:
        JSON with action result
    """
    data = request.get_json() or {}
    pct = data.get("pct", 100)
    result = browser_service.click_percentage(pct)
    return jsonify(result)


@app.route("/api/trade/clear", methods=["POST"])
def trade_clear():
    """Clear bet to 0.

    Returns:
        JSON with action result
    """
    result = browser_service.click_clear()
    return jsonify(result)


@app.route("/api/trade/half", methods=["POST"])
def trade_half():
    """Halve current bet.

    Returns:
        JSON with action result
    """
    result = browser_service.click_half()
    return jsonify(result)


@app.route("/api/trade/double", methods=["POST"])
def trade_double():
    """Double current bet.

    Returns:
        JSON with action result
    """
    result = browser_service.click_double()
    return jsonify(result)


@app.route("/api/trade/max", methods=["POST"])
def trade_max():
    """Set bet to max balance.

    Returns:
        JSON with action result
    """
    result = browser_service.click_max()
    return jsonify(result)


# =============================================================================
# REST API - GAMES
# =============================================================================


@app.route("/api/games")
def get_games():
    """Get list of recorded games (session or all).

    Query params:
        limit: Maximum number of games (default 50)
        session_only: If true (default), show only this session's games

    Per rugs-expert knowledge:
    - gameHistory is 10-game rolling window
    - Games are deduplicated by gameId
    - Shows unique games recorded since dashboard started (by default)
    """
    limit = request.args.get("limit", 50, type=int)
    session_only = request.args.get("session_only", "true").lower() != "false"

    if session_only:
        games = session_tracker.get_session_games(limit=limit)
    else:
        games = data_service.get_games(limit=limit)

    return jsonify(
        {
            "games": games,
            "limit": limit,
            "count": len(games),
            "session_only": session_only,
        }
    )


@app.route("/api/games/<game_id>")
def get_game(game_id: str):
    """Get single game by ID.

    Returns:
        JSON with full game data, or 404 if not found
    """
    game = data_service.get_game(game_id)
    if not game:
        return jsonify({"error": "Game not found"}), 404

    return jsonify(game)


@app.route("/api/games/<game_id>/prices")
def get_game_prices(game_id: str):
    """Get price array for a specific game (for charting).

    Returns:
        JSON with prices array
    """
    prices = data_service.get_game_prices(game_id)
    return jsonify(
        {
            "game_id": game_id,
            "prices": prices,
            "count": len(prices),
        }
    )


# =============================================================================
# CHROME TAB OPENER
# =============================================================================


def open_in_chrome_delayed(url: str, delay: float = 1.5):
    """
    Open dashboard in Chrome after a delay (to let Flask start).

    Args:
        url: Dashboard URL to open
        delay: Seconds to wait before opening (default 1.5)
    """

    def _open():
        time.sleep(delay)
        if is_chrome_running():
            logger.info("Opening dashboard in Chrome (same window as rugs.fun)...")
            result = open_dashboard_tab(url)
            if result:
                logger.info(f"Dashboard tab opened: {url}")
            else:
                logger.warning("Failed to open Chrome tab - access manually")
        else:
            logger.info(f"Chrome not running on CDP port - open manually: {url}")

    thread = threading.Thread(target=_open, daemon=True, name="ChromeTabOpener")
    thread.start()


# =============================================================================
# MAIN
# =============================================================================


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="VECTRA Recording Dashboard")
    parser.add_argument(
        "--port",
        "-p",
        type=int,
        default=int(os.environ.get("PORT", 5000)),
        help="Port to run on (default: 5000)",
    )
    parser.add_argument("--no-browser", "-n", action="store_true", help="Don't auto-open in Chrome")
    parser.add_argument(
        "--debug",
        action="store_true",
        default=os.environ.get("FLASK_DEBUG", "false").lower() == "true",
        help="Run in debug mode",
    )
    return parser.parse_args()


def main():
    """Run the Flask development server."""
    args = parse_args()

    url = f"http://localhost:{args.port}"

    logger.info(f"Starting Recording Dashboard on {url}")
    logger.info(f"Data directory: {data_service.data_dir}")
    logger.info(f"Control file: {control_service.control_file}")

    # Auto-open in Chrome tab (unless disabled)
    if not args.no_browser:
        open_in_chrome_delayed(url)

    # Use socketio.run for WebSocket support (live mode)
    # allow_unsafe_werkzeug=True required for threading mode
    socketio.run(app, host="0.0.0.0", port=args.port, debug=args.debug, allow_unsafe_werkzeug=True)


if __name__ == "__main__":
    main()
