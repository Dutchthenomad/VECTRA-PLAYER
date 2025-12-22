"""
Tests for legacy recorder deprecation flags in Config class.

Tests verify that:
1. Default values are True (backwards compatibility)
2. Environment variables control each flag
3. All common boolean string variants are recognized
4. Flags are independent and don't affect each other
"""

from config import Config


class TestLegacyFlags:
    """Tests for get_legacy_flags() method"""

    def test_default_values_all_true(self, monkeypatch):
        """All legacy flags should default to True for backwards compatibility"""
        # Clear all legacy env vars to ensure defaults
        for key in [
            "LEGACY_RECORDER_SINK",
            "LEGACY_DEMO_RECORDER",
            "LEGACY_RAW_CAPTURE",
            "LEGACY_UNIFIED_RECORDER",
            "LEGACY_GAME_STATE_RECORDER",
            "LEGACY_PLAYER_SESSION_RECORDER",
        ]:
            monkeypatch.delenv(key, raising=False)

        flags = Config.get_legacy_flags()

        assert flags == {
            "enable_recorder_sink": True,
            "enable_demo_recorder": True,
            "enable_raw_capture": True,
            "enable_unified_recorder": True,
            "enable_game_state_recorder": True,
            "enable_player_session_recorder": True,
        }

    def test_all_flags_present(self, monkeypatch):
        """Verify all expected flag keys are present"""
        for key in [
            "LEGACY_RECORDER_SINK",
            "LEGACY_DEMO_RECORDER",
            "LEGACY_RAW_CAPTURE",
            "LEGACY_UNIFIED_RECORDER",
            "LEGACY_GAME_STATE_RECORDER",
            "LEGACY_PLAYER_SESSION_RECORDER",
        ]:
            monkeypatch.delenv(key, raising=False)

        flags = Config.get_legacy_flags()

        expected_keys = {
            "enable_recorder_sink",
            "enable_demo_recorder",
            "enable_raw_capture",
            "enable_unified_recorder",
            "enable_game_state_recorder",
            "enable_player_session_recorder",
        }
        assert set(flags.keys()) == expected_keys

    def test_recorder_sink_flag(self, monkeypatch):
        """Test LEGACY_RECORDER_SINK environment variable"""
        monkeypatch.setenv("LEGACY_RECORDER_SINK", "false")
        flags = Config.get_legacy_flags()
        assert flags["enable_recorder_sink"] is False

        monkeypatch.setenv("LEGACY_RECORDER_SINK", "true")
        flags = Config.get_legacy_flags()
        assert flags["enable_recorder_sink"] is True

    def test_demo_recorder_flag(self, monkeypatch):
        """Test LEGACY_DEMO_RECORDER environment variable"""
        monkeypatch.setenv("LEGACY_DEMO_RECORDER", "false")
        flags = Config.get_legacy_flags()
        assert flags["enable_demo_recorder"] is False

        monkeypatch.setenv("LEGACY_DEMO_RECORDER", "true")
        flags = Config.get_legacy_flags()
        assert flags["enable_demo_recorder"] is True

    def test_raw_capture_flag(self, monkeypatch):
        """Test LEGACY_RAW_CAPTURE environment variable"""
        monkeypatch.setenv("LEGACY_RAW_CAPTURE", "false")
        flags = Config.get_legacy_flags()
        assert flags["enable_raw_capture"] is False

        monkeypatch.setenv("LEGACY_RAW_CAPTURE", "true")
        flags = Config.get_legacy_flags()
        assert flags["enable_raw_capture"] is True

    def test_unified_recorder_flag(self, monkeypatch):
        """Test LEGACY_UNIFIED_RECORDER environment variable"""
        monkeypatch.setenv("LEGACY_UNIFIED_RECORDER", "false")
        flags = Config.get_legacy_flags()
        assert flags["enable_unified_recorder"] is False

        monkeypatch.setenv("LEGACY_UNIFIED_RECORDER", "true")
        flags = Config.get_legacy_flags()
        assert flags["enable_unified_recorder"] is True

    def test_game_state_recorder_flag(self, monkeypatch):
        """Test LEGACY_GAME_STATE_RECORDER environment variable"""
        monkeypatch.setenv("LEGACY_GAME_STATE_RECORDER", "false")
        flags = Config.get_legacy_flags()
        assert flags["enable_game_state_recorder"] is False

        monkeypatch.setenv("LEGACY_GAME_STATE_RECORDER", "true")
        flags = Config.get_legacy_flags()
        assert flags["enable_game_state_recorder"] is True

    def test_player_session_recorder_flag(self, monkeypatch):
        """Test LEGACY_PLAYER_SESSION_RECORDER environment variable"""
        monkeypatch.setenv("LEGACY_PLAYER_SESSION_RECORDER", "false")
        flags = Config.get_legacy_flags()
        assert flags["enable_player_session_recorder"] is False

        monkeypatch.setenv("LEGACY_PLAYER_SESSION_RECORDER", "true")
        flags = Config.get_legacy_flags()
        assert flags["enable_player_session_recorder"] is True

    def test_flags_are_independent(self, monkeypatch):
        """Changing one flag should not affect others"""
        # Set only one flag to false
        monkeypatch.setenv("LEGACY_RECORDER_SINK", "false")

        flags = Config.get_legacy_flags()

        # Only the set flag should be False
        assert flags["enable_recorder_sink"] is False
        assert flags["enable_demo_recorder"] is True
        assert flags["enable_raw_capture"] is True
        assert flags["enable_unified_recorder"] is True
        assert flags["enable_game_state_recorder"] is True
        assert flags["enable_player_session_recorder"] is True

    def test_mixed_flag_states(self, monkeypatch):
        """Test with some flags enabled and some disabled"""
        monkeypatch.setenv("LEGACY_RECORDER_SINK", "false")
        monkeypatch.setenv("LEGACY_DEMO_RECORDER", "true")
        monkeypatch.setenv("LEGACY_RAW_CAPTURE", "false")
        monkeypatch.setenv("LEGACY_UNIFIED_RECORDER", "true")

        flags = Config.get_legacy_flags()

        assert flags["enable_recorder_sink"] is False
        assert flags["enable_demo_recorder"] is True
        assert flags["enable_raw_capture"] is False
        assert flags["enable_unified_recorder"] is True
        assert flags["enable_game_state_recorder"] is True  # Default
        assert flags["enable_player_session_recorder"] is True  # Default

    def test_all_flags_disabled(self, monkeypatch):
        """Test disabling all legacy recorders"""
        for key in [
            "LEGACY_RECORDER_SINK",
            "LEGACY_DEMO_RECORDER",
            "LEGACY_RAW_CAPTURE",
            "LEGACY_UNIFIED_RECORDER",
            "LEGACY_GAME_STATE_RECORDER",
            "LEGACY_PLAYER_SESSION_RECORDER",
        ]:
            monkeypatch.setenv(key, "false")

        flags = Config.get_legacy_flags()

        assert all(value is False for value in flags.values())


