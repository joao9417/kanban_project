from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy, reverse
from django.contrib.messages.views import SuccessMessageMixin
from django.contrib import messages
from .models import Board, Column, Card
from .forms import BoardForm, ColumnForm, CardForm

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

# Board Views
class BoardListView(LoginRequiredMixin, ListView):
    model = Board
    template_name = 'tasks/board_list.html'
    context_object_name = 'boards'

    def get_queryset(self):
        return Board.objects.filter(owner=self.request.user)

class BoardCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Board
    form_class = BoardForm
    template_name = 'tasks/board_form.html'
    success_url = reverse_lazy('board_list')
    success_message = "Board created successfully!"

    def form_valid(self, form):
        form.instance.owner = self.request.user
        return super().form_valid(form)

class BoardUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Board
    form_class = BoardForm
    template_name = 'tasks/board_form.html'
    success_message = "Board updated successfully!"

    def get_queryset(self):
        return Board.objects.filter(owner=self.request.user)
    
    def get_success_url(self):
         return reverse('board_list')

class BoardDeleteView(LoginRequiredMixin, DeleteView):
    model = Board
    template_name = 'tasks/confirm_delete.html'
    success_url = reverse_lazy('board_list')
    context_object_name = 'object'

    def get_queryset(self):
        return Board.objects.filter(owner=self.request.user)
    
    def form_valid(self, form):
        messages.success(self.request, "Board deleted successfully!")
        return super().form_valid(form)

class BoardDetailView(LoginRequiredMixin, DetailView):
    model = Board
    template_name = 'tasks/board_detail.html'
    context_object_name = 'board'

    def get_queryset(self):
        return Board.objects.filter(owner=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        # Prefetch related columns and cards for performance
        context['columns'] = self.object.columns.prefetch_related('cards').order_by('order')
        return context

# Column Views
class ColumnCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Column
    form_class = ColumnForm
    template_name = 'tasks/column_form.html'
    success_message = "Column created successfully!"

    def form_valid(self, form):
        board = get_object_or_404(Board, pk=self.kwargs['board_id'], owner=self.request.user)
        form.instance.board = board
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('board_detail', kwargs={'pk': self.kwargs['board_id']})

class ColumnUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Column
    form_class = ColumnForm
    template_name = 'tasks/column_form.html'
    success_message = "Column updated successfully!"

    def get_queryset(self):
        return Column.objects.filter(board__owner=self.request.user)

    def get_success_url(self):
        return reverse('board_detail', kwargs={'pk': self.object.board.pk})

class ColumnDeleteView(LoginRequiredMixin, DeleteView):
    model = Column
    template_name = 'tasks/confirm_delete.html'
    context_object_name = 'object'

    def get_queryset(self):
        return Column.objects.filter(board__owner=self.request.user)

    def get_success_url(self):
        return reverse('board_detail', kwargs={'pk': self.object.board.pk})
        
    def form_valid(self, form):
        messages.success(self.request, "Column deleted successfully!")
        return super().form_valid(form)


# Card Views
class CardCreateView(LoginRequiredMixin, SuccessMessageMixin, CreateView):
    model = Card
    form_class = CardForm
    template_name = 'tasks/card_form.html'
    success_message = "Card created successfully!"

    def form_valid(self, form):
        column = get_object_or_404(Column, pk=self.kwargs['column_id'], board__owner=self.request.user)
        form.instance.column = column
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('board_detail', kwargs={'pk': self.object.column.board.pk})

class CardUpdateView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    model = Card
    form_class = CardForm
    template_name = 'tasks/card_form.html'
    success_message = "Card updated successfully!"

    def get_queryset(self):
        return Card.objects.filter(column__board__owner=self.request.user)

    def get_success_url(self):
        return reverse('board_detail', kwargs={'pk': self.object.column.board.pk})

class CardDeleteView(LoginRequiredMixin, DeleteView):
    model = Card
    template_name = 'tasks/confirm_delete.html'
    context_object_name = 'object'

    def get_queryset(self):
        return Card.objects.filter(column__board__owner=self.request.user)

    def get_success_url(self):
        return reverse('board_detail', kwargs={'pk': self.object.column.board.pk})
        
    def form_valid(self, form):
        messages.success(self.request, "Card deleted successfully!")
        return super().form_valid(form)

