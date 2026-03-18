"""
teams/views.py

Views for team (member) management:
  - BoardMembersView  → list + add + remove members with specialty_role.
  - BoardFinishView   → owner marks a board as 'finished' (triggers analytics signal).
"""
from django.http import HttpRequest, HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied
from django.views.generic import View
from django.db import transaction

from boards.models import Board
from boards.views import get_board_owner_or_403, get_board_or_403
from .models import BoardMembership
from .forms import MembershipForm


class BoardMembersView(LoginRequiredMixin, View):
    """
    GET:  Renders the team management page showing current members and the
          Add Member form (user dropdown + specialty_role select).
    POST: Handles two actions via the 'action' POST field:
            'remove' → removes a member (deletes BoardMembership row).
            (default) → validates and creates a new BoardMembership.
    Only the board owner (Jefe) may access this view.
    """
    template_name = 'teams/board_members.html'

    def _get_board(self, pk: int) -> Board:
        return get_board_owner_or_403(pk, self.request.user)

    def get(self, request: HttpRequest, pk: int) -> HttpResponse:
        board = self._get_board(pk)
        form  = MembershipForm(board=board)
        return render(request, self.template_name, {
            'board': board,
            'form':  form,
        })

    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        board  = self._get_board(pk)
        action = request.POST.get('action')

        if action == 'remove':
            # Handle removal of existing members via POST 'action=remove'
            member_id = request.POST.get('member_id')
            try:
                # Use User ID and Board instance to find the explicit through-table row
                membership = BoardMembership.objects.get(board=board, user_id=member_id)
                username   = membership.user.username
                membership.delete()
                messages.success(request, f'{username} removed from the board.')
            except BoardMembership.DoesNotExist:
                messages.error(request, 'Member not found.')
            return redirect('board_members', pk=pk)

        # --- Add member ---
        form = MembershipForm(request.POST, board=board)
        if form.is_valid():
            user_to_add    = form.cleaned_data['user']
            specialty_role = form.cleaned_data['specialty_role']
            BoardMembership.objects.create(
                board          = board,
                user           = user_to_add,
                specialty_role = specialty_role,
            )
            messages.success(
                request,
                f'{user_to_add.username} added as '
                f'{dict(BoardMembership.ROLE_CHOICES).get(specialty_role, specialty_role)}.',
            )
            return redirect('board_members', pk=pk)

        # Re-render with form errors
        return render(request, self.template_name, {'board': board, 'form': form})


class BoardFinishView(LoginRequiredMixin, View):
    """
    POST: Marks a board as 'finished'.
    The post_save signal in boards/signals.py generates BoardAnalytics.
    Only the board owner may call this endpoint.
    """
    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        board = get_board_owner_or_403(pk, request.user)
        if board.status == Board.STATUS_FINISHED:
            messages.warning(request, 'This board is already finished.')
        else:
            # Change status to 'finished' which is the trigger for analytics generation
            board.status = Board.STATUS_FINISHED
            # The Board.save() call sends a post_save signal processed in boards/signals.py
            board.save()
            messages.success(
                request,
                f"Project '{board.title}' has been closed. Analytics saved.",
            )
        return redirect('board_analytics', pk=pk)


class BoardTransferLeadershipView(LoginRequiredMixin, View):
    """
    POST: Transfers board ownership (Líder) to an existing member.
    The current leader takes the member's previous specialty_role.
    Only the board owner may call this endpoint.
    """
    def post(self, request: HttpRequest, pk: int) -> HttpResponse:
        board = get_board_owner_or_403(pk, request.user)
        
        if board.memberships.count() == 0:
            messages.error(request, 'Cannot transfer leadership: the project has no other members.')
            return redirect('board_detail', pk=pk)
            
        new_leader_id = request.POST.get('new_leader_id')
        if not new_leader_id:
            messages.error(request, 'No new leader selected.')
            return redirect('board_detail', pk=pk)

        try:
            new_leader_membership = board.memberships.get(user_id=new_leader_id)
        except BoardMembership.DoesNotExist:
            messages.error(request, 'Selected user is not a member of this project.')
            return redirect('board_detail', pk=pk)

        old_owner = board.owner
        new_owner = new_leader_membership.user
        
        with transaction.atomic():
            # 1. Old owner takes the membership (and role) of the new leader
            new_leader_membership.user = old_owner
            new_leader_membership.save()
            
            # 2. New leader becomes the board owner
            board.owner = new_owner
            board.save()
            
        messages.success(
            request, 
            f'Leadership successfully transferred to {new_owner.get_full_name() or new_owner.username}. You are now a project member.'
        )
        return redirect('board_detail', pk=pk)
