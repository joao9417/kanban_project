"""
boards/signals.py

post_save signal for Board: when status transitions to 'finished',
auto-calculates and persists analytics into BoardAnalytics.
"""
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


@receiver(post_save, sender='boards.Board')
def handle_board_save(sender, instance, created, **kwargs):
    """
    Triggered every time a Board is saved.
    Only acts when the board status transitions to 'finished'.
    Creates or updates the associated BoardAnalytics record.
    """
    if instance.status != 'finished':
        return

    # Avoid circular import
    from .models import BoardAnalytics

    all_cards = _get_all_board_cards(instance)
    now = timezone.now()

    total_cards     = all_cards.count()
    completed_cards = all_cards.filter(status='done').count()
    overdue_cards   = sum(
        1 for card in all_cards
        if card.due_date and card.status != 'done' and now > card.due_date
    )
    avg_progress = (
        sum(c.progress for c in all_cards) / total_cards if total_cards > 0 else 0.0
    )
    discipline_stats = _calculate_discipline_stats(all_cards)

    BoardAnalytics.objects.update_or_create(
        board=instance,
        defaults={
            'total_cards':      total_cards,
            'completed_cards':  completed_cards,
            'overdue_cards':    overdue_cards,
            'avg_progress':     round(avg_progress, 2),
            'discipline_stats': discipline_stats,
        },
    )


def _get_all_board_cards(board):
    """Returns a QuerySet of all Cards across all Columns of a Board."""
    from .models import Card
    return Card.objects.filter(column__board=board)


def _calculate_discipline_stats(cards):
    """
    Calculates per-discipline statistics.
    Returns: {"mec": {"count": N, "avg_progress": X}, ...}
    """
    from .models import Card
    disciplines = [code for code, _ in Card.DISCIPLINE_CHOICES]
    stats = {}
    for discipline in disciplines:
        discipline_cards = [c for c in cards if c.discipline == discipline]
        count = len(discipline_cards)
        avg_progress = (
            sum(c.progress for c in discipline_cards) / count if count > 0 else 0.0
        )
        stats[discipline] = {
            'count':        count,
            'avg_progress': round(avg_progress, 2),
        }
    return stats
