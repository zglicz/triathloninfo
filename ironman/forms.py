from django import forms
from .models import Race, RaceResult

class RaceFilterForm(forms.Form):
	race_id = forms.ModelChoiceField(
		queryset=Race.objects.none(),
		widget=forms.Select(attrs={"onChange": 'submit()', 'class': 'form-control'}),
		label='',
		empty_label=None)

	age_group = forms.ChoiceField(
		choices=[(None, 'All')] + RaceResult.AGE_GROUPS,
		widget=forms.Select(attrs={'onchange': 'submit();', 'class': 'form-control'}),
		label='')
	sex = forms.ChoiceField(
		choices=[(None, 'Both')] + RaceResult.SEXES,
		widget=forms.Select(attrs={'onchange': 'submit();', 'class': 'form-control'}),
		label='')

	def __init__(self, race, *args, **kwargs):
		super(RaceFilterForm, self).__init__(*args, **kwargs)
		self.fields['race_id'].queryset = Race.objects.filter(title=race.title)