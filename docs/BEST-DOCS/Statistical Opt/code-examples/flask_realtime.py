"""
Flask Real-time Dashboard Pattern

Demonstrates the Flask + SocketIO pattern for real-time game state
broadcasting used in VECTRA-PLAYER's dashboard.

Usage:
    from flask_realtime import create_app

    app = create_app()
    socketio = app.extensions['socketio']
    socketio.run(app, port=5000)
"""

import threading
import time
from dataclasses import asdict, dataclass
from typing import Any

from flask import Flask, jsonify, render_template_string
from flask_socketio import SocketIO, emit

# Simple template for demo
DASHBOARD_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Game Dashboard</title>
    <script src="https://cdnjs.cloudflare.com/ajax/libs/socket.io/4.0.1/socket.io.js"></script>
    <style>
        body { font-family: monospace; padding: 20px; background: #1a1a2e; color: #eee; }
        .stat { display: inline-block; margin: 10px; padding: 15px; background: #16213e; border-radius: 8px; }
        .value { font-size: 24px; font-weight: bold; color: #4ecca3; }
        #price.rising { color: #4ecca3; }
        #price.falling { color: #e94560; }
    </style>
</head>
<body>
    <h1>Game Dashboard</h1>
    <div class="stat">
        <div>Game ID</div>
        <div class="value" id="game_id">-</div>
    </div>
    <div class="stat">
        <div>Tick</div>
        <div class="value" id="tick">0</div>
    </div>
    <div class="stat">
        <div>Price</div>
        <div class="value" id="price">1.00x</div>
    </div>
    <div class="stat">
        <div>Status</div>
        <div class="value" id="status">Disconnected</div>
    </div>

    <script>
        const socket = io();
        let lastPrice = 1.0;

        socket.on('connect', () => {
            document.getElementById('status').textContent = 'Connected';
        });

        socket.on('disconnect', () => {
            document.getElementById('status').textContent = 'Disconnected';
        });

        socket.on('game_state', (data) => {
            document.getElementById('game_id').textContent = data.game_id || '-';
            document.getElementById('tick').textContent = data.tick || 0;

            const priceEl = document.getElementById('price');
            const price = data.price || 1.0;
            priceEl.textContent = price.toFixed(2) + 'x';
            priceEl.className = price >= lastPrice ? 'rising' : 'falling';
            lastPrice = price;
        });

        socket.on('game_ended', (data) => {
            console.log('Game ended:', data);
        });
    </script>
</body>
</html>
"""


@dataclass
class GameState:
    """Current game state."""

    game_id: str = ""
    tick: int = 0
    price: float = 1.0
    phase: str = "idle"
    connected_players: int = 0


def create_app() -> Flask:
    """
    Create Flask application with SocketIO.

    Returns:
        Configured Flask app
    """
    app = Flask(__name__)
    app.config["SECRET_KEY"] = "dev-secret-key"

    # Initialize SocketIO
    socketio = SocketIO(app, cors_allowed_origins="*")

    # Store state
    app.game_state = GameState()

    # Routes
    @app.route("/")
    def index():
        return render_template_string(DASHBOARD_TEMPLATE)

    @app.route("/api/state")
    def api_state():
        return jsonify(asdict(app.game_state))

    # SocketIO events
    @socketio.on("connect")
    def handle_connect():
        emit("game_state", asdict(app.game_state))

    @socketio.on("subscribe")
    def handle_subscribe(data):
        """Client subscribes to updates."""
        # Join room for targeted broadcasts
        from flask_socketio import join_room

        room = data.get("room", "game")
        join_room(room)
        emit("subscribed", {"room": room})

    return app


class GameStateBroadcaster:
    """
    Broadcasts game state updates via SocketIO.

    Integrates with EventBus to receive game events and
    broadcast to connected dashboard clients.
    """

    def __init__(self, socketio: SocketIO):
        self.socketio = socketio
        self._running = False
        self._state = GameState()

    def update_state(self, **kwargs):
        """
        Update game state and broadcast.

        Args:
            **kwargs: State fields to update
        """
        for key, value in kwargs.items():
            if hasattr(self._state, key):
                setattr(self._state, key, value)

        # Broadcast to all clients
        self.socketio.emit("game_state", asdict(self._state))

    def on_game_tick(self, event: dict):
        """Handle game tick event from EventBus."""
        self.update_state(
            game_id=event.get("game_id", ""),
            tick=event.get("tick", 0),
            price=event.get("price", 1.0),
            phase="active",
        )

    def on_game_ended(self, event: dict):
        """Handle game ended event."""
        self.update_state(phase="ended")
        self.socketio.emit("game_ended", event)

    def start_demo_broadcast(self, interval: float = 0.25):
        """Start demo broadcast with simulated data."""

        def broadcast_loop():
            tick = 0
            price = 1.0
            import random

            while self._running:
                tick += 1
                price *= 1 + random.uniform(-0.02, 0.03)
                price = max(0.5, min(50, price))

                self.update_state(
                    game_id="demo_game",
                    tick=tick,
                    price=price,
                    phase="active",
                )
                time.sleep(interval)

        self._running = True
        thread = threading.Thread(target=broadcast_loop, daemon=True)
        thread.start()

    def stop(self):
        """Stop demo broadcast."""
        self._running = False


# Integration with EventBus
def integrate_with_event_bus(socketio: SocketIO, event_bus: Any):
    """
    Connect SocketIO broadcaster to EventBus.

    Args:
        socketio: Flask-SocketIO instance
        event_bus: EventBus instance

    Example:
        from event_bus import get_event_bus, Events

        app = create_app()
        socketio = app.extensions['socketio']
        bus = get_event_bus()

        integrate_with_event_bus(socketio, bus)
    """
    broadcaster = GameStateBroadcaster(socketio)

    # Subscribe to game events
    @event_bus.subscribe("game.tick")
    def on_tick(event):
        broadcaster.on_game_tick(event.data)

    @event_bus.subscribe("game.ended")
    def on_ended(event):
        broadcaster.on_game_ended(event.data)

    return broadcaster


# Example usage
if __name__ == "__main__":
    app = create_app()
    socketio = app.extensions["socketio"]

    # Start demo broadcaster
    broadcaster = GameStateBroadcaster(socketio)
    broadcaster.start_demo_broadcast()

    print("Dashboard running at http://localhost:5000")
    socketio.run(app, host="0.0.0.0", port=5000, debug=False)
