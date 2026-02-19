from django.db import models
from django.contrib.auth.models import User

class Board(models.Model):
    """
    Represents a Kanban board owned by a user.
    """
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='boards')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        """
        Returns the string representation of the board.
        """
        return str(self.title)

class Column(models.Model):
    """
    Represents a column within a Board (e.g., Todo, In Progress, Done).
    """
    board = models.ForeignKey(Board, on_delete=models.CASCADE, related_name='columns')
    title = models.CharField(max_length=255)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self) -> str:
        """
        Returns the string representation of the column, including the board title.
        """
        return f"{self.board.title} - {self.title}"

class Card(models.Model):
    """
    Represents a task card within a Column.
    """
    column = models.ForeignKey(Column, on_delete=models.CASCADE, related_name='cards')
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)
    due_date = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['order', 'created_at']

    def __str__(self) -> str:
        """
        Returns the string representation of the card.
        """
        return str(self.title)
