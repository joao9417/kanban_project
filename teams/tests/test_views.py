"""
teams/tests/test_views.py

Integration tests for BoardMembersView and BoardFinishView.
Verifies role is required, add/remove works, and permissions enforced.
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User

from boards.models import Board, Column
from teams.models import BoardMembership


class BoardMembersViewTest(TestCase):
    def setUp(self):
        self.owner   = User.objects.create_user('mem_owner',   password='pass123')
        self.eng     = User.objects.create_user('mem_eng',     password='pass123')
        self.stranger= User.objects.create_user('mem_stranger',password='pass123')
        self.board   = Board.objects.create(title='Members Board', owner=self.owner)
        self.url     = reverse('board_members', kwargs={'pk': self.board.pk})

    # --- GET ---------------------------------------------------------------

    def test_owner_can_view_page(self):
        self.client.login(username='mem_owner', password='pass123')
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 200)
        self.assertTemplateUsed(resp, 'teams/board_members.html')

    def test_stranger_gets_403_on_get(self):
        self.client.login(username='mem_stranger', password='pass123')
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 403)

    def test_unauthenticated_redirects(self):
        resp = self.client.get(self.url)
        self.assertEqual(resp.status_code, 302)

    # --- ADD member --------------------------------------------------------

    def test_owner_can_add_member_with_role(self):
        """Successful POST creates a BoardMembership row with the correct role."""
        self.client.login(username='mem_owner', password='pass123')
        resp = self.client.post(self.url, {
            'user': self.eng.pk,
            'specialty_role': BoardMembership.ROLE_ELEC,
        })
        self.assertRedirects(resp, self.url)
        membership = BoardMembership.objects.get(board=self.board, user=self.eng)
        self.assertEqual(membership.specialty_role, BoardMembership.ROLE_ELEC)

    def test_add_member_without_role_fails(self):
        """POST without specialty_role re-renders form with error; no membership created."""
        self.client.login(username='mem_owner', password='pass123')
        resp = self.client.post(self.url, {
            'user': self.eng.pk,
            'specialty_role': '',    # blank → invalid
        })
        self.assertEqual(resp.status_code, 200)   # form re-rendered
        self.assertFalse(
            BoardMembership.objects.filter(board=self.board, user=self.eng).exists()
        )

    def test_add_member_without_user_fails(self):
        """POST without a user selection is invalid."""
        self.client.login(username='mem_owner', password='pass123')
        resp = self.client.post(self.url, {
            'user': '',
            'specialty_role': BoardMembership.ROLE_MEC,
        })
        self.assertEqual(resp.status_code, 200)

    # --- REMOVE member -----------------------------------------------------

    def test_owner_can_remove_member(self):
        """POST action=remove deletes the BoardMembership."""
        membership = BoardMembership.objects.create(
            board=self.board, user=self.eng, specialty_role='auto'
        )
        self.client.login(username='mem_owner', password='pass123')
        resp = self.client.post(self.url, {
            'action': 'remove',
            'member_id': self.eng.pk,
        })
        self.assertRedirects(resp, self.url)
        self.assertFalse(
            BoardMembership.objects.filter(board=self.board, user=self.eng).exists()
        )

    def test_non_owner_cannot_add_member(self):
        """A board member (non-owner) gets 403 on POST."""
        BoardMembership.objects.create(board=self.board, user=self.eng, specialty_role='mec')
        extra = User.objects.create_user('mem_extra', password='pass123')
        self.client.login(username='mem_eng', password='pass123')
        resp = self.client.post(self.url, {
            'user': extra.pk,
            'specialty_role': 'mec',
        })
        self.assertEqual(resp.status_code, 403)


class BoardFinishViewTest(TestCase):
    def setUp(self):
        self.owner   = User.objects.create_user('fin_owner', password='pass123')
        self.stranger= User.objects.create_user('fin_stranger', password='pass123')
        self.board   = Board.objects.create(title='Finish Board', owner=self.owner)
        Column.objects.create(board=self.board, title='General', order=0)
        self.url = reverse('board_finish', kwargs={'pk': self.board.pk})

    def test_owner_can_finish_board(self):
        self.client.login(username='fin_owner', password='pass123')
        self.client.post(self.url)
        self.board.refresh_from_db()
        self.assertEqual(self.board.status, Board.STATUS_FINISHED)

    def test_stranger_cannot_finish_board(self):
        self.client.login(username='fin_stranger', password='pass123')
        resp = self.client.post(self.url)
        self.assertEqual(resp.status_code, 403)
        self.board.refresh_from_db()
        self.assertEqual(self.board.status, Board.STATUS_ACTIVE)
