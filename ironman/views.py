from django.http import HttpResponse
from django.shortcuts import render, get_object_or_404, redirect
from .models import Race, RaceResult
from .forms import RaceFilterForm
from django.db.models import Q
from django.views import generic
from django.utils.http import urlencode
from django.urls import reverse



class IndexView(generic.TemplateView):
	template_name = 'races/index.html'
	
	def get_context_data(self, *args, **kwargs):
		context = super(IndexView, self).get_context_data(**kwargs)
		q = self.request.GET.get('q')
		search_type = self.request.GET.get('search_type', 'race')
		if search_type == 'race':
			races = Race.objects \
				.filter(Q(title__contains=q) if q else Q()) \
				.order_by('-date')
			context['races'] = races
		else:
			race_results = RaceResult.objects \
				.filter(Q(athlete_name__contains=q) if q else Q()) \
				.order_by('-race__date') \
				[:50]
			context['race_results'] = race_results
		context['q'] = q
		context['search_type'] = search_type
		return context

class RaceView(generic.TemplateView):
	template_name = 'races/results.html'

	def dispatch(self, request, *args, **kwargs):
		race_id = request.GET.get('race_id')
		race = get_object_or_404(Race, pk=kwargs['race_id'])
		if race_id and str(race.id) != str(race_id):
			path = reverse('ironman:race', kwargs={'race_id': race_id})
			helper_query_dict = request.GET.copy()
			helper_query_dict.pop('race_id')
			params = helper_query_dict.urlencode()
			return redirect("%s?%s" % (path, params));
		return super(RaceView, self).dispatch(request, *args, **kwargs)

	def get_context_data(self, *args, **kwargs):
		context = super().get_context_data(**kwargs)
		race_id = kwargs['race_id']
		age_group = self.request.GET.get('age_group')
		sex = self.request.GET.get('sex')		
		race = get_object_or_404(Race, pk=race_id)
		filter_obj = Q(race_id=race.id) & Q(finish_time__isnull=False)
		if age_group:
			filter_obj &= Q(age_group=age_group)
		if sex:
			filter_obj &= Q(sex=sex)
		race_results = RaceResult \
			.objects \
			.filter(filter_obj) \
			.order_by('finish_time')
		races_all_years = Race.objects.filter(title=race.title)
		context['race_results'] = race_results
		context['race'] = race
		context['race_filter_form'] = RaceFilterForm(race, initial={'age_group': age_group, 'sex': sex, 'race_id': race.pk})
		return context
