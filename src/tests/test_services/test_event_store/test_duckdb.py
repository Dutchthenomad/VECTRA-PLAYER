"""
TDD Tests for DuckDB Query Layer

Issue #10: [Infra] DuckDB query layer

Tests written FIRST per TDD Iron Law.
"""

import uuid
from decimal import Decimal

import pandas as pd
import pyarrow as pa
import pytest

from services.event_store.paths import EventStorePaths
from services.event_store.schema import EventEnvelope, EventSource
from services.event_store.writer import ParquetWriter

# =============================================================================
# Fixtures
# =============================================================================


@pytest.fixture
def temp_data_dir(tmp_path):
    """Create temporary data directory for tests"""
    data_dir = tmp_path / "rugs_data"
    data_dir.mkdir()
    return data_dir


@pytest.fixture
def paths(temp_data_dir):
    """Create EventStorePaths with temp directory"""
    return EventStorePaths(data_dir=temp_data_dir)


@pytest.fixture
def populated_store(paths):
    """Create a store with sample data for query tests"""
    writer = ParquetWriter(paths, buffer_size=100, flush_interval=3600)
    session_id = str(uuid.uuid4())

    # Game 1: 10 ticks + 2 player actions
    game1_id = "game-001"
    for tick in range(10):
        writer.write(
            EventEnvelope.from_game_tick(
                tick=tick,
                price=Decimal(str(1.0 + tick * 0.1)),
                data={"tick": tick, "gameId": game1_id},
                source=EventSource.PUBLIC_WS,
                session_id=session_id,
                seq=tick,
                game_id=game1_id,
            )
        )

    writer.write(
        EventEnvelope.from_player_action(
            action_type="buy",
            data={"amount": 100},
            source=EventSource.UI,
            session_id=session_id,
            seq=100,
            game_id=game1_id,
            player_id="player-alice",
            username="Alice",
        )
    )
    writer.write(
        EventEnvelope.from_player_action(
            action_type="sell",
            data={"amount": 50},
            source=EventSource.UI,
            session_id=session_id,
            seq=101,
            game_id=game1_id,
            player_id="player-alice",
            username="Alice",
        )
    )

    # Game 2: 5 ticks (different player)
    game2_id = "game-002"
    for tick in range(5):
        writer.write(
            EventEnvelope.from_game_tick(
                tick=tick,
                price=Decimal(str(2.0 + tick * 0.2)),
                data={"tick": tick, "gameId": game2_id},
                source=EventSource.PUBLIC_WS,
                session_id=session_id,
                seq=200 + tick,
                game_id=game2_id,
            )
        )

    writer.write(
        EventEnvelope.from_player_action(
            action_type="buy",
            data={"amount": 200},
            source=EventSource.UI,
            session_id=session_id,
            seq=210,
            game_id=game2_id,
            player_id="player-bob",
            username="Bob",
        )
    )

    # Game 3: Alice plays again (for player filtering tests)
    game3_id = "game-003"
    for tick in range(3):
        writer.write(
            EventEnvelope.from_game_tick(
                tick=tick,
                price=Decimal(str(3.0 + tick * 0.3)),
                data={"tick": tick, "gameId": game3_id},
                source=EventSource.PUBLIC_WS,
                session_id=session_id,
                seq=300 + tick,
                game_id=game3_id,
            )
        )

    writer.write(
        EventEnvelope.from_player_action(
            action_type="buy",
            data={"amount": 150},
            source=EventSource.UI,
            session_id=session_id,
            seq=310,
            game_id=game3_id,
            player_id="player-alice",
            username="Alice",
        )
    )

    writer.close()

    return {
        "paths": paths,
        "session_id": session_id,
        "games": {
            "game-001": {"ticks": 10, "player": "player-alice"},
            "game-002": {"ticks": 5, "player": "player-bob"},
            "game-003": {"ticks": 3, "player": "player-alice"},
        },
    }


# =============================================================================
# Instantiation Tests
# =============================================================================


