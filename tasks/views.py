from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView, View
from django.urls import reverse_lazy, reverse
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.utils import timezone
from .models import Board, Column, Card, BoardAnalytics
from .forms import BoardForm, ColumnForm, CardForm, MemberForm
from typing import Any, Dict


# ---------------------------------------------------------------------------
# Permission helpers
# ---------------------------------------------------------------------------

def is_board_member(user: User, board: Board) -> bool:
    """Returns True if user is the owner OR an invited member of the board."""
    return board.is_accessible_by(user)


def is_board_owner(user: User, board: Board) -> bool:
    """Returns True only if user is the board owner (Jefe de Ingeniería)."""
    return board.is_owned_by(user)


def get_board_or_403(pk: int, user: User) -> Board:
    """
    Fetches a Board by pk; raises 403 if the user has no access.
    Replaces get_object_or_404(owner=user) throughout the codebase.
    """
    board = get_object_or_404(Board, pk=pk)
    if not is_board_member(user, board):
        raise PermissionDenied
    return board


def get_board_owner_or_403(pk: int, user: User) -> Board:
    """Fetches a Board by pk; raises 403 if user is not the owner."""
    board = get_object_or_404(Board, pk=pk)
    if not is_board_owner(user, board):
        raise PermissionDenied
    return board


# ---------------------------------------------------------------------------
# Auth views
# ---------------------------------------------------------------------------

def register(request: HttpRequest) -> HttpResponse:
    """Handles user registration using the built-in UserCreationForm."""
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful! Welcome aboard.")
            return redirect('board_list')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


# ---------------------------------------------------------------------------
# Board views
# ---------------------------------------------------------------------------

class BoardListView(LoginRequiredMixin, ListView):
    """
    Dashboard: lists boards owned by the user AND boards shared with them.
    """
    model = Board
    template_name = 'tasks/board_list.html'
    context_object_name = 'boards'

    def get_queryset(self):
        # Not used directly; we split into two sets in get_context_data
        return Board.objects.none()

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        user = self.request.user
        context['owned_boards'] = Board.objects.filter(owner=user).order_by('-created_at')
        context['shared_boards'] = Board.objects.filter(members=user).order_by('-created_at')
        return context


class BoardCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """Handles the creation of a new project board."""
    model = Board
    form_class = BoardForm
    template_name = 'tasks/board_form.html'
    success_url = reverse_lazy('board_list')
    success_message = "Board created successfully!"

    def form_valid(self, form):
        form.instance.owner = self.request.user
        response = super().form_valid(form)
        # Auto-create a default column so cards can always be created
        Column.objects.get_or_create(
            board=self.object, defaults={'title': 'General', 'order': 0}
        )
        return response


class BoardUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Only the owner may edit board metadata."""
    model = Board
    form_class = BoardForm
    template_name = 'tasks/board_form.html'
    success_message = "Board updated successfully!"

    def get_object(self, queryset=None):
        return get_board_owner_or_403(self.kwargs['pk'], self.request.user)

    def get_success_url(self) -> str:
        return reverse('board_list')


class BoardDeleteView(LoginRequiredMixin, DeleteView):
    """Only the owner may delete a board."""
    model = Board
    template_name = 'tasks/confirm_delete.html'
    success_url = reverse_lazy('board_list')
    context_object_name = 'object'

    def get_object(self, queryset=None):
        return get_board_owner_or_403(self.kwargs['pk'], self.request.user)

    def form_valid(self, form) -> HttpResponse:
        messages.success(self.request, "Board deleted successfully!")
        return super().form_valid(form)


class BoardDetailView(LoginRequiredMixin, DetailView):
    """
    Board detail with dual-view toggle:
      ?view=scrum    → columns grouped by Card.status  (default)
      ?view=workload → columns grouped by Card.assignee
    """
    model = Board
    template_name = 'tasks/board_detail.html'
    context_object_name = 'board'

    def get_object(self, queryset=None):
        return get_board_or_403(self.kwargs['pk'], self.request.user)

    def get_context_data(self, **kwargs: Any) -> Dict[str, Any]:
        context = super().get_context_data(**kwargs)
        board = self.object
        user = self.request.user
        view_mode = self.request.GET.get('view', 'scrum')

        # All cards for this board, prefetched
        all_cards = Card.objects.filter(column__board=board).select_related('assignee')

        context['view_mode'] = view_mode
        context['is_owner'] = is_board_owner(user, board)

        if view_mode == 'workload':
            context['workload_data'] = self._build_workload_data(board, all_cards)
        else:
            context['scrum_data'] = self._build_scrum_data(all_cards)

        # Keep manual columns available for column management
        columns = board.columns.prefetch_related('cards').order_by('order')
        context['columns'] = columns
        # Provide a default column for "Add Task" buttons (guaranteed by BoardCreateView)
        context['default_column'] = columns.first()
        return context

    def _build_scrum_data(self, all_cards):
        """
        Returns a list of dicts, one per status column:
        [{'label': 'Backlog', 'status': 'backlog', 'cards': [...]}, ...]
        """
        scrum_columns = []
        for status_key, status_label in Card.STATUS_CHOICES:
            cards = [c for c in all_cards if c.status == status_key]
            scrum_columns.append({
                'status': status_key,
                'label': status_label,
                'cards': cards,
            })
        return scrum_columns

    def _build_workload_data(self, board, all_cards):
        """
        Returns a list of dicts, one per board member (including owner):
        [{
            'member': User,
            'cards': [...],
            'total': N,
            'overdue': M,
        }, ...]
        Plus an 'Unassigned' bucket.
        """
        now = timezone.now()
        # Build member list: owner always first, then members
        members = [board.owner] + list(board.members.exclude(pk=board.owner.pk))

        workload = []
        assigned_card_ids = set()

        for member in members:
            member_cards = [c for c in all_cards if c.assignee_id == member.pk]
            assigned_card_ids.update(c.pk for c in member_cards)
            overdue_count = sum(
                1 for c in member_cards
                if c.due_date and c.status != Card.STATUS_DONE and now > c.due_date
            )
            workload.append({
                'member': member,
                'cards': member_cards,
                'total': len(member_cards),
                'overdue': overdue_count,
            })

        # Unassigned cards bucket
        unassigned = [c for c in all_cards if c.pk not in assigned_card_ids]
        if unassigned:
            unassigned_overdue = sum(
                1 for c in unassigned
                if c.due_date and c.status != Card.STATUS_DONE and now > c.due_date
            )
            workload.append({
                'member': None,  # Signals "Unassigned" in template
                'cards': unassigned,
                'total': len(unassigned),
                'overdue': unassigned_overdue,
            })

        return workload


# ---------------------------------------------------------------------------
# Board member management (owner only)
# ---------------------------------------------------------------------------

class BoardMembersView(LoginRequiredMixin, View):
    """
    GET:  display current members and add-member form.
    POST: add a member by username (owner only).
    """
    template_name = 'tasks/board_members.html'

    def get_board(self, pk):
        return get_board_owner_or_403(pk, self.request.user)

    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        board = self.get_board(pk)
        form = MemberForm()
        return render(request, self.template_name, {'board': board, 'form': form})

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        board = self.get_board(pk)
        action = request.POST.get('action')

        if action == 'remove':
            member_id = request.POST.get('member_id')
            try:
                user_to_remove = board.members.get(pk=member_id)
                board.members.remove(user_to_remove)
                messages.success(request, f"{user_to_remove.username} removed from the board.")
            except User.DoesNotExist:
                messages.error(request, "Member not found.")
        else:
            form = MemberForm(request.POST)
            if form.is_valid():
                username = form.cleaned_data['username']
                try:
                    user_to_add = User.objects.get(username=username)
                    if user_to_add == board.owner:
                        messages.warning(request, "The owner is already on this board.")
                    elif board.members.filter(pk=user_to_add.pk).exists():
                        messages.warning(request, f"{username} is already a member.")
                    else:
                        board.members.add(user_to_add)
                        messages.success(request, f"{username} added to the board.")
                except User.DoesNotExist:
                    messages.error(request, f"User '{username}' does not exist.")

        return redirect('board_members', pk=pk)


# ---------------------------------------------------------------------------
# Board finish view (owner only — signal handles analytics creation)
# ---------------------------------------------------------------------------

class BoardFinishView(LoginRequiredMixin, View):
    """
    POST: marks the board as 'finished'.
    The post_save signal in signals.py handles BoardAnalytics creation.
    Only the board owner (Jefe) may call this endpoint.
    """
    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        board = get_board_owner_or_403(pk, request.user)
        if board.status == Board.STATUS_FINISHED:
            messages.warning(request, "This board is already finished.")
        else:
            board.status = Board.STATUS_FINISHED
            board.save()  # triggers post_save signal → creates BoardAnalytics
            messages.success(request, f"Project '{board.title}' has been closed. Analytics saved.")
        return redirect('board_analytics', pk=pk)


# ---------------------------------------------------------------------------
# Board analytics view (member or owner)
# ---------------------------------------------------------------------------

class BoardAnalyticsView(LoginRequiredMixin, DetailView):
    """Displays archived statistics for a finished board."""
    model = Board
    template_name = 'tasks/board_analytics.html'
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
    """Handles the creation of a new column within a specific board."""
    model = Column
    form_class = ColumnForm
    template_name = 'tasks/column_form.html'
    success_message = "Column created successfully!"

    def form_valid(self, form):
        board = get_board_or_403(self.kwargs['board_id'], self.request.user)
        form.instance.board = board
        return super().form_valid(form)

    def get_success_url(self) -> str:
        return reverse('board_detail', kwargs={'pk': self.kwargs['board_id']})


class ColumnUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """Handles the modification of an existing column."""
    model = Column
    form_class = ColumnForm
    template_name = 'tasks/column_form.html'
    success_message = "Column updated successfully!"

    def get_queryset(self):
        return Column.objects.filter(board__owner=self.request.user)

    def get_success_url(self) -> str:
        return reverse('board_detail', kwargs={'pk': self.object.board.pk})


class ColumnDeleteView(LoginRequiredMixin, DeleteView):
    """Handles the deletion of a column."""
    model = Column
    template_name = 'tasks/confirm_delete.html'
    context_object_name = 'object'

    def get_queryset(self):
        return Column.objects.filter(board__owner=self.request.user)

    def get_success_url(self) -> str:
        return reverse('board_detail', kwargs={'pk': self.object.board.pk})

    def form_valid(self, form) -> HttpResponse:
        messages.success(self.request, "Column deleted successfully!")
        return super().form_valid(form)


# ---------------------------------------------------------------------------
# Card views
# ---------------------------------------------------------------------------

class CardCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    """Handles the creation of a new card within a specific column."""
    model = Card
    form_class = CardForm
    template_name = 'tasks/card_form.html'
    success_message = "Card created successfully!"

    def _get_column(self):
        column = get_object_or_404(Column, pk=self.kwargs['column_id'])
        if not is_board_member(self.request.user, column.board):
            raise PermissionDenied
        return column

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['board'] = self._get_column().board
        kwargs['is_owner'] = is_board_owner(self.request.user, self._get_column().board)
        return kwargs

    def form_valid(self, form):
        column = self._get_column()
        form.instance.column = column
        return super().form_valid(form)

    def get_success_url(self) -> str:
        return reverse('board_detail', kwargs={'pk': self.object.column.board.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['board'] = self._get_column().board
        return context


class CardUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    """
    Handles card editing.
    Permission rule:
      - Members (engineers) may update cards but cannot set status to 'done'.
      - Only the board owner (Jefe) may set status to 'done'.
    """
    model = Card
    form_class = CardForm
    template_name = 'tasks/card_form.html'
    success_message = "Card updated successfully!"

    def get_queryset(self):
        # Members can edit cards on boards they belong to (or own)
        user = self.request.user
        return Card.objects.filter(
            column__board__owner=user
        ) | Card.objects.filter(
            column__board__members=user
        )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        board = self.object.column.board
        kwargs['board'] = board
        kwargs['is_owner'] = is_board_owner(self.request.user, board)
        return kwargs

    def form_valid(self, form):
        board = self.object.column.board
        new_status = form.cleaned_data.get('status')
        # Enforce: only the owner may set a card to 'done'
        if new_status == Card.STATUS_DONE and not is_board_owner(self.request.user, board):
            form.add_error('status', "Only the project owner (Jefe) can mark a task as Done.")
            return self.form_invalid(form)
        return super().form_valid(form)

    def get_success_url(self) -> str:
        return reverse('board_detail', kwargs={'pk': self.object.column.board.pk})

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['board'] = self.object.column.board
        return context


class CardDeleteView(LoginRequiredMixin, DeleteView):
    """Handles the deletion of a card (member or owner)."""
    model = Card
    template_name = 'tasks/confirm_delete.html'
    context_object_name = 'object'

    def get_queryset(self):
        user = self.request.user
        return Card.objects.filter(
            column__board__owner=user
        ) | Card.objects.filter(
            column__board__members=user
        )

    def get_success_url(self) -> str:
        return reverse('board_detail', kwargs={'pk': self.object.column.board.pk})

    def form_valid(self, form) -> HttpResponse:
        messages.success(self.request, "Card deleted successfully!")
        return super().form_valid(form)
