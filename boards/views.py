"""
boards/views.py

All views related to Boards, Columns, Cards, and Board Analytics.
Team/member management has been extracted to the `teams` app.

Permission helpers:
  - is_board_member  → owner or invited member
  - is_board_owner   → strictly the owner (Jefe de Ingeniería)
"""
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import (
    ListView, DetailView, CreateView, UpdateView, DeleteView, View,
)
from django.urls import reverse_lazy, reverse
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from typing import Any, Dict

from .models import Board, Column, Card, BoardAnalytics
from .forms import BoardForm, ColumnForm, CardForm


# ---------------------------------------------------------------------------
# Permission helpers
# ---------------------------------------------------------------------------

def is_board_member(user: User, board: Board) -> bool:
    """Returns True if user is the owner OR an invited member."""
    return board.is_accessible_by(user)


def is_board_owner(user: User, board: Board) -> bool:
    """Returns True only if user is the board owner (Jefe)."""
    return board.is_owned_by(user)


def get_board_or_403(pk: int, user: User) -> Board:
    """Fetches Board by pk; raises 403 if user has no access."""
    board = get_object_or_404(Board, pk=pk)
    if not is_board_member(user, board):
        raise PermissionDenied
    return board


def get_board_owner_or_403(pk: int, user: User) -> Board:
    """Fetches Board by pk; raises 403 if user is not the owner."""
    board = get_object_or_404(Board, pk=pk)
    if not is_board_owner(user, board):
        raise PermissionDenied
    return board


# ---------------------------------------------------------------------------
# Auth views
# ---------------------------------------------------------------------------

def register(request: HttpRequest) -> HttpResponse:
    """Handles new user registration using Django's built-in UserCreationForm."""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Registration successful! Welcome aboard.')
            return redirect('board_list')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


# ---------------------------------------------------------------------------
# Board views
# ---------------------------------------------------------------------------

class BoardListView(LoginRequiredMixin, ListView):
    """
    Dashboard: lists boards owned by the current user AND boards shared with them.
    Context keys: owned_boards, shared_boards.
    """
    model                = Board
    template_name        = 'boards/board_list.html'
    context_object_name  = 'boards'

    def get_queryset(self):
        # Not used directly; split into two sets in get_context_data
        return Board.objects.none()

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['owned_boards']  = Board.objects.filter(owner=user).order_by('-created_at')
        context['shared_boards'] = Board.objects.filter(members=user).order_by('-created_at')
        return context


class BoardCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """Creates a new project board. Auto-creates a default 'General' column."""
    model            = Board
    form_class       = BoardForm
    template_name    = 'boards/board_form.html'
    success_url      = reverse_lazy('board_list')
    success_message  = 'Board created successfully!'

    def form_valid(self, form):
        form.instance.owner = self.request.user
        response = super().form_valid(form)
        # Guarantee at least one column so cards can always be created
        Column.objects.get_or_create(
            board=self.object,
            defaults={'title': 'General', 'order': 0},
        )
        return response


class BoardUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Allows only the board owner to edit board metadata."""
    model           = Board
    form_class      = BoardForm
    template_name   = 'boards/board_form.html'
    success_message = 'Board updated successfully!'

    def get_object(self, queryset=None):
        return get_board_owner_or_403(self.kwargs['pk'], self.request.user)

    def get_success_url(self) -> str:
        return reverse('board_list')


class BoardDeleteView(LoginRequiredMixin, DeleteView):
    """Allows only the board owner to delete a board."""
    model               = Board
    template_name       = 'boards/confirm_delete.html'
    success_url         = reverse_lazy('board_list')
    context_object_name = 'object'

    def get_object(self, queryset=None):
        return get_board_owner_or_403(self.kwargs['pk'], self.request.user)

    def form_valid(self, form) -> HttpResponse:
        messages.success(self.request, 'Board deleted successfully!')
        return super().form_valid(form)


class BoardDetailView(LoginRequiredMixin, DetailView):
    """
    Main board view with dual-view toggle:
      ?view=scrum    → cards grouped by status (default)
      ?view=workload → cards grouped by assignee
    """
    model               = Board
    template_name       = 'boards/board_detail.html'
    context_object_name = 'board'

    def get_object(self, queryset=None):
        return get_board_or_403(self.kwargs['pk'], self.request.user)

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context   = super().get_context_data(**kwargs)
        board     = self.object
        user      = self.request.user
        view_mode = self.request.GET.get('view', 'scrum')

        all_cards = Card.objects.filter(column__board=board).select_related('assignee')

        context['view_mode'] = view_mode
        context['is_owner']  = is_board_owner(user, board)

        if view_mode == 'workload':
            context['workload_data'] = self._build_workload_data(board, all_cards)
        else:
            context['scrum_data'] = self._build_scrum_data(all_cards)

        columns                   = board.columns.prefetch_related('cards').order_by('order')
        context['columns']        = columns
        context['default_column'] = columns.first()

        # Default Tasks modal data: catalog + role→user mapping for preview badges
        from teams.models import BoardMembership
        role_to_user = {
            m.specialty_role: m.user.get_full_name() or m.user.username
            for m in board.memberships.select_related('user').all()
        }
        context['default_tasks']     = DEFAULT_TASKS
        context['discipline_labels'] = DISCIPLINE_LABELS
        context['role_to_user']      = role_to_user

        return context


    def _build_scrum_data(self, all_cards):
        """
        Groups all board cards into status buckets matching the project workflow.
        Returns a list of dictionaries containing the status key, human title,
        and a list of card objects for that status. Used for the default column view.
        """
        return [
            {
                'status': status_key,
                'label':  status_label,
                # Filter cards in-memory to avoid redundant N+1 queries per status
                'cards':  [c for c in all_cards if c.status == status_key],
            }
            for status_key, status_label in Card.STATUS_CHOICES
        ]

    def _build_workload_data(self, board, all_cards):
        """
        Builds a resource-centric view of the board tasks.
        Organizes tasks by assignee (Board Owner first, then members alphabetically).
        Calculates total cards and real-time overdue alerts per engineer.
        Includes an 'Unassigned' bucket for cards without a designated specialist.
        """
        now     = timezone.now()
        # Ensure Owner is always the first column in the workload view
        members = [board.owner] + list(board.members.exclude(pk=board.owner.pk))

        workload          = []
        assigned_card_ids = set()

        for member in members:
            # Match cards to assignee (prefetch_related used in all_cards for performance)
            member_cards = [c for c in all_cards if c.assignee_id == member.pk]
            assigned_card_ids.update(c.pk for c in member_cards)

            # Count overdue items: due date passed and status not 'done'
            overdue_count = sum(
                1 for c in member_cards
                if c.due_date and c.status != Card.STATUS_DONE and now > c.due_date
            )

            workload.append({
                'member':  member,
                'cards':   member_cards,
                'total':   len(member_cards),
                'overdue': overdue_count,
            })

        unassigned = [c for c in all_cards if c.pk not in assigned_card_ids]
        if unassigned:
            unassigned_overdue = sum(
                1 for c in unassigned
                if c.due_date and c.status != Card.STATUS_DONE and now > c.due_date
            )
            workload.append({
                'member':  None,
                'cards':   unassigned,
                'total':   len(unassigned),
                'overdue': unassigned_overdue,
            })

        return workload


class BoardAnalyticsView(LoginRequiredMixin, DetailView):
    """Displays the archived analytics for a finished board."""
    model               = Board
    template_name       = 'boards/board_analytics.html'
    context_object_name = 'board'

    def get_object(self, queryset=None):
        return get_board_or_403(self.kwargs['pk'], self.request.user)

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        try:
            context['analytics'] = self.object.analytics
        except BoardAnalytics.DoesNotExist:
            context['analytics'] = None
        context['is_owner'] = is_board_owner(self.request.user, self.object)
        return context


# ---------------------------------------------------------------------------
# Column views
# ---------------------------------------------------------------------------

class ColumnCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """Creates a column within a specific board."""
    model           = Column
    form_class      = ColumnForm
    template_name   = 'boards/column_form.html'
    success_message = 'Column created successfully!'

    def form_valid(self, form):
        board = get_board_or_403(self.kwargs['board_id'], self.request.user)
        form.instance.board = board
        return super().form_valid(form)

    def get_success_url(self) -> str:
        return reverse('board_detail', kwargs={'pk': self.kwargs['board_id']})


class ColumnUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Edits an existing column (owner only)."""
    model           = Column
    form_class      = ColumnForm
    template_name   = 'boards/column_form.html'
    success_message = 'Column updated successfully!'

    def get_queryset(self):
        return Column.objects.filter(board__owner=self.request.user)

    def get_success_url(self) -> str:
        return reverse('board_detail', kwargs={'pk': self.object.board.pk})