class TestEventStoreQueryInstantiation:
    """Tests for EventStoreQuery initialization"""

    def test_instantiate_with_paths(self, paths):
        """EventStoreQuery can be instantiated with EventStorePaths"""
        from services.event_store.duckdb import EventStoreQuery

        query = EventStoreQuery(paths)
        assert query is not None

    def test_instantiate_with_defaults(self):
        """EventStoreQuery can be instantiated with no arguments"""
        from services.event_store.duckdb import EventStoreQuery

        query = EventStoreQuery()
        assert query is not None


# =============================================================================
# Core Query Tests
# =============================================================================


class TestCoreQueryMethods:
    """Tests for raw SQL query methods"""

    def test_query_returns_dataframe(self, populated_store):
        """query() returns pandas DataFrame"""
        from services.event_store.duckdb import EventStoreQuery

        query = EventStoreQuery(populated_store["paths"])
        result = query.query("SELECT 1 as value")

        assert isinstance(result, pd.DataFrame)
        assert len(result) == 1
        assert result.iloc[0]["value"] == 1

    def test_query_with_parquet_glob(self, populated_store):
        """query() can read from Parquet files"""
        from services.event_store.duckdb import EventStoreQuery

        query = EventStoreQuery(populated_store["paths"])
        parquet_glob = str(populated_store["paths"].events_parquet_dir / "**/*.parquet")
        result = query.query(f"SELECT COUNT(*) as cnt FROM '{parquet_glob}'")

        assert result.iloc[0]["cnt"] > 0

    def test_query_arrow_returns_arrow_table(self, populated_store):
        """query_arrow() returns PyArrow Table"""
        from services.event_store.duckdb import EventStoreQuery

        query = EventStoreQuery(populated_store["paths"])
        result = query.query_arrow("SELECT 1 as value, 'test' as name")

        assert isinstance(result, pa.Table)
        assert result.num_rows == 1

    def test_query_with_params(self, populated_store):
        """query() supports parameterized queries"""
        from services.event_store.duckdb import EventStoreQuery

        query = EventStoreQuery(populated_store["paths"])
        result = query.query(
            "SELECT $value as result",
            params={"value": 42},
        )

        assert result.iloc[0]["result"] == 42


# =============================================================================
# Game Episode Tests
# =============================================================================


class TestGameEpisodeExtraction:
    """Tests for game episode extraction (RL training primary use case)"""

    def test_get_game_episode_returns_dataframe(self, populated_store):
        """get_game_episode() returns DataFrame for a game"""
        from services.event_store.duckdb import EventStoreQuery

        query = EventStoreQuery(populated_store["paths"])
        episode = query.get_game_episode("game-001")

        assert isinstance(episode, pd.DataFrame)
        assert len(episode) > 0

    def test_get_game_episode_contains_all_events(self, populated_store):
        """get_game_episode() returns all event types for the game"""
        from services.event_store.duckdb import EventStoreQuery

        query = EventStoreQuery(populated_store["paths"])
        episode = query.get_game_episode("game-001")

        # Game 1 has 10 ticks + 2 player actions = 12 events
        assert len(episode) == 12

    def test_get_game_episode_sorted_by_seq(self, populated_store):
        """get_game_episode() returns events sorted by sequence number"""
        from services.event_store.duckdb import EventStoreQuery

        query = EventStoreQuery(populated_store["paths"])
        episode = query.get_game_episode("game-001")

        seqs = episode["seq"].tolist()
        assert seqs == sorted(seqs)

    def test_get_game_episode_nonexistent_returns_empty(self, populated_store):
        """get_game_episode() returns empty DataFrame for nonexistent game"""
        from services.event_store.duckdb import EventStoreQuery

        query = EventStoreQuery(populated_store["paths"])
        episode = query.get_game_episode("nonexistent-game")

        assert isinstance(episode, pd.DataFrame)
        assert len(episode) == 0

    def test_iter_episodes_yields_dataframes(self, populated_store):
        """iter_episodes() yields DataFrame per game"""
        from services.event_store.duckdb import EventStoreQuery

        query = EventStoreQuery(populated_store["paths"])
        episodes = list(query.iter_episodes())

        assert len(episodes) == 3  # 3 games
        for ep in episodes:
            assert isinstance(ep, pd.DataFrame)

    def test_iter_episodes_with_player_filter(self, populated_store):
        """iter_episodes() can filter by player_id"""
        from services.event_store.duckdb import EventStoreQuery

        query = EventStoreQuery(populated_store["paths"])
        episodes = list(query.iter_episodes(player_id="player-alice"))

        # Alice played in game-001 and game-003
        assert len(episodes) == 2

    def test_iter_episodes_with_limit(self, populated_store):
        """iter_episodes() respects limit parameter"""
        from services.event_store.duckdb import EventStoreQuery

        query = EventStoreQuery(populated_store["paths"])
        episodes = list(query.iter_episodes(limit=2))

        assert len(episodes) == 2

    def test_iter_episodes_with_min_ticks(self, populated_store):
        """iter_episodes() can filter by minimum tick count"""
        from services.event_store.duckdb import EventStoreQuery

        query = EventStoreQuery(populated_store["paths"])
        episodes = list(query.iter_episodes(min_ticks=5))

        # Only game-001 (10 ticks) and game-002 (5 ticks) qualify
        assert len(episodes) == 2

    def test_get_episodes_batch(self, populated_store):
        """get_episodes_batch() returns dict of DataFrames"""
        from services.event_store.duckdb import EventStoreQuery

        query = EventStoreQuery(populated_store["paths"])
        episodes = query.get_episodes_batch(["game-001", "game-002"])

        assert isinstance(episodes, dict)
        assert "game-001" in episodes
        assert "game-002" in episodes
        assert len(episodes["game-001"]) == 12  # 10 ticks + 2 actions
        assert len(episodes["game-002"]) == 6  # 5 ticks + 1 action


