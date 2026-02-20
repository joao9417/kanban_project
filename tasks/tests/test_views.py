"""
Phase 2 Unit Tests — Views & Permissions
Validates:
  - Non-member (stranger) gets 403 on board_detail
  - Member has read access to the board detail
  - Owner (Jefe) has full access
  - Member cannot set card status to 'done' via CardUpdateView
  - Owner CAN set card status to 'done'
  - BoardMembersView restricted to owner
  - BoardFinishView restricted to owner
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from tasks.models import Board, Column, Card


class PermissionSetupMixin:
    """Shared setUp for permission tests."""

    def setUp(self):
        self.client = Client()

        # Three users: owner, member, stranger
        self.owner = User.objects.create_user(username='jefe_view', password='pass123')
        self.member = User.objects.create_user(username='eng_view', password='pass123')
        self.stranger = User.objects.create_user(username='stranger', password='pass123')

        # Board owned by owner; member is invited
        self.board = Board.objects.create(title='View Test Board', owner=self.owner)
        self.board.members.add(self.member)

        # Column and card on the board
        self.column = Column.objects.create(board=self.board, title='Main', order=0)
        self.card = Card.objects.create(
            column=self.column,
            title='Test Task',
            status=Card.STATUS_TODO,
            discipline=Card.DISCIPLINE_MEC,
            progress=40,
        )


class BoardDetailPermissionTest(PermissionSetupMixin, TestCase):
    """Tests access control on the BoardDetailView."""

    def test_stranger_gets_403_on_board_detail(self):
        """A non-member/non-owner gets 403 Forbidden on the board detail view."""
        self.client.login(username='stranger', password='pass123')
        url = reverse('board_detail', kwargs={'pk': self.board.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_member_can_access_board_detail(self):
        """An invited member (engineer) can access the board detail view."""
        self.client.login(username='eng_view', password='pass123')
        url = reverse('board_detail', kwargs={'pk': self.board.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_owner_can_access_board_detail(self):
        """The board owner can access the board detail view."""
        self.client.login(username='jefe_view', password='pass123')
        url = reverse('board_detail', kwargs={'pk': self.board.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_board_detail_contains_is_owner_true_for_owner(self):
        """BoardDetailView sets is_owner=True in context for the board owner."""
        self.client.login(username='jefe_view', password='pass123')
        url = reverse('board_detail', kwargs={'pk': self.board.pk})
        response = self.client.get(url)
        self.assertTrue(response.context['is_owner'])

    def test_board_detail_contains_is_owner_false_for_member(self):
        """BoardDetailView sets is_owner=False in context for regular members."""
        self.client.login(username='eng_view', password='pass123')
        url = reverse('board_detail', kwargs={'pk': self.board.pk})
        response = self.client.get(url)
        self.assertFalse(response.context['is_owner'])

    def test_unauthenticated_redirected_to_login(self):
        """Unauthenticated users are redirected to login, not given 403."""
        url = reverse('board_detail', kwargs={'pk': self.board.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 302)
        self.assertIn('/accounts/login/', response['Location'])


class BoardListViewTest(PermissionSetupMixin, TestCase):
    """Tests that the board list shows owned and shared boards correctly."""

    def test_owner_sees_owned_board(self):
        """Owner sees their board in owned_boards context."""
        self.client.login(username='jefe_view', password='pass123')
        response = self.client.get(reverse('board_list'))
        self.assertIn(self.board, response.context['owned_boards'])

    def test_member_sees_board_in_shared(self):
        """Member sees the shared board in shared_boards context."""
        self.client.login(username='eng_view', password='pass123')
        response = self.client.get(reverse('board_list'))
        self.assertIn(self.board, response.context['shared_boards'])

    def test_stranger_does_not_see_board(self):
        """Stranger sees neither owned nor shared boards listing."""
        self.client.login(username='stranger', password='pass123')
        response = self.client.get(reverse('board_list'))
        self.assertNotIn(self.board, response.context['owned_boards'])
        self.assertNotIn(self.board, response.context['shared_boards'])


class CardStatusPermissionTest(PermissionSetupMixin, TestCase):
    """
    Tests role-based card status restriction.
    Only the board owner (Jefe) may set a card status to 'done'.
    """

    def _update_card_status(self, username, new_status):
        self.client.login(username=username, password='pass123')
        url = reverse('card_update', kwargs={'pk': self.card.pk})
        data = {
            'title': self.card.title,
            'description': '',
            'status': new_status,
            'discipline': self.card.discipline,
            'progress': 40,
            'order': 0,
        }
        return self.client.post(url, data, follow=True)

    def test_member_cannot_set_card_to_done(self):
        """
        When a member tries to set status='done', the form is invalid and
        the card status remains unchanged.
        """
        response = self._update_card_status('eng_view', Card.STATUS_DONE)
        # Should stay on the form (200) with an error, not redirect to board
        self.card.refresh_from_db()
        self.assertNotEqual(self.card.status, Card.STATUS_DONE)

    def test_owner_can_set_card_to_done(self):
        """Owner (Jefe) can successfully set a card status to 'done'."""
        response = self._update_card_status('jefe_view', Card.STATUS_DONE)
        self.card.refresh_from_db()
        self.assertEqual(self.card.status, Card.STATUS_DONE)

    def test_stranger_cannot_update_card(self):
        """Stranger cannot access the card update view (queryset returns nothing → 404)."""
        self.client.login(username='stranger', password='pass123')
        url = reverse('card_update', kwargs={'pk': self.card.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 404)


class BoardMembersViewPermissionTest(PermissionSetupMixin, TestCase):
    """Tests that only the owner can access the board members management view."""

    def test_owner_can_access_members_view(self):
        self.client.login(username='jefe_view', password='pass123')
        url = reverse('board_members', kwargs={'pk': self.board.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_member_cannot_access_members_view(self):
        """A regular member cannot manage the members list (gets 403)."""
        self.client.login(username='eng_view', password='pass123')
        url = reverse('board_members', kwargs={'pk': self.board.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_stranger_cannot_access_members_view(self):
        self.client.login(username='stranger', password='pass123')
        url = reverse('board_members', kwargs={'pk': self.board.pk})
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

    def test_owner_can_add_member(self):
        """Owner can add the stranger as a member via POST."""
        self.client.login(username='jefe_view', password='pass123')
        url = reverse('board_members', kwargs={'pk': self.board.pk})
        self.client.post(url, {'username': 'stranger'})
        self.board.refresh_from_db()
        self.assertIn(self.stranger, self.board.members.all())

    def test_owner_can_remove_member(self):
        """Owner can remove an existing member via POST."""
        self.client.login(username='jefe_view', password='pass123')
        url = reverse('board_members', kwargs={'pk': self.board.pk})
        self.client.post(url, {'action': 'remove', 'member_id': self.member.pk})
        self.board.refresh_from_db()
        self.assertNotIn(self.member, self.board.members.all())


class BoardFinishViewPermissionTest(PermissionSetupMixin, TestCase):
    """Tests that only the owner can finish a board."""

    def test_member_cannot_finish_board(self):
        self.client.login(username='eng_view', password='pass123')
        url = reverse('board_finish', kwargs={'pk': self.board.pk})
        response = self.client.post(url)
        self.assertEqual(response.status_code, 403)
        self.board.refresh_from_db()
        self.assertEqual(self.board.status, Board.STATUS_ACTIVE)

    def test_owner_can_finish_board(self):
        self.client.login(username='jefe_view', password='pass123')
        url = reverse('board_finish', kwargs={'pk': self.board.pk})
        response = self.client.post(url)
        self.board.refresh_from_db()
        self.assertEqual(self.board.status, Board.STATUS_FINISHED)
