from django import forms
from .models import Race, RaceResult

class RaceFilterForm(forms.Form):
	race_id = forms.ModelChoiceField(queryset=Race.objects.none(), widget=forms.Select(attrs={"onChange": 'submit()'}))

	age_group = forms.ChoiceField(
		choices=RaceResult.AGE_GROUPS,
		widget=forms.Select(attrs={'onchange': 'submit();'}))
	sex = forms.ChoiceField(
		choices=RaceResult.SEXES,
		widget=forms.Select(attrs={'onchange': 'submit();'}))

	def __init__(self, race, *args, **kwargs):
		super(RaceFilterForm, self).__init__(*args, **kwargs)
		self.fields['race_id'].queryset = Race.objects.filter(title=race.title)