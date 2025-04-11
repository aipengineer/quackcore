# tests/test_teaching/test_core/test_badges.py
"""
Tests for the teaching badges management module.

This module tests the badge management functionality in quackcore.teaching.core.badges.
"""
from unittest.mock import patch

from quackcore.teaching.core.models import Badge, UserProgress
from quackcore.teaching.core import badges


class TestBadgeManagement:
    """Tests for badge management functions."""

    @patch("quackcore.teaching.core.badges._BADGES")
    def test_get_all_badges(self, mock_badges):
        """Test getting all available badges."""
        # Setup
        badge1 = Badge(
            id="badge1",
            name="Badge 1",
            description="First Badge",
            required_xp=50,
            emoji="🏆",
        )
        badge2 = Badge(
            id="badge2",
            name="Badge 2",
            description="Second Badge",
            required_xp=100,
            emoji="🏅",
        )
        mock_badges.values.return_value = [badge1, badge2]

        # Act
        result = badges.get_all_badges()

        # Assert
        assert len(result) == 2
        assert badge1 in result
        assert badge2 in result
        mock_badges.values.assert_called_once()

    @patch("quackcore.teaching.core.badges._BADGES")
    def test_get_badge_existing(self, mock_badges):
        """Test getting an existing badge by ID."""
        # Setup
        badge = Badge(
            id="test-badge",
            name="Test Badge",
            description="A test badge",
            required_xp=50,
            emoji="🏆",
        )
        mock_badges.get.return_value = badge

        # Act
        result = badges.get_badge("test-badge")

        # Assert
        assert result == badge
        mock_badges.get.assert_called_once_with("test-badge")

    @patch("quackcore.teaching.core.badges._BADGES")
    def test_get_badge_nonexistent(self, mock_badges):
        """Test getting a non-existent badge by ID."""
        # Setup
        mock_badges.get.return_value = None

        # Act
        result = badges.get_badge("nonexistent-badge")

        # Assert
        assert result is None
        mock_badges.get.assert_called_once_with("nonexistent-badge")

    @patch("quackcore.teaching.core.badges._BADGES")
    def test_get_user_badges(self, mock_badges):
        """Test getting badges earned by a user."""
        # Setup
        badge1 = Badge(
            id="badge1",
            name="Badge 1",
            description="First Badge",
            required_xp=50,
            emoji="🏆",
        )
        badge2 = Badge(
            id="badge2",
            name="Badge 2",
            description="Second Badge",
            required_xp=100,
            emoji="🏅",
        )

        mock_badges.__getitem__.side_effect = lambda key: {
            "badge1": badge1,
            "badge2": badge2,
        }.get(key)

        user = UserProgress(
            github_username="testuser",
            earned_badge_ids=["badge1", "nonexistent"],
        )

        # Act
        result = badges.get_user_badges(user)

        # Assert
        assert len(result) == 1
        assert result[0] == badge1

    @patch("quackcore.teaching.core.badges._BADGES")
    @patch("quackcore.teaching.core.badges.logger")
    def test_award_badge_success(self, mock_logger, mock_badges):
        """Test awarding a badge to a user successfully."""
        # Setup
        badge = Badge(
            id="test-badge",
            name="Test Badge",
            description="A test badge",
            required_xp=50,
            emoji="🏆",
        )
        mock_badges.__getitem__.return_value = badge
        mock_badges.get.return_value = True

        user = UserProgress(github_username="testuser")

        # Act
        result = badges.award_badge(user, "test-badge")

        # Assert
        assert result is True
        assert "test-badge" in user.earned_badge_ids
        mock_logger.info.assert_called_with(
            f"Awarded badge to user: {badge.name} ({badge.emoji})"
        )

    @patch("quackcore.teaching.core.badges._BADGES")
    @patch("quackcore.teaching.core.badges.logger")
    def test_award_badge_already_earned(self, mock_logger, mock_badges):
        """Test awarding a badge to a user who already has it."""
        # Setup
        badge = Badge(
            id="test-badge",
            name="Test Badge",
            description="A test badge",
            required_xp=50,
            emoji="🏆",
        )
        mock_badges.__getitem__.return_value = badge
        mock_badges.get.return_value = True

        user = UserProgress(
            github_username="testuser",
            earned_badge_ids=["test-badge"],
        )

        # Act
        result = badges.award_badge(user, "test-badge")

        # Assert
        assert result is False
        mock_logger.debug.assert_called_with("User already has badge: test-badge")

    @patch("quackcore.teaching.core.badges._BADGES")
    @patch("quackcore.teaching.core.badges.logger")
    def test_award_nonexistent_badge(self, mock_logger, mock_badges):
        """Test awarding a non-existent badge."""
        # Setup
        mock_badges.get.return_value = None
        user = UserProgress(github_username="testuser")

        # Act
        result = badges.award_badge(user, "nonexistent")

        # Assert
        assert result is False
        assert "nonexistent" not in user.earned_badge_ids
        mock_logger.warning.assert_called_with(
            "Attempted to award non-existent badge: nonexistent"
        )

    @patch("quackcore.teaching.core.badges._BADGES")
    def test_get_next_badges(self, mock_badges):
        """Test getting the next badges a user could earn."""
        # Setup
        badge1 = Badge(
            id="badge1",
            name="Badge 1",
            description="First Badge",
            required_xp=50,
            emoji="🏆",
        )
        badge2 = Badge(
            id="badge2",
            name="Badge 2",
            description="Second Badge",
            required_xp=100,
            emoji="🏅",
        )
        badge3 = Badge(
            id="badge3",
            name="Badge 3",
            description="Third Badge",
            required_xp=200,
            emoji="🎖️",
        )
        # Non-XP badge
        badge4 = Badge(
            id="badge4",
            name="Badge 4",
            description="Fourth Badge",
            required_xp=0,
            emoji="⭐",
        )

        mock_badges.values.return_value = [badge1, badge2, badge3, badge4]

        user = UserProgress(
            github_username="testuser",
            xp=75,
            earned_badge_ids=["badge1"],
        )

        # Act
        result = badges.get_next_badges(user, limit=2)

        # Assert
        assert len(result) == 2
        assert result[0] == badge2  # Next in XP progression
        assert result[1] == badge3  # Following in XP progression

    def test_get_badge_progress_earned(self):
        """Test calculating a user's progress for an earned badge."""
        # Setup
        user = UserProgress(
            github_username="testuser",
            xp=150,
            earned_badge_ids=["badge1"],
        )

        # Mock the _BADGES dict access
        with patch("quackcore.teaching.core.badges._BADGES") as mock_badges:
            badge = Badge(
                id="badge1",
                name="Badge 1",
                description="First Badge",
                required_xp=100,
                emoji="🏆",
            )
            mock_badges.get.return_value = badge

            # Act
            progress = badges.get_badge_progress(user, "badge1")

            # Assert
            assert progress == 1.0  # Fully completed

    def test_get_badge_progress_xp_based(self):
        """Test calculating a user's progress for an XP-based badge."""
        # Setup
        user = UserProgress(
            github_username="testuser",
            xp=75,
        )

        # Mock the _BADGES dict access
        with patch("quackcore.teaching.core.badges._BADGES") as mock_badges:
            badge = Badge(
                id="badge1",
                name="Badge 1",
                description="First Badge",
                required_xp=100,
                emoji="🏆",
            )
            mock_badges.get.return_value = badge

            # Act
            progress = badges.get_badge_progress(user, "badge1")

            # Assert
            assert progress == 0.75  # 75% progress (75/100 XP)

    def test_get_badge_progress_nonexistent(self):
        """Test calculating progress for a non-existent badge."""
        # Setup
        user = UserProgress(github_username="testuser")

        # Mock the _BADGES dict access
        with patch("quackcore.teaching.core.badges._BADGES") as mock_badges:
            mock_badges.get.return_value = None

            # Act
            progress = badges.get_badge_progress(user, "nonexistent")

            # Assert
            assert progress == 0.0  # No progress