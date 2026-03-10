"""
teams/forms.py

MembershipForm: used by the Add Member UI to collect both the target
user and their mandatory specialty_role in a single form submission.
"""
from django import forms
from django.contrib.auth.models import User
from .models import BoardMembership


class MembershipForm(forms.Form):
    """
    Form to add a new engineer to a board.

    Fields:
        user           – searchable dropdown of eligible users (those not
                         already the owner or a current member of the board).
        specialty_role – required selection of the engineer's discipline role.

    Accepts an optional `board` kwarg in __init__ so the user queryset can
    be filtered appropriately.
    """

    user = forms.ModelChoiceField(
        queryset=User.objects.none(),
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id':    'id_user',
        }),
        label='Engineer',
        empty_label='— Select an engineer —',
    )

    specialty_role = forms.ChoiceField(
        choices=[('', '— Select a role —')] + BoardMembership.ROLE_CHOICES,
        widget=forms.Select(attrs={
            'class': 'form-select',
            'id':    'id_specialty_role',
        }),
        label='Specialty Role',
    )

    def __init__(self, *args, **kwargs):
        board = kwargs.pop('board', None)
        super().__init__(*args, **kwargs)

        if board is not None:
            # Show only users that can actually be invited
            excluded_ids = list(board.members.values_list('pk', flat=True))
            excluded_ids.append(board.owner.pk)
            self.fields['user'].queryset = User.objects.exclude(
                pk__in=excluded_ids
            ).order_by('username')
        else:
            self.fields['user'].queryset = User.objects.order_by('username')

    def clean_specialty_role(self):
        """Validate that a non-empty role was selected."""
        role = self.cleaned_data.get('specialty_role')
        if not role:
            raise forms.ValidationError('Please select a specialty role.')
        return role