class TestBoolEnvMethod:
    """Tests for _get_bool_env() helper method"""

    def test_true_variants(self, monkeypatch):
        """Test all recognized true values"""
        test_cases = [
            ("true", True),
            ("True", True),
            ("TRUE", True),
            ("1", True),
            ("yes", True),
            ("Yes", True),
            ("YES", True),
        ]

        for env_value, expected in test_cases:
            monkeypatch.setenv("TEST_BOOL_ENV", env_value)
            result = Config._get_bool_env("TEST_BOOL_ENV", False)
            assert result is expected, f"Failed for value: {env_value}"

    def test_false_variants(self, monkeypatch):
        """Test all recognized false values"""
        test_cases = [
            ("false", False),
            ("False", False),
            ("FALSE", False),
            ("0", False),
            ("no", False),
            ("No", False),
            ("NO", False),
            ("anything_else", False),
            ("", False),
        ]

        for env_value, expected in test_cases:
            monkeypatch.setenv("TEST_BOOL_ENV", env_value)
            result = Config._get_bool_env("TEST_BOOL_ENV", False)
            assert result is expected, f"Failed for value: {env_value}"

    def test_default_when_missing(self, monkeypatch):
        """Test default value is used when env var is not set"""
        monkeypatch.delenv("TEST_BOOL_ENV", raising=False)

        # Test default True
        result = Config._get_bool_env("TEST_BOOL_ENV", True)
        assert result is True

        # Test default False
        result = Config._get_bool_env("TEST_BOOL_ENV", False)
        assert result is False

    def test_case_insensitive(self, monkeypatch):
        """Test that boolean parsing is case insensitive"""
        test_values = ["true", "True", "TRUE", "TrUe", "tRuE"]

        for value in test_values:
            monkeypatch.setenv("TEST_BOOL_ENV", value)
            result = Config._get_bool_env("TEST_BOOL_ENV", False)
            assert result is True, f"Failed for value: {value}"

    def test_whitespace_handling(self, monkeypatch):
        """Test that whitespace is not stripped (invalid values return False)"""
        # Note: The implementation doesn't strip whitespace, so these should be False
        test_cases = [
            (" true", False),  # Leading space
            ("true ", False),  # Trailing space
            (" true ", False),  # Both
        ]

        for env_value, expected in test_cases:
            monkeypatch.setenv("TEST_BOOL_ENV", env_value)
            result = Config._get_bool_env("TEST_BOOL_ENV", True)
            assert result is expected, f"Failed for value: '{env_value}'"


