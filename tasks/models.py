from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone


class Board(models.Model):
    """
    Represents an engineering project board.
    Owner = Jefe de Ingeniería; Members = assigned engineers.
    """
    STATUS_ACTIVE = 'active'
    STATUS_FINISHED = 'finished'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_FINISHED, 'Finished'),
    ]

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='boards'
    )
    members = models.ManyToManyField(
        User,
        related_name='shared_boards',
        blank=True,
        help_text="Engineers who can access and edit tasks on this board."
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
        default=STATUS_ACTIVE
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
    Represents a manual column within a Board.
    Kept for backwards-compat; main board views now use Card.status or assignee.
    """
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name='columns')
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self) -> str:
        return f"{self.board.title} - {self.title}"


class Card(models.Model):
    """
    Represents an engineering task on a Board column.
    Extends basic card with status, assignee, discipline, and progress tracking.
    """
    # --- Status choices ---
    STATUS_BACKLOG = 'backlog'
    STATUS_TODO = 'todo'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_REVIEW = 'review'
    STATUS_DONE = 'done'
    STATUS_CHOICES = [
        (STATUS_BACKLOG,     'Backlog'),
        (STATUS_TODO,        'To Do'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_REVIEW,      'Review'),
        (STATUS_DONE,        'Done'),
    ]

    # Statuses accessible by regular members (engineers) — cap at Review
    MEMBER_ALLOWED_STATUSES = [
        STATUS_BACKLOG, STATUS_TODO, STATUS_IN_PROGRESS, STATUS_REVIEW
    ]

    # --- Discipline choices with colour mapping (used in templates) ---
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

    # Bootstrap colour class per discipline (used in templates via dict or tag)
    DISCIPLINE_COLOURS = {
        DISCIPLINE_MEC:    'primary',
        DISCIPLINE_ELEC:   'warning',
        DISCIPLINE_AUTO:   'success',
        DISCIPLINE_REFRIG: 'info',
    }

    column = models.ForeignKey(Column, on_delete=models.CASCADE, related_name='cards')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_BACKLOG
    )
    assignee = models.ForeignKey(
        User,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name='assigned_cards',
        help_text="Engineer responsible for this task."
    )
    discipline = models.CharField(
        max_length=10,
        choices=DISCIPLINE_CHOICES,
        blank=True
    )
    progress = models.PositiveSmallIntegerField(
        default=0,
        help_text="Completion percentage (0-100)."
    )
    order = models.PositiveIntegerField(default=0)
    due_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self) -> str:
        return str(self.title)

    @property
    def is_overdue(self) -> bool:
        """Returns True if the card is past its due date and not done."""
        if self.due_date and self.status != self.STATUS_DONE:
            return timezone.now() > self.due_date
        return False

    @property
    def discipline_colour(self) -> str:
        """Returns the Bootstrap colour class for this card's discipline."""
        return self.DISCIPLINE_COLOURS.get(self.discipline, 'secondary')


class BoardAnalytics(models.Model):
    """
    Stores archived statistics for a finished Board.
    Populated automatically via post_save signal when Board.status → 'finished'.
    """
    board = models.OneToOneField(
        Board,
        on_delete=models.CASCADE,
        related_name='analytics'
    )
    finished_at = models.DateTimeField(auto_now_add=True)
    total_cards = models.IntegerField(default=0)
    completed_cards = models.IntegerField(default=0)
    overdue_cards = models.IntegerField(default=0)
    avg_progress = models.FloatField(
        default=0.0,
        help_text="Average progress % across all cards at time of closing."
    )
    # JSON structure: {"mec": {"count": N, "avg_days": X}, ...}
    discipline_stats = models.JSONField(default=dict, blank=True)

    def __str__(self) -> str:
        return f"Analytics for {self.board.title}"

    @property
    def completion_rate(self) -> float:
        """Returns the percentage of completed cards (0–100)."""
        if self.total_cards == 0:
            return 0.0
        return round((self.completed_cards / self.total_cards) * 100, 1)

    @property
    def overdue_rate(self) -> float:
        """Returns the percentage of overdue cards (0–100)."""
        if self.total_cards == 0:
            return 0.0
        return round((self.overdue_cards / self.total_cards) * 100, 1)