# =============================================================================
# Player Query Tests
# =============================================================================


class TestPlayerQueries:
    """Tests for player-focused queries"""

    def test_get_player_games(self, populated_store):
        """get_player_games() returns all events from player's games"""
        from services.event_store.duckdb import EventStoreQuery

        query = EventStoreQuery(populated_store["paths"])
        result = query.get_player_games("player-alice")

        assert isinstance(result, pd.DataFrame)
        # Alice's games: game-001 (12 events) + game-003 (4 events) = 16
        assert len(result) == 16

    def test_get_player_actions(self, populated_store):
        """get_player_actions() returns only player_action events"""
        from services.event_store.duckdb import EventStoreQuery

        query = EventStoreQuery(populated_store["paths"])
        result = query.get_player_actions("player-alice")

        assert isinstance(result, pd.DataFrame)
        # Alice: 2 actions in game-001 + 1 in game-003 = 3
        assert len(result) == 3
        assert all(result["doc_type"] == "player_action")

    def test_get_player_games_with_limit(self, populated_store):
        """get_player_games() respects limit"""
        from services.event_store.duckdb import EventStoreQuery

        query = EventStoreQuery(populated_store["paths"])
        result = query.get_player_games("player-alice", limit=5)

        assert len(result) <= 5


# =============================================================================
# Discovery / Listing Tests
# =============================================================================


class TestDiscoveryMethods:
    """Tests for listing and discovery methods"""

    def test_list_games(self, populated_store):
        """list_games() returns unique game IDs"""
        from services.event_store.duckdb import EventStoreQuery

        query = EventStoreQuery(populated_store["paths"])
        games = query.list_games()

        assert isinstance(games, list)
        assert len(games) == 3
        assert "game-001" in games
        assert "game-002" in games
        assert "game-003" in games

    def test_list_games_with_limit(self, populated_store):
        """list_games() respects limit"""
        from services.event_store.duckdb import EventStoreQuery

        query = EventStoreQuery(populated_store["paths"])
        games = query.list_games(limit=2)

        assert len(games) == 2

    def test_list_players(self, populated_store):
        """list_players() returns unique player IDs"""
        from services.event_store.duckdb import EventStoreQuery

        query = EventStoreQuery(populated_store["paths"])
        players = query.list_players()

        assert isinstance(players, list)
        assert len(players) == 2
        assert "player-alice" in players
        assert "player-bob" in players

    def test_count_events_total(self, populated_store):
        """count_events() returns total event count"""
        from services.event_store.duckdb import EventStoreQuery

        query = EventStoreQuery(populated_store["paths"])
        count = query.count_events()

        # 10 + 2 + 5 + 1 + 3 + 1 = 22 events
        assert count == 22

    def test_count_events_by_doc_type(self, populated_store):
        """count_events() can filter by doc_type"""
        from services.event_store.duckdb import EventStoreQuery

        query = EventStoreQuery(populated_store["paths"])
        tick_count = query.count_events(doc_type="game_tick")

        # 10 + 5 + 3 = 18 ticks
        assert tick_count == 18


