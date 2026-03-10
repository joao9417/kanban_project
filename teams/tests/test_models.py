"""
teams/tests/test_models.py

Unit tests for BoardMembership model: creation, uniqueness, role badge colours.
"""
from django.test import TestCase
from django.db import IntegrityError
from django.contrib.auth.models import User

from boards.models import Board
from teams.models import BoardMembership


class BoardMembershipModelTest(TestCase):
    def setUp(self):
        self.owner  = User.objects.create_user('tm_owner', password='pass')
        self.eng1   = User.objects.create_user('tm_eng1', password='pass')
        self.eng2   = User.objects.create_user('tm_eng2', password='pass')
        self.board  = Board.objects.create(title='Team Test Board', owner=self.owner)

    def test_create_membership(self):
        m = BoardMembership.objects.create(
            board=self.board, user=self.eng1, specialty_role=BoardMembership.ROLE_MEC
        )
        self.assertEqual(m.board, self.board)
        self.assertEqual(m.user, self.eng1)
        self.assertEqual(m.specialty_role, 'mec')

    def test_str_representation(self):
        m = BoardMembership.objects.create(
            board=self.board, user=self.eng1, specialty_role=BoardMembership.ROLE_ELEC
        )
        self.assertIn('tm_eng1', str(m))
        self.assertIn('Team Test Board', str(m))

    def test_role_badge_colour_mec(self):
        m = BoardMembership(specialty_role='mec')
        self.assertEqual(m.role_badge_colour, 'primary')

    def test_role_badge_colour_elec(self):
        m = BoardMembership(specialty_role='elec')
        self.assertEqual(m.role_badge_colour, 'warning')

    def test_role_badge_colour_auto(self):
        m = BoardMembership(specialty_role='auto')
        self.assertEqual(m.role_badge_colour, 'success')

    def test_role_badge_colour_refrig(self):
        m = BoardMembership(specialty_role='refrig')
        self.assertEqual(m.role_badge_colour, 'danger')

    def test_unique_together_enforced(self):
        """A user cannot be added to the same board twice."""
        BoardMembership.objects.create(
            board=self.board, user=self.eng1, specialty_role='mec'
        )
        with self.assertRaises(IntegrityError):
            BoardMembership.objects.create(
                board=self.board, user=self.eng1, specialty_role='elec'
            )

    def test_board_members_queryset(self):
        """Board.members M2M reflects created memberships."""
        BoardMembership.objects.create(board=self.board, user=self.eng1, specialty_role='mec')
        BoardMembership.objects.create(board=self.board, user=self.eng2, specialty_role='auto')
        members = list(self.board.members.values_list('pk', flat=True))
        self.assertIn(self.eng1.pk, members)
        self.assertIn(self.eng2.pk, members)
        self.assertEqual(self.board.members.count(), 2)