class TestIntegrationWithConfig:
    """Integration tests with the full Config class"""

    def test_legacy_flags_accessible_via_instance(self, monkeypatch):
        """Test that legacy flags are accessible via Config instance"""
        monkeypatch.setenv("LEGACY_RECORDER_SINK", "false")

        config = Config(validate=False, ensure_directories=False)
        flags = config.get_legacy_flags()

        assert flags["enable_recorder_sink"] is False

    def test_legacy_flags_accessible_via_class(self, monkeypatch):
        """Test that legacy flags are accessible via Config class method"""
        monkeypatch.setenv("LEGACY_DEMO_RECORDER", "false")

        flags = Config.get_legacy_flags()

        assert flags["enable_demo_recorder"] is False

    def test_legacy_flags_do_not_affect_other_config(self, monkeypatch):
        """Ensure legacy flags don't interfere with other configuration"""
        monkeypatch.setenv("LEGACY_RECORDER_SINK", "false")

        config = Config(validate=False, ensure_directories=False)
        flags = config.get_legacy_flags()
        data_config = config.get_data_config()

        # Legacy flags should be independent
        assert flags["enable_recorder_sink"] is False

        # Other config should be unaffected
        assert "data_dir" in data_config
        assert "schema_version" in data_config

    def test_multiple_calls_return_fresh_values(self, monkeypatch):
        """Test that changing env vars between calls affects the result"""
        monkeypatch.setenv("LEGACY_RECORDER_SINK", "true")
        flags1 = Config.get_legacy_flags()
        assert flags1["enable_recorder_sink"] is True

        # Change env var
        monkeypatch.setenv("LEGACY_RECORDER_SINK", "false")
        flags2 = Config.get_legacy_flags()
        assert flags2["enable_recorder_sink"] is False


class TestDocumentation:
    """Tests for documentation and method signature"""

    def test_method_exists(self):
        """Verify get_legacy_flags method exists"""
        assert hasattr(Config, "get_legacy_flags")
        assert callable(Config.get_legacy_flags)

    def test_method_is_classmethod(self):
        """Verify get_legacy_flags is a classmethod"""
        import inspect

        assert isinstance(inspect.getattr_static(Config, "get_legacy_flags"), classmethod)

    def test_method_has_docstring(self):
        """Verify method has documentation"""
        assert Config.get_legacy_flags.__doc__ is not None
        assert len(Config.get_legacy_flags.__doc__) > 0

    def test_returns_dict(self, monkeypatch):
        """Verify return type is dict"""
        for key in [
            "LEGACY_RECORDER_SINK",
            "LEGACY_DEMO_RECORDER",
            "LEGACY_RAW_CAPTURE",
            "LEGACY_UNIFIED_RECORDER",
            "LEGACY_GAME_STATE_RECORDER",
            "LEGACY_PLAYER_SESSION_RECORDER",
        ]:
            monkeypatch.delenv(key, raising=False)

        result = Config.get_legacy_flags()
        assert isinstance(result, dict)

    def test_all_values_are_bool(self, monkeypatch):
        """Verify all returned values are booleans"""
        for key in [
            "LEGACY_RECORDER_SINK",
            "LEGACY_DEMO_RECORDER",
            "LEGACY_RAW_CAPTURE",
            "LEGACY_UNIFIED_RECORDER",
            "LEGACY_GAME_STATE_RECORDER",
            "LEGACY_PLAYER_SESSION_RECORDER",
        ]:
            monkeypatch.delenv(key, raising=False)

        flags = Config.get_legacy_flags()
        assert all(isinstance(value, bool) for value in flags.values())
