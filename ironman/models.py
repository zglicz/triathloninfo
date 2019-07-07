from django.db import models
from django.utils.translation import ugettext_lazy as _
from model_utils import Choices
from datetime import datetime, timedelta

class Race(models.Model):
    DISTANCES = Choices(('half-ironman', _('IRONMAN 70.3')),
                        ('full-ironman', _('IRONMAN')))
    distance = models.CharField(choices=DISTANCES, max_length=40)
    title = models.CharField(max_length=255)
    date = models.DateField()
    location = models.CharField(max_length=255)

    def get_computed_race_data(self):
        age_group_list = [age[0] for age in RaceResult.AGE_GROUPS]
        gender_list = [gender[0] for gender in RaceResult.SEXES]
        select_query = {
            'avg_swim': 'AVG(swim_time)',
            'avg_bike': 'AVG(bike_time)',
            'avg_run': 'AVG(run_time)',
            'avg_finish': 'AVG(finish_time)'
        }
        computed_race_data_list = []
        for gender in gender_list:
            for age_group in age_group_list:
                results = self.raceresult_set.filter(
                    age_group=age_group,
                    sex=gender,
                    race_status='Finished').extra(
                    select=select_query).values('avg_swim', 'avg_bike', 'avg_run', 'avg_finish')[0]
                for key, value in results.items():
                    # We don't want to cast `None` as a string, but we want to cast the
                    # `datetime.timedelta` value as a string for saving into the db.
                    if value is not None:
                        results[key] = timedelta(microseconds=value)
                race_data = ComputedRaceData(race=self,
                                             sex=gender,
                                             age_group=age_group,
                                             average_swim_time=results['avg_swim'],
                                             average_bike_time=results['avg_bike'],
                                             average_run_time=results['avg_run'],
                                             average_finish_time=results['avg_finish'])
                computed_race_data_list.append(race_data)
        return computed_race_data_list

    def __str__(self):
            return '{0} {1}'.format(self.title, self.date.year)

    class Meta:
        unique_together = ('distance', 'title', 'date',)


class RaceResult(models.Model):
    AGE_GROUPS = Choices('Pro', '18-24', '25-29', '30-34', '35-39',
                         '40-44', '45-49', '50-54', '55-59', '60-64',
                         '65-69', '70-74', '75-79', '80-999')
    SEXES = Choices('M', 'F')
    RACE_STATUSES = Choices('DQ', 'DNS', 'DNF', 'Finished')
    race = models.ForeignKey(Race, on_delete=models.CASCADE)
    athlete_name = models.CharField(max_length=255)
    age_group = models.CharField(max_length=255, choices=AGE_GROUPS)
    sex = models.CharField(max_length=1, choices=SEXES)
    athlete_country = models.CharField(max_length=255, blank=True, null=True)
    division_rank = models.IntegerField(blank=True, null=True,)
    gender_rank = models.IntegerField(blank=True, null=True,)
    overall_rank = models.IntegerField(blank=True, null=True,)
    swim_time = models.DurationField(blank=True, null=True,)
    bike_time = models.DurationField(blank=True, null=True,)
    run_time = models.DurationField(blank=True, null=True,)
    finish_time = models.DurationField(blank=True, null=True,)
    points = models.IntegerField(blank=True, null=True,)
    race_status = models.CharField(choices=RACE_STATUSES,
                                   default=RACE_STATUSES['Finished'], max_length=40)

    def finish_time_as_string(self):
        return self.finish_time.strftime('%H:%M:%S') if self.finish_time else '---'
    finish_time_as_string.short_description = "finish time"

    str_finish_time = property(finish_time_as_string)

    def __str__(self):
            return '{0} - {1}'.format(self.athlete_name, self.finish_time)


class ComputedRaceData(models.Model):
    race = models.ForeignKey('Race', on_delete=models.CASCADE)
    age_group = models.CharField(max_length=255, choices=RaceResult.AGE_GROUPS)
    sex = models.CharField(max_length=1, choices=RaceResult.SEXES)
    average_swim_time = models.DurationField(blank=True, null=True,)
    average_bike_time = models.DurationField(blank=True, null=True,)
    average_run_time = models.DurationField(blank=True, null=True,)
    average_finish_time = models.DurationField(blank=True, null=True,)
