from django.shortcuts import render, redirect
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login

def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            return redirect('board_list')
    else:
        form = UserCreationForm()
    return render(request, 'registration/register.html', {'form': form})

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from .models import Board, Column, Card
from django import forms

# Board Views
class BoardListView(LoginRequiredMixin, ListView):
    model = Board
    template_name = 'tasks/board_list.html'
    context_object_name = 'boards'

    def get_queryset(self):
        return Board.objects.filter(owner=self.request.user)

class BoardCreateView(LoginRequiredMixin, CreateView):
    model = Board
    fields = ['title', 'description']
    template_name = 'tasks/board_form.html'
    success_url = reverse_lazy('board_list')

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)

class BoardDetailView(LoginRequiredMixin, DetailView):
    model = Board
    template_name = 'tasks/board_detail.html'
    context_object_name = 'board'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Prefetch related columns and cards for performance
        context['columns'] = self.object.columns.prefetch_related('cards').order_by('order')
        return context

# Column Views
class ColumnCreateView(LoginRequiredMixin, CreateView):
    model = Column
    fields = ['title', 'order']
    template_name = 'tasks/column_form.html'

    def form_valid(self, form):
        board = get_object_or_404(Board, pk=self.kwargs['board_id'], owner=self.request.user)
        form.instance.board = board
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('board_detail', kwargs={'pk': self.kwargs['board_id']})

# Card Views
class CardCreateView(LoginRequiredMixin, CreateView):
    model = Card
    fields = ['title', 'description', 'due_date', 'order']
    template_name = 'tasks/card_form.html'

    def form_valid(self, form):
        column = get_object_or_404(Column, pk=self.kwargs['column_id'], board__owner=self.request.user)
        form.instance.column = column
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('board_detail', kwargs={'pk': self.object.column.board.pk})