class ColumnDeleteView(LoginRequiredMixin, DeleteView):
    """Deletes a column (owner only)."""
    model               = Column
    template_name       = 'boards/confirm_delete.html'
    context_object_name = 'object'

    def get_queryset(self):
        return Column.objects.filter(board__owner=self.request.user)

    def get_success_url(self) -> str:
        return reverse('board_detail', kwargs={'pk': self.object.board.pk})

    def form_valid(self, form) -> HttpResponse:
        messages.success(self.request, 'Column deleted successfully!')
        return super().form_valid(form)


# ---------------------------------------------------------------------------
# Card views
# ---------------------------------------------------------------------------

class CardCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """Creates a card within a specific column."""
    model           = Card
    form_class      = CardForm
    template_name   = 'boards/card_form.html'
    success_message = 'Card created successfully!'

    def _get_column(self):
        column = get_object_or_404(Column, pk=self.kwargs['column_id'])
        if not is_board_member(self.request.user, column.board):
            raise PermissionDenied
        return column

    def get_form_kwargs(self):
        kwargs            = super().get_form_kwargs()
        column            = self._get_column()
        kwargs['board']   = column.board
        kwargs['is_owner'] = is_board_owner(self.request.user, column.board)
        return kwargs

    def form_valid(self, form):
        form.instance.column = self._get_column()
        return super().form_valid(form)

    def get_success_url(self) -> str:
        return reverse('board_detail', kwargs={'pk': self.object.column.board.pk})

    def get_context_data(self, **kwargs):
        context          = super().get_context_data(**kwargs)
        context['board'] = self._get_column().board
        return context


class CardUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """
    Edits an existing card.
    Only the board owner (Jefe) may promote a card to 'done'.
    """
    model           = Card
    form_class      = CardForm
    template_name   = 'boards/card_form.html'
    success_message = 'Card updated successfully!'

    def get_queryset(self):
        user = self.request.user
        return (
            Card.objects.filter(column__board__owner=user)
            | Card.objects.filter(column__board__members=user)
        ).distinct()

    def get_form_kwargs(self):
        kwargs             = super().get_form_kwargs()
        board              = self.object.column.board
        kwargs['board']    = board
        kwargs['is_owner'] = is_board_owner(self.request.user, board)
        return kwargs

    def form_valid(self, form):
        board      = self.object.column.board
        new_status = form.cleaned_data.get('status')
        if new_status == Card.STATUS_DONE and not is_board_owner(self.request.user, board):
            form.add_error('status', 'Only the project owner (Jefe) can mark a task as Done.')
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_success_url(self) -> str:
        return reverse('board_detail', kwargs={'pk': self.object.column.board.pk})

    def get_context_data(self, **kwargs):
        context          = super().get_context_data(**kwargs)
        context['board'] = self.object.column.board
        return context


class CardDeleteView(LoginRequiredMixin, DeleteView):
    """Deletes a card (member or owner)."""
    model               = Card
    template_name       = 'boards/confirm_delete.html'
    context_object_name = 'object'

    def get_queryset(self):
        user = self.request.user
        return (
            Card.objects.filter(column__board__owner=user)
            | Card.objects.filter(column__board__members=user)
        ).distinct()


    def get_success_url(self) -> str:
        return reverse('board_detail', kwargs={'pk': self.object.column.board.pk})

    def form_valid(self, form) -> HttpResponse:
        messages.success(self.request, 'Card deleted successfully!')
        return super().form_valid(form)


