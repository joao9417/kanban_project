"""
boards/models.py

Core data models for the Kanban board system:
  - Board: an engineering project, owned by a Jefe, with engineer members.
  - Column: an ordered container within a Board.
  - Card: an individual task within a Column.
  - BoardAnalytics: archived stats generated when a Board is finished.

Membership is managed via `teams.BoardMembership` (through model).
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Board(models.Model):
    """
    Represents an engineering project board.
    Owner = Jefe de Ingeniería; Members = assigned engineers.
    The many-to-many relation uses `teams.BoardMembership` as a through
    model so that each membership can carry a specialty_role.
    """
    STATUS_ACTIVE   = 'active'
    STATUS_FINISHED = 'finished'
    STATUS_CHOICES  = [
        (STATUS_ACTIVE,   'Active'),
        (STATUS_FINISHED, 'Finished'),
    ]

    title       = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    owner       = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='boards',
    )
    members = models.ManyToManyField(
        User,
        through='teams.BoardMembership',
        related_name='shared_boards',
        blank=True,
        help_text='Engineers who can access and edit tasks on this board.',
    )
    status     = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return str(self.title)

    def is_accessible_by(self, user: User) -> bool:
        """Returns True if user is owner or a board member."""
        return self.owner == user or self.members.filter(pk=user.pk).exists()

    def is_owned_by(self, user: User) -> bool:
        """Returns True only if user is the board owner (Jefe)."""
        return self.owner == user


class Column(models.Model):
    """
    Represents an ordered column within a Board.
    Manual columns are shown as a secondary view below the Scrum/Workload
    perspectives which derive columns from Card.status or Card.assignee.
    """
    board      = models.ForeignKey(Board, on_delete=models.CASCADE, related_name='columns')
    title      = models.CharField(max_length=255)
    order      = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self) -> str:
        return f'{self.board.title} — {self.title}'


class Card(models.Model):
    """
    Represents an engineering task attached to a Column.
    Tracks status, discipline, assignee, progress, and due date.
    """
    # --- Status choices ---
    STATUS_BACKLOG      = 'backlog'
    STATUS_TODO         = 'todo'
    STATUS_IN_PROGRESS  = 'in_progress'
    STATUS_REVIEW       = 'review'
    STATUS_DONE         = 'done'
    STATUS_CHOICES = [
        (STATUS_BACKLOG,     'Backlog'),
        (STATUS_TODO,        'To Do'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_REVIEW,      'Review'),
        (STATUS_DONE,        'Done'),
    ]

    # Statuses a regular member (engineer) may set — cannot reach 'done'
    MEMBER_ALLOWED_STATUSES = [
        STATUS_BACKLOG, STATUS_TODO, STATUS_IN_PROGRESS, STATUS_REVIEW,
    ]

    # --- Discipline choices with Bootstrap colour mapping ---
    DISCIPLINE_MEC    = 'mec'
    DISCIPLINE_ELEC   = 'elec'
    DISCIPLINE_AUTO   = 'auto'
    DISCIPLINE_REFRIG = 'refrig'
    DISCIPLINE_CHOICES = [
        (DISCIPLINE_MEC,    'Mecánica'),
        (DISCIPLINE_ELEC,   'Eléctrica'),
        (DISCIPLINE_AUTO,   'Automatización'),
        (DISCIPLINE_REFRIG, 'Refrigeración'),
    ]
    DISCIPLINE_COLOURS = {
        DISCIPLINE_MEC:    'primary',
        DISCIPLINE_ELEC:   'warning',
        DISCIPLINE_AUTO:   'success',
        DISCIPLINE_REFRIG: 'info',
    }

    column      = models.ForeignKey(Column, on_delete=models.CASCADE, related_name='cards')
    title       = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status      = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_BACKLOG,
    )
    assignee = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='assigned_cards',
        help_text='Engineer responsible for this task.',
    )
    discipline = models.CharField(
        max_length=10,
        choices=DISCIPLINE_CHOICES,
        blank=True,
    )
    progress = models.PositiveSmallIntegerField(
        default=0,
        help_text='Completion percentage (0–100).',
    )
    order      = models.PositiveIntegerField(default=0)
    due_date   = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self) -> str:
        return str(self.title)

    @property
    def is_overdue(self) -> bool:
        """Returns True if card is past its due date and not yet done."""
        if self.due_date and self.status != self.STATUS_DONE:
            return timezone.now() > self.due_date
        return False

    @property
    def discipline_colour(self) -> str:
        """Returns the Bootstrap colour class for this card's discipline."""
        return self.DISCIPLINE_COLOURS.get(self.discipline, 'secondary')


class BoardAnalytics(models.Model):
    """
    Stores archived performance statistics for a finished Board.
    Auto-populated by a post_save signal (boards/signals.py) when
    Board.status transitions to 'finished'.
    """
    board           = models.OneToOneField(Board, on_delete=models.CASCADE, related_name='analytics')
    finished_at     = models.DateTimeField(auto_now_add=True)
    total_cards     = models.IntegerField(default=0)
    completed_cards = models.IntegerField(default=0)
    overdue_cards   = models.IntegerField(default=0)
    avg_progress    = models.FloatField(
        default=0.0,
        help_text='Average progress % across all cards at time of closing.',
    )
    # e.g. {"mec": {"count": 5, "avg_progress": 72.0}, ...}
    discipline_stats = models.JSONField(default=dict, blank=True)

    def __str__(self) -> str:
        return f'Analytics for {self.board.title}'

    @property
    def completion_rate(self) -> float:
        """Returns percentage of completed cards (0–100)."""
        if self.total_cards == 0:
            return 0.0
        return round((self.completed_cards / self.total_cards) * 100, 1)

    @property
    def overdue_rate(self) -> float:
        """Returns percentage of overdue cards (0–100)."""
        if self.total_cards == 0:
            return 0.0
        return round((self.overdue_cards / self.total_cards) * 100, 1)
