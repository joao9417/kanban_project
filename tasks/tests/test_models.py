"""
Phase 1 Unit Tests — Models & Signal
Tests validate:
  - Board, Column, Card model creation with all new fields
  - Card.is_overdue property
  - BoardAnalytics auto-creation via post_save signal when Board is finished
  - Analytics correctness: avg_progress and overdue count
"""
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from tasks.models import Board, Column, Card, BoardAnalytics


class BoardModelTest(TestCase):
    """Tests for the extended Board model."""

    def setUp(self):
        self.owner = User.objects.create_user(username='jefe', password='pass123')
        self.engineer = User.objects.create_user(username='engineer1', password='pass123')
        self.board = Board.objects.create(
            title='Plant Installation X',
            description='Full plant setup project',
            owner=self.owner,
            status=Board.STATUS_ACTIVE
        )

    def test_board_creation(self):
        """Board is created with correct default status."""
        self.assertEqual(self.board.status, Board.STATUS_ACTIVE)
        self.assertEqual(str(self.board), 'Plant Installation X')

    def test_board_is_accessible_by_owner(self):
        """Owner has access to their board."""
        self.assertTrue(self.board.is_accessible_by(self.owner))

    def test_board_is_not_accessible_by_non_member(self):
        """Non-members do not have access."""
        self.assertFalse(self.board.is_accessible_by(self.engineer))

    def test_board_is_accessible_by_member(self):
        """Adding a member grants access."""
        self.board.members.add(self.engineer)
        self.assertTrue(self.board.is_accessible_by(self.engineer))

    def test_board_is_owned_by(self):
        """is_owned_by returns True only for the owner."""
        self.assertTrue(self.board.is_owned_by(self.owner))
        self.assertFalse(self.board.is_owned_by(self.engineer))


class CardModelTest(TestCase):
    """Tests for the extended Card model including new fields."""

    def setUp(self):
        self.owner = User.objects.create_user(username='jefe2', password='pass123')
        self.engineer = User.objects.create_user(username='eng2', password='pass123')
        self.board = Board.objects.create(title='Board A', owner=self.owner)
        self.column = Column.objects.create(board=self.board, title='Backlog', order=0)

    def _create_card(self, **kwargs):
        defaults = dict(
            column=self.column,
            title='Install pump',
            status=Card.STATUS_TODO,
            discipline=Card.DISCIPLINE_MEC,
            progress=50,
            assignee=self.engineer,
        )
        defaults.update(kwargs)
        return Card.objects.create(**defaults)

    def test_card_creation_with_new_fields(self):
        """Card is created with all new engineering fields."""
        card = self._create_card()
        self.assertEqual(card.status, Card.STATUS_TODO)
        self.assertEqual(card.discipline, Card.DISCIPLINE_MEC)
        self.assertEqual(card.progress, 50)
        self.assertEqual(card.assignee, self.engineer)

    def test_card_is_not_overdue_without_due_date(self):
        """Card without due_date is never overdue."""
        card = self._create_card(due_date=None)
        self.assertFalse(card.is_overdue)

    def test_card_is_overdue_past_due_date(self):
        """Card past its due date and not done is overdue."""
        past = timezone.now() - timedelta(days=2)
        card = self._create_card(due_date=past, status=Card.STATUS_TODO)
        self.assertTrue(card.is_overdue)

    def test_done_card_is_not_overdue(self):
        """Done card is never overdue even if past due date."""
        past = timezone.now() - timedelta(days=2)
        card = self._create_card(due_date=past, status=Card.STATUS_DONE)
        self.assertFalse(card.is_overdue)

    def test_future_card_is_not_overdue(self):
        """Card with future due date is not overdue."""
        future = timezone.now() + timedelta(days=5)
        card = self._create_card(due_date=future)
        self.assertFalse(card.is_overdue)

    def test_discipline_colour_mapping(self):
        """Discipline colour returns correct Bootstrap class."""
        card = self._create_card(discipline=Card.DISCIPLINE_ELEC)
        self.assertEqual(card.discipline_colour, 'warning')


