"""
teams/models.py

BoardMembership model: the explicit through model for Board.members.
Each membership records which engineer belongs to which board AND their
engineering specialty role (colour-coded for the UI).
"""
from django.db import models
from django.contrib.auth.models import User


class BoardMembership(models.Model):
    """
    Through model linking a User (engineer) to a Board with a mandatory
    specialty_role.  One user can be a member of many boards, and each
    board can have many engineers, but the (board, user) pair is unique.

    Specialty roles and their UI badge colours:
        mec    → Ingeniero Mecánico      → Bootstrap 'primary'  (blue)
        elec   → Ingeniero Eléctrico     → Bootstrap 'warning'  (yellow)
        auto   → Ingeniero de Control    → Bootstrap 'success'  (green)
        refrig → Técnico de Refrigeración→ Bootstrap 'danger'   (red)
    """
    ROLE_MEC    = 'mec'
    ROLE_ELEC   = 'elec'
    ROLE_AUTO   = 'auto'
    ROLE_REFRIG = 'refrig'
    ROLE_CHOICES = [
        (ROLE_MEC,    'Ingeniero Mecánico'),
        (ROLE_ELEC,   'Ingeniero Eléctrico'),
        (ROLE_AUTO,   'Ingeniero de Control'),
        (ROLE_REFRIG, 'Técnico de Refrigeración'),
    ]

    # Badge colour class per role (Bootstrap contextual colours)
    ROLE_BADGE_COLOURS = {
        ROLE_MEC:    'primary',  # blue
        ROLE_ELEC:   'warning',  # yellow
        ROLE_AUTO:   'success',  # green
        ROLE_REFRIG: 'danger',   # red
    }

    board = models.ForeignKey(
        'boards.Board',
        on_delete=models.CASCADE,
        related_name='memberships',
    )
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='board_memberships',
    )
    specialty_role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        help_text='Engineering specialty role for this board.',
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # A user can only appear once per board
        unique_together = ('board', 'user')
        ordering = ['joined_at']

    def __str__(self) -> str:
        return f'{self.user.username} @ {self.board.title} [{self.get_specialty_role_display()}]'

    @property
    def role_badge_colour(self) -> str:
        """Returns the Bootstrap colour class for this membership's role."""
        return self.ROLE_BADGE_COLOURS.get(self.specialty_role, 'secondary')
