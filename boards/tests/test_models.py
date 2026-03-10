"""
boards/tests/test_models.py

Unit tests for Board, Column, Card, and BoardAnalytics models.
"""
from django.test import TestCase
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta

from boards.models import Board, Column, Card, BoardAnalytics


class BoardModelTest(TestCase):
    def setUp(self):
        self.owner  = User.objects.create_user('owner_bm', password='pass')
        self.member = User.objects.create_user('member_bm', password='pass')
        self.other  = User.objects.create_user('other_bm', password='pass')
        self.board  = Board.objects.create(title='Test Board', owner=self.owner)

    def test_str(self):
        self.assertEqual(str(self.board), 'Test Board')

    def test_is_accessible_by_owner(self):
        self.assertTrue(self.board.is_accessible_by(self.owner))

    def test_is_accessible_by_member(self):
        from teams.models import BoardMembership
        BoardMembership.objects.create(
            board=self.board, user=self.member, specialty_role='mec'
        )
        self.assertTrue(self.board.is_accessible_by(self.member))

    def test_is_not_accessible_by_stranger(self):
        self.assertFalse(self.board.is_accessible_by(self.other))

    def test_is_owned_by_owner(self):
        self.assertTrue(self.board.is_owned_by(self.owner))

    def test_is_not_owned_by_member(self):
        self.assertFalse(self.board.is_owned_by(self.member))


class CardModelTest(TestCase):
    def setUp(self):
        self.owner    = User.objects.create_user('card_owner', password='pass')
        self.board    = Board.objects.create(title='B', owner=self.owner)
        self.column   = Column.objects.create(board=self.board, title='C', order=0)

    def test_is_overdue_true(self):
        past = timezone.now() - timedelta(days=1)
        card = Card.objects.create(
            column=self.column, title='Late', status=Card.STATUS_TODO, due_date=past
        )
        self.assertTrue(card.is_overdue)

    def test_is_overdue_false_when_done(self):
        past = timezone.now() - timedelta(days=1)
        card = Card.objects.create(
            column=self.column, title='Done', status=Card.STATUS_DONE, due_date=past
        )
        self.assertFalse(card.is_overdue)

    def test_discipline_colour(self):
        card = Card.objects.create(column=self.column, title='T', discipline='mec')
        self.assertEqual(card.discipline_colour, 'primary')


class BoardAnalyticsModelTest(TestCase):
    def setUp(self):
        owner = User.objects.create_user('analytics_owner', password='pass')
        board = Board.objects.create(title='Proj', owner=owner)
        self.analytics = BoardAnalytics.objects.create(
            board=board, total_cards=10, completed_cards=8, overdue_cards=2, avg_progress=80.0
        )

    def test_completion_rate(self):
        self.assertAlmostEqual(self.analytics.completion_rate, 80.0)

    def test_overdue_rate(self):
        self.assertAlmostEqual(self.analytics.overdue_rate, 20.0)

    def test_completion_rate_zero_cards(self):
        owner = User.objects.create_user('zero_owner', password='pass')
        board = Board.objects.create(title='Empty', owner=owner)
        a = BoardAnalytics.objects.create(board=board)
        self.assertEqual(a.completion_rate, 0.0)