# ---------------------------------------------------------------------------
# Predefined task catalog
# ---------------------------------------------------------------------------

#: Predefined task templates grouped by discipline code.
#: Each entry maps a discipline key to a list of default task title strings.
#: The discipline keys match Card.DISCIPLINE_* and BoardMembership.ROLE_*.
DEFAULT_TASKS: Dict[str, list] = {
    'mec': [
        'Planteamiento SM',
        'Cálculo Tuberías',
        'Refrigerante',
        'Aislamiento',
        'Drenajes',
        'Soportes',
    ],
    'elec': [
        'Montaje de Bandejas',
        'Tendido de Cables',
        'Conexión de Tableros',
        'Sensores',
        'Tierras',
    ],
    'auto': [
        'Configuración de Controladores (Dixell/Carel)',
        'Programación PLC/HMI',
        'Red Modbus',
        'Scada',
    ],
    'refrig': [
        'Prueba Nitrógeno',
        'Vacío',
        'Carga Refrigerante',
        'Ajuste Recalentamiento',
        'Acta de Entrega',
    ],
}

# Human-readable labels for each discipline (matches Card.DISCIPLINE_CHOICES)
DISCIPLINE_LABELS: Dict[str, str] = {
    'mec':    'Mecánica',
    'elec':   'Eléctrica',
    'auto':   'Automatización',
    'refrig': 'Arranque / Refrigeración',
}


# ---------------------------------------------------------------------------
# Default Tasks (bulk creation) view
# ---------------------------------------------------------------------------

class BoardDefaultTasksView(LoginRequiredMixin, View):
    """
    POST-only endpoint that bulk-creates predefined task cards in the board's
    Backlog column.

    Form fields (submitted from the modal):
      - ``sel_{disc}_{i}``  (checkbox, value = task title) — one per selected task.
      - ``due_{disc}_{i}``  (datetime-local input) — optional due date per task.

    Auto-assignment logic:
      - Looks up the board's memberships to build a role → User mapping.
      - The discipline code is identical to the membership specialty_role code, so
        if a member with role 'mec' exists they are assigned to all 'mec' tasks.
      - If no matching specialist is found the card is created unassigned.

    Only the board owner (Jefe) may access this endpoint.
    """

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        board = get_board_owner_or_403(pk, request.user)

        # Use the first column as the Backlog target
        column = board.columns.order_by('order', 'created_at').first()
        if column is None:
            messages.error(request, 'This board has no columns yet. Create a column first.')
            return redirect('board_detail', pk=pk)

        # Build role → User map from current memberships
        from teams.models import BoardMembership
        role_to_user = {
            m.specialty_role: m.user
            for m in board.memberships.select_related('user').all()
        }

        created_count = 0
        POST = request.POST

        for disc, task_list in DEFAULT_TASKS.items():
            # Get specialist for this discipline (role codes match discipline codes)
            assignee = role_to_user.get(disc)
            for i, task_title in enumerate(task_list):
                # The browser sends check_disc_index for each row marked as active
                checkbox_key = f'sel_{disc}_{i}'
                if checkbox_key not in POST:
                    continue

                # Parse optional due date
                due_date = None
                due_raw = POST.get(f'due_{disc}_{i}', '').strip()
                if due_raw:
                    from django.utils.dateparse import parse_datetime
                    due_date = parse_datetime(due_raw)

                # Determine next order value so new cards appear at the bottom
                next_order = (
                    Card.objects.filter(column=column).count()
                )

                Card.objects.create(
                    column     = column,
                    title      = task_title,
                    discipline = disc,
                    status     = Card.STATUS_BACKLOG,
                    assignee   = assignee,
                    due_date   = due_date,
                    progress   = 0,
                    order      = next_order,
                )
                created_count += 1

        if created_count > 0:
            messages.success(
                request,
                f'{created_count} default task{"s" if created_count != 1 else ""} '
                f'created in the Backlog.',
            )
        else:
            messages.warning(request, 'No tasks were selected.')

        return redirect(reverse('board_detail', kwargs={'pk': pk}))