# =============================================================================
# Feature Engineering Tests
# =============================================================================


class TestFeatureEngineering:
    """Tests for SQL window function feature extraction"""

    def test_get_tick_features_returns_dataframe(self, populated_store):
        """get_tick_features() returns DataFrame with computed features"""
        from services.event_store.duckdb import EventStoreQuery

        query = EventStoreQuery(populated_store["paths"])
        features = query.get_tick_features("game-001")

        assert isinstance(features, pd.DataFrame)
        assert len(features) == 10  # Only ticks, not actions

    def test_get_tick_features_has_price_change(self, populated_store):
        """get_tick_features() includes price_change column"""
        from services.event_store.duckdb import EventStoreQuery

        query = EventStoreQuery(populated_store["paths"])
        features = query.get_tick_features("game-001")

        assert "price_change" in features.columns
        # First tick has no previous, so None/NaN
        assert pd.isna(features.iloc[0]["price_change"])
        # Second tick: 1.1 - 1.0 = 0.1
        assert abs(features.iloc[1]["price_change"] - 0.1) < 0.001

    def test_get_tick_features_has_volatility(self, populated_store):
        """get_tick_features() includes volatility columns"""
        from services.event_store.duckdb import EventStoreQuery

        query = EventStoreQuery(populated_store["paths"])
        features = query.get_tick_features("game-001")

        assert "volatility_5" in features.columns
        assert "volatility_10" in features.columns

    def test_get_tick_features_has_drawdown(self, populated_store):
        """get_tick_features() includes max_price and drawdown"""
        from services.event_store.duckdb import EventStoreQuery

        query = EventStoreQuery(populated_store["paths"])
        features = query.get_tick_features("game-001")

        assert "max_price" in features.columns
        assert "drawdown" in features.columns
        # Max price should be monotonically increasing (prices go up in test data)
        max_prices = features["max_price"].tolist()
        assert max_prices == sorted(max_prices)

    def test_get_tick_features_sorted_by_tick(self, populated_store):
        """get_tick_features() returns ticks in order"""
        from services.event_store.duckdb import EventStoreQuery

        query = EventStoreQuery(populated_store["paths"])
        features = query.get_tick_features("game-001")

        ticks = features["tick"].tolist()
        assert ticks == list(range(10))


# =============================================================================
# Empty Store Tests
# =============================================================================


class TestEmptyStore:
    """Tests for queries on empty store"""

    def test_list_games_empty(self, paths):
        """list_games() returns empty list on empty store"""
        from services.event_store.duckdb import EventStoreQuery

        query = EventStoreQuery(paths)
        games = query.list_games()

        assert games == []

    def test_count_events_empty(self, paths):
        """count_events() returns 0 on empty store"""
        from services.event_store.duckdb import EventStoreQuery

        query = EventStoreQuery(paths)
        count = query.count_events()

        assert count == 0

    def test_iter_episodes_empty(self, paths):
        """iter_episodes() yields nothing on empty store"""
        from services.event_store.duckdb import EventStoreQuery

        query = EventStoreQuery(paths)
        episodes = list(query.iter_episodes())

        assert episodes == []


# =============================================================================
# Thread Safety Tests
# =============================================================================


class TestThreadSafety:
    """Tests for concurrent query access"""

    def test_concurrent_queries(self, populated_store):
        """Multiple threads can query concurrently"""
        import threading

        from services.event_store.duckdb import EventStoreQuery

        query = EventStoreQuery(populated_store["paths"])
        results = []
        errors = []

        def run_query(game_id: str):
            try:
                episode = query.get_game_episode(game_id)
                results.append((game_id, len(episode)))
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=run_query, args=(f"game-00{i}",)) for i in range(1, 4)]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread errors: {errors}"
        assert len(results) == 3
