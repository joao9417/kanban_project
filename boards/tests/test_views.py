"""
boards/tests/test_views.py

Integration tests for Board, Column, and Card views.
Verifies permission enforcement (owner vs member vs stranger).
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User

from boards.models import Board, Column, Card
from teams.models import BoardMembership


def make_board(owner_username='board_owner_v', member_username=None):
    owner = User.objects.create_user(owner_username, password='pass123')
    board = Board.objects.create(title='Test Board', owner=owner)
    column = Column.objects.create(board=board, title='General', order=0)
    member = None
    if member_username:
        member = User.objects.create_user(member_username, password='pass123')
        BoardMembership.objects.create(board=board, user=member, specialty_role='mec')
    return owner, board, column, member


class BoardListViewTest(TestCase):
    def test_redirects_unauthenticated(self):
        resp = self.client.get(reverse('board_list'))
        self.assertRedirects(resp, f"{reverse('login')}?next={reverse('board_list')}")

    def test_authenticated_user_sees_dashboard(self):
        user = User.objects.create_user('list_user', password='pass')
        self.client.login(username='list_user', password='pass')
        resp = self.client.get(reverse('board_list'))
        self.assertEqual(resp.status_code, 200)
        self.assertIn('owned_boards', resp.context)


class BoardDetailViewTest(TestCase):
    def setUp(self):
        self.owner, self.board, self.column, self.member = make_board(
            'detail_owner', 'detail_member'
        )
        self.stranger = User.objects.create_user('detail_stranger', password='pass123')

    def test_owner_can_view(self):
        self.client.login(username='detail_owner', password='pass123')
        resp = self.client.get(reverse('board_detail', kwargs={'pk': self.board.pk}))
        self.assertEqual(resp.status_code, 200)

    def test_member_can_view(self):
        self.client.login(username='detail_member', password='pass123')
        resp = self.client.get(reverse('board_detail', kwargs={'pk': self.board.pk}))
        self.assertEqual(resp.status_code, 200)

    def test_stranger_gets_403(self):
        self.client.login(username='detail_stranger', password='pass123')
        resp = self.client.get(reverse('board_detail', kwargs={'pk': self.board.pk}))
        self.assertEqual(resp.status_code, 403)

    def test_scrum_view_default(self):
        self.client.login(username='detail_owner', password='pass123')
        resp = self.client.get(reverse('board_detail', kwargs={'pk': self.board.pk}))
        self.assertEqual(resp.context['view_mode'], 'scrum')
        self.assertIn('scrum_data', resp.context)

    def test_workload_view_toggle(self):
        self.client.login(username='detail_owner', password='pass123')
        resp = self.client.get(
            reverse('board_detail', kwargs={'pk': self.board.pk}) + '?view=workload'
        )
        self.assertEqual(resp.context['view_mode'], 'workload')
        self.assertIn('workload_data', resp.context)


class BoardCreateViewTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('create_user', password='pass123')
        self.client.login(username='create_user', password='pass123')

    def test_create_board_success(self):
        resp = self.client.post(
            reverse('board_create'),
            {'title': 'New Board', 'description': 'A test board'},
        )
        self.assertRedirects(resp, reverse('board_list'))
        self.assertTrue(Board.objects.filter(title='New Board').exists())

    def test_default_column_created(self):
        self.client.post(
            reverse('board_create'),
            {'title': 'Board With Column', 'description': ''},
        )
        board = Board.objects.get(title='Board With Column')
        self.assertTrue(board.columns.exists())


class CardStatusPermissionTest(TestCase):
    """Owner can set 'done'; engineer (member) cannot."""

    def setUp(self):
        self.owner, self.board, self.column, self.member = make_board(
            'card_perm_owner', 'card_perm_member'
        )
        self.card = Card.objects.create(
            column=self.column, title='Task', status=Card.STATUS_TODO
        )

    def test_owner_can_set_card_to_done(self):
        self.client.login(username='card_perm_owner', password='pass123')
        resp = self.client.post(
            reverse('card_update', kwargs={'pk': self.card.pk}),
            {
                'title': 'Task', 'description': '', 'status': Card.STATUS_DONE,
                'discipline': '', 'progress': 100, 'order': 0,
            },
        )
        self.card.refresh_from_db()
        self.assertEqual(self.card.status, Card.STATUS_DONE)

    def test_member_cannot_set_card_to_done(self):
        self.client.login(username='card_perm_member', password='pass123')
        resp = self.client.post(
            reverse('card_update', kwargs={'pk': self.card.pk}),
            {
                'title': 'Task', 'description': '', 'status': Card.STATUS_DONE,
                'discipline': '', 'progress': 50, 'order': 0,
            },
        )
        self.card.refresh_from_db()
        self.assertNotEqual(self.card.status, Card.STATUS_DONE)
