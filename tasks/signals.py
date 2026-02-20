from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


@receiver(post_save, sender='tasks.Board')
def handle_board_save(sender, instance, created, **kwargs):
    """
    post_save signal for Board.
    When a board's status transitions to 'finished', automatically calculate
    and persist analytics metrics into BoardAnalytics.
    """
    if instance.status != 'finished':
        return  # Only act on boards being finished

    # Avoid circular import by importing here
    from .models import BoardAnalytics

    # Gather all cards across all columns of this board
    all_cards = _get_all_board_cards(instance)
    now = timezone.now()

    total_cards = all_cards.count()
    completed_cards = all_cards.filter(status='done').count()

    # Overdue: passed due_date AND not marked done
    overdue_cards = sum(
        1 for card in all_cards
        if card.due_date and card.status != 'done' and now > card.due_date
    )

    # Average progress across all cards
    if total_cards > 0:
        avg_progress = sum(c.progress for c in all_cards) / total_cards
    else:
        avg_progress = 0.0

    # Per-discipline stats: {discipline_key: {count, avg_days}}
    discipline_stats = _calculate_discipline_stats(all_cards)

    # Create or update the analytics record
    BoardAnalytics.objects.update_or_create(
        board=instance,
        defaults={
            'total_cards': total_cards,
            'completed_cards': completed_cards,
            'overdue_cards': overdue_cards,
            'avg_progress': round(avg_progress, 2),
            'discipline_stats': discipline_stats,
        }
    )


def _get_all_board_cards(board):
    """
    Returns a QuerySet of all Cards belonging to all Columns of a Board.
    """
    from .models import Card
    return Card.objects.filter(column__board=board)


def _calculate_discipline_stats(cards):
    """
    Calculates per-discipline statistics from a card queryset.

    Returns a dict in the form:
    {
        "mec":    {"count": N, "avg_progress": X},
        "elec":   {"count": N, "avg_progress": X},
        ...
    }
    Average completion days cannot be calculated without start_date; we store
    avg_progress per discipline as the primary metric for now.
    """
    from .models import Card

    disciplines = [code for code, _ in Card.DISCIPLINE_CHOICES]
    stats = {}

    for discipline in disciplines:
        discipline_cards = [c for c in cards if c.discipline == discipline]
        count = len(discipline_cards)
        if count > 0:
            avg_progress = sum(c.progress for c in discipline_cards) / count
        else:
            avg_progress = 0.0

        stats[discipline] = {
            'count': count,
            'avg_progress': round(avg_progress, 2),
        }

    return stats