class BoardAnalyticsSignalTest(TestCase):
    """
    Tests for the post_save signal that auto-creates BoardAnalytics
    when a Board transitions to 'finished'.
    """

    def setUp(self):
        self.owner = User.objects.create_user(username='jefe3', password='pass123')
        self.eng_a = User.objects.create_user(username='eng_a', password='pass123')
        self.board = Board.objects.create(title='Signal Test Board', owner=self.owner)
        self.column = Column.objects.create(board=self.board, title='Main', order=0)

        # Create 4 cards with varying progress and due dates
        past = timezone.now() - timedelta(days=3)
        future = timezone.now() + timedelta(days=5)

        # Card 1: done, progress=100
        Card.objects.create(
            column=self.column, title='Task 1',
            status=Card.STATUS_DONE, progress=100,
            discipline=Card.DISCIPLINE_MEC, due_date=past
        )
        # Card 2: in_progress, progress=60, overdue
        Card.objects.create(
            column=self.column, title='Task 2',
            status=Card.STATUS_IN_PROGRESS, progress=60,
            discipline=Card.DISCIPLINE_ELEC, due_date=past
        )
        # Card 3: todo, progress=20, not overdue
        Card.objects.create(
            column=self.column, title='Task 3',
            status=Card.STATUS_TODO, progress=20,
            discipline=Card.DISCIPLINE_MEC, due_date=future
        )
        # Card 4: review, progress=80, overdue
        Card.objects.create(
            column=self.column, title='Task 4',
            status=Card.STATUS_REVIEW, progress=80,
            discipline=Card.DISCIPLINE_AUTO, due_date=past
        )

    def test_analytics_not_created_on_active_board(self):
        """BoardAnalytics is NOT created while board is active."""
        self.board.save()  # save without changing to finished
        self.assertFalse(BoardAnalytics.objects.filter(board=self.board).exists())

    def test_signal_creates_analytics_on_finish(self):
        """Signal auto-creates BoardAnalytics when status changes to 'finished'."""
        self.board.status = Board.STATUS_FINISHED
        self.board.save()
        self.assertTrue(BoardAnalytics.objects.filter(board=self.board).exists())

    def test_analytics_total_cards_correct(self):
        """Analytics total_cards equals the number of cards in the board."""
        self.board.status = Board.STATUS_FINISHED
        self.board.save()
        analytics = BoardAnalytics.objects.get(board=self.board)
        self.assertEqual(analytics.total_cards, 4)

    def test_analytics_completed_cards_correct(self):
        """Analytics completed_cards counts only cards with status='done'."""
        self.board.status = Board.STATUS_FINISHED
        self.board.save()
        analytics = BoardAnalytics.objects.get(board=self.board)
        self.assertEqual(analytics.completed_cards, 1)

    def test_analytics_overdue_cards_correct(self):
        """Analytics overdue_cards counts past-due non-done cards (Tasks 2 and 4)."""
        self.board.status = Board.STATUS_FINISHED
        self.board.save()
        analytics = BoardAnalytics.objects.get(board=self.board)
        # Task 1 is done (not overdue), Task 3 is future (not overdue)
        # Tasks 2 and 4 are past due AND not done → 2 overdue
        self.assertEqual(analytics.overdue_cards, 2)

    def test_analytics_avg_progress_correct(self):
        """
        avg_progress = (100 + 60 + 20 + 80) / 4 = 65.0
        """
        self.board.status = Board.STATUS_FINISHED
        self.board.save()
        analytics = BoardAnalytics.objects.get(board=self.board)
        expected_avg = (100 + 60 + 20 + 80) / 4  # 65.0
        self.assertAlmostEqual(analytics.avg_progress, expected_avg, places=1)

    def test_analytics_completion_rate_property(self):
        """completion_rate property = 1 done / 4 total = 25.0%"""
        self.board.status = Board.STATUS_FINISHED
        self.board.save()
        analytics = BoardAnalytics.objects.get(board=self.board)
        self.assertEqual(analytics.completion_rate, 25.0)

    def test_analytics_discipline_stats_structure(self):
        """discipline_stats contains correct per-discipline data."""
        self.board.status = Board.STATUS_FINISHED
        self.board.save()
        analytics = BoardAnalytics.objects.get(board=self.board)
        stats = analytics.discipline_stats

        # Mecánica: Tasks 1 (100) and 3 (20) → avg = 60
        self.assertIn('mec', stats)
        self.assertEqual(stats['mec']['count'], 2)
        self.assertAlmostEqual(stats['mec']['avg_progress'], 60.0, places=1)

        # Eléctrica: Task 2 (60) → avg = 60
        self.assertIn('elec', stats)
        self.assertEqual(stats['elec']['count'], 1)
        self.assertAlmostEqual(stats['elec']['avg_progress'], 60.0, places=1)

        # Automatización: Task 4 (80) → avg = 80
        self.assertIn('auto', stats)
        self.assertEqual(stats['auto']['count'], 1)
        self.assertAlmostEqual(stats['auto']['avg_progress'], 80.0, places=1)

        # Refrigeración: 0 cards
        self.assertIn('refrig', stats)
        self.assertEqual(stats['refrig']['count'], 0)

    def test_signal_updates_analytics_if_called_again(self):
        """Finishing the board a second time updates analytics (no duplicate)."""
        self.board.status = Board.STATUS_FINISHED
        self.board.save()
        self.board.save()  # Second save should update, not create a new record
        count = BoardAnalytics.objects.filter(board=self.board).count()
        self.assertEqual(count, 1)
