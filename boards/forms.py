"""
boards/forms.py

Forms for creating and updating Boards, Columns, and Cards.
All form widgets are styled with Bootstrap 5 classes.
"""
from django import forms
from django.contrib.auth.models import User
from .models import Board, Column, Card


class BoardForm(forms.ModelForm):
    """Form for creating and editing a Board (title + description only)."""

    class Meta:
        model  = Board
        fields = ['title', 'description']
        widgets = {
            'title': forms.TextInput(attrs={
                'class':       'form-control',
                'placeholder': 'Enter project title',
            }),
            'description': forms.Textarea(attrs={
                'class':       'form-control',
                'placeholder': 'Enter description',
                'rows':        3,
            }),
        }


class ColumnForm(forms.ModelForm):
    """Form for creating and editing a Column."""

    class Meta:
        model  = Column
        fields = ['title', 'order']
        widgets = {
            'title': forms.TextInput(attrs={
                'class':       'form-control',
                'placeholder': 'Enter column title',
            }),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }


class CardForm(forms.ModelForm):
    """
    Form for creating and editing a Card (engineering task).

    Accepts two extra kwargs from the view:
        board    – used to limit the `assignee` queryset to board participants.
        is_owner – when False (regular engineer), restricts status choices to
                   MEMBER_ALLOWED_STATUSES (cannot reach 'done').
    """

    def __init__(self, *args, **kwargs):
        board: Board = kwargs.pop('board', None)
        is_owner: bool = kwargs.pop('is_owner', True)
        super().__init__(*args, **kwargs)

        # Limit assignee choices to users who are on this board
        if board is not None:
            member_ids = list(board.members.values_list('pk', flat=True))
            member_ids.append(board.owner.pk)
            self.fields['assignee'].queryset = User.objects.filter(pk__in=member_ids)
        else:
            self.fields['assignee'].queryset = User.objects.all()

        # Engineers cannot promote a card to 'done' — restrict their choices
        if not is_owner:
            self.fields['status'].choices = [
                (k, v) for k, v in Card.STATUS_CHOICES
                if k in Card.MEMBER_ALLOWED_STATUSES
            ]

    class Meta:
        model  = Card
        fields = [
            'title', 'description', 'status', 'assignee',
            'discipline', 'progress', 'due_date', 'order',
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class':       'form-control',
                'placeholder': 'Enter task title',
            }),
            'description': forms.Textarea(attrs={
                'class':       'form-control',
                'placeholder': 'Enter description',
                'rows':        3,
            }),
            'status':     forms.Select(attrs={'class': 'form-select'}),
            'assignee':   forms.Select(attrs={'class': 'form-select'}),
            'discipline': forms.Select(attrs={'class': 'form-select'}),
            'progress': forms.NumberInput(attrs={
                'class': 'form-range',
                'type':  'range',
                'min':   0,
                'max':   100,
                'step':  5,
                'id':    'progressRange',
            }),
            'due_date': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type':  'datetime-local',
            }),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
        }
