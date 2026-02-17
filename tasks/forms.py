from django import forms
from .models import Board, Column, Card

class BoardForm(forms.ModelForm):
    class Meta:
        model = Board
        fields = ['title', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full p-2 border rounded', 'placeholder': 'Enter board title'}),
            'description': forms.Textarea(attrs={'class': 'w-full p-2 border rounded', 'placeholder': 'Enter description', 'rows': 3}),
        }

class ColumnForm(forms.ModelForm):
    class Meta:
        model = Column
        fields = ['title', 'order']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full p-2 border rounded', 'placeholder': 'Enter column title'}),
            'order': forms.NumberInput(attrs={'class': 'w-full p-2 border rounded'}),
        }

class CardForm(forms.ModelForm):
    class Meta:
        model = Card
        fields = ['title', 'description', 'due_date', 'order']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'w-full p-2 border rounded', 'placeholder': 'Enter card title'}),
            'description': forms.Textarea(attrs={'class': 'w-full p-2 border rounded', 'placeholder': 'Enter description', 'rows': 3}),
            'due_date': forms.DateTimeInput(attrs={'class': 'w-full p-2 border rounded', 'type': 'datetime-local'}),
            'order': forms.NumberInput(attrs={'class': 'w-full p-2 border rounded'}),
        }
