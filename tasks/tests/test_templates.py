"""
Phase 5 Unit Tests — Template Logic (Workload Badge)
Validates that the workload_data context computed in BoardDetailView
contains mathematically correct overdue counts per engineer.

The badge rendered in board_detail.html reads directly from
workload_data[i]['overdue'], so testing the view context is the most
precise way to verify the badge logic without HTML parsing.

Definition of 'overdue':
  due_date < now  AND  status != 'done'
"""
from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import timedelta
from tasks.models import Board, Column, Card


class WorkloadBadgeOverdueTest(TestCase):
    """
    Tests the overdue count in the Workload view badge.

    Setup:
      - owner (Jefe) + engineer A + engineer B
      - 5 cards with varying due_date and status values
    Expected badge results per engineer:
      engineer_a: 2 tasks, 1 overdue   (Task1=todo/past, Task2=done/past)
      engineer_b: 2 tasks, 1 overdue   (Task3=review/past, Task4=in_progress/future)
      unassigned:  1 task,  0 overdue  (Task5=todo/future)
    """

    def setUp(self):
        self.client = Client()

        self.owner = User.objects.create_user(username='jefe_tmpl', password='pass123')
        self.engineer_a = User.objects.create_user(username='eng_a_tmpl', password='pass123')
        self.engineer_b = User.objects.create_user(username='eng_b_tmpl', password='pass123')

        self.board = Board.objects.create(title='Template Test Board', owner=self.owner)
        self.board.members.add(self.engineer_a, self.engineer_b)
        self.column = Column.objects.create(board=self.board, title='Main', order=0)

        past = timezone.now() - timedelta(days=3)
        future = timezone.now() + timedelta(days=5)

        # Task 1: engineer_a, past due, status=todo → OVERDUE ✓
        self.card1 = Card.objects.create(
            column=self.column, title='Task 1',
            status=Card.STATUS_TODO, assignee=self.engineer_a,
            due_date=past, progress=30
        )
        # Task 2: engineer_a, past due, status=done → NOT overdue (done)
        self.card2 = Card.objects.create(
            column=self.column, title='Task 2',
            status=Card.STATUS_DONE, assignee=self.engineer_a,
            due_date=past, progress=100
        )
        # Task 3: engineer_b, past due, status=review → OVERDUE ✓
        self.card3 = Card.objects.create(
            column=self.column, title='Task 3',
            status=Card.STATUS_REVIEW, assignee=self.engineer_b,
            due_date=past, progress=80
        )
        # Task 4: engineer_b, future due, status=in_progress → NOT overdue
        self.card4 = Card.objects.create(
            column=self.column, title='Task 4',
            status=Card.STATUS_IN_PROGRESS, assignee=self.engineer_b,
            due_date=future, progress=40
        )
        # Task 5: unassigned, future due, status=todo → NOT overdue
        self.card5 = Card.objects.create(
            column=self.column, title='Task 5',
            status=Card.STATUS_TODO, assignee=None,
            due_date=future, progress=0
        )

    def _get_workload_data(self):
        """Helper: returns the workload_data context list from the view."""
        self.client.login(username='jefe_tmpl', password='pass123')
        url = reverse('board_detail', kwargs={'pk': self.board.pk})
        response = self.client.get(url + '?view=workload')
        self.assertEqual(response.status_code, 200)
        return response.context['workload_data']

    def _find_entry(self, workload_data, member):
        """Helper: find the workload entry for a given User (or None for unassigned)."""
        for entry in workload_data:
            if entry['member'] == member:
                return entry
        return None

    # ── Totals ──────────────────────────────────────────────────────────────

    def test_engineer_a_total_is_2(self):
        wl = self._get_workload_data()
        entry = self._find_entry(wl, self.engineer_a)
        self.assertIsNotNone(entry, "No workload entry found for engineer_a")
        self.assertEqual(entry['total'], 2)

    def test_engineer_b_total_is_2(self):
        wl = self._get_workload_data()
        entry = self._find_entry(wl, self.engineer_b)
        self.assertIsNotNone(entry)
        self.assertEqual(entry['total'], 2)

    def test_unassigned_total_is_1(self):
        wl = self._get_workload_data()
        entry = self._find_entry(wl, None)
        self.assertIsNotNone(entry, "No unassigned entry in workload data")
        self.assertEqual(entry['total'], 1)

    # ── Overdue badge counts ─────────────────────────────────────────────────

    def test_engineer_a_overdue_is_1(self):
        """
        engineer_a has 2 tasks:
          Task1 (todo, past) → overdue
          Task2 (done, past) → NOT overdue
        Expected badge overdue count = 1
        """
        wl = self._get_workload_data()
        entry = self._find_entry(wl, self.engineer_a)
        self.assertEqual(entry['overdue'], 1,
            "engineer_a should have 1 overdue task (done card does not count)")

    def test_engineer_b_overdue_is_1(self):
        """
        engineer_b has 2 tasks:
          Task3 (review, past) → overdue
          Task4 (in_progress, future) → NOT overdue
        Expected badge overdue count = 1
        """
        wl = self._get_workload_data()
        entry = self._find_entry(wl, self.engineer_b)
        self.assertEqual(entry['overdue'], 1,
            "engineer_b should have 1 overdue task (future task does not count)")

    def test_unassigned_overdue_is_0(self):
        """
        Unassigned task (Task5) has a future due date → 0 overdue.
        """
        wl = self._get_workload_data()
        entry = self._find_entry(wl, None)
        self.assertEqual(entry['overdue'], 0)

    def test_owner_entry_exists(self):
        """Owner (Jefe) always has a workload column even with no tasks."""
        wl = self._get_workload_data()
        entry = self._find_entry(wl, self.owner)
        self.assertIsNotNone(entry, "Owner must always appear in workload view")

    def test_total_items_in_workload_equals_member_count_plus_unassigned(self):
        """
        Workload list length = owner + 2 members + 1 unassigned bucket = 4
        """
        wl = self._get_workload_data()
        # owner + engineer_a + engineer_b + unassigned = 4
        self.assertEqual(len(wl), 4)
