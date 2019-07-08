import re
import json
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from urllib.parse import quote, urlsplit
from urllib.request import urlopen, HTTPError, Request
from .models import ComputedRaceData, Race, RaceResult
import socket
from .constants import WEBDRIVER_VERSION

class Webdriver:

    def __init__(self):
        self.race = None
        self.race_distance = ''
        self.gender = ''
        self.age_group = ''
        ironman_url = 'http://www.ironman.com/events/triathlon-races.aspx?d=ironman'
        half_ironman_url = 'http://www.ironman.com/events/triathlon-races.aspx?d=ironman+70.3'
        self.ironman_html_url = 'http://www.ironman.com/handlers/eventresults.aspx?'
        self.ironman_urls = [{'url': ironman_url, 'distance': 'full-ironman'},
                             {'url': half_ironman_url, 'distance': 'half-ironman'}]

    def run(self):
        for url in self.ironman_urls:
            self.race_distance = url['distance']
            self.get_ironman_urls(url['url'])

    def get_ironman_urls(self, url):
        print('list of all races', url)
        response = self.urlopen_custom(url)
        soup = BeautifulSoup(response, 'lxml')

        event_urls = soup.select('a.eventDetails')
        event_result_urls = [event_url.attrs['href'] for event_url in event_urls]

        for result_url in reversed(event_result_urls):
            self.scrape_race(result_url)

    def scrape_race(self, results_url, validate_url=True):
        print('scraping race: ', results_url)
        if validate_url:
            reg = re.compile('.+\/ironman(?:-70.3)?\/[\w\-\']+\/(.+)')
            extra_data_on_url = reg.findall(results_url)
            if extra_data_on_url:
                results_url = results_url.replace(extra_data_on_url[0], 'results.aspx')
            else:
                results_url = results_url.replace('.aspx', '/results.aspx')

        try:
            response = self.urlopen_custom(results_url)
        except HTTPError:  # no results for this page.
            print("404: ", results_url)
            return
        except socket.timeout:
            print("timeout for: ", results_url)
            return
        soup = BeautifulSoup(response, 'lxml')

        race_years = soup.select('nav.rResultswWrap ul li a')
        if race_years:
            race_links = [r.attrs['href'] for r in race_years]
        else:  # This race has only one year of data, and no side menu
            race_date = soup.select('.moduleContentInner header h1')[0].text.split(' ')[0]
            try:
                race_date = datetime.strptime(race_date, '%m/%d/%Y').strftime('%Y%m%d')
            except ValueError:  # This means the data is really messed up. Ignore.
                print('{0} for the date {1} is weird. Check it.'.format(results_url, race_date))
                return

            race_links = ['{0}?rd={1}'.format(results_url, race_date)]

        self.race_name = soup.select('#eventDetails h3.eventTitle')[0].text.strip()
        self.race_location = soup.select('#eventDetails h4.eventSubtitle')[0].contents[0].strip()

        for race_link in race_links:
            self.scrape_race_year(race_link)

    def scrape_race_year(self, race_link):
        try:
            response = self.urlopen_custom(race_link)
        except socket.timeout:
            print("Failed to load {0}".format(race_link))
            return
        soup = BeautifulSoup(response, 'lxml')

        filter_control = soup.select('#mainContentCol4 .moduleContentInner #filterResultsForm')

        if filter_control:
            age_group_list = [age[0] for age in RaceResult.AGE_GROUPS]
            gender_list = [gender[0] for gender in RaceResult.SEXES]

            race_link = soup.select('.eventResults th.header.name a')[0].attrs['href']

            reg = re.compile('race\=([\w\.\-\']+)&rd=(\d+)')
            race_url_name, race_date = (reg.findall(race_link)[0][0],
                                        reg.findall(race_link)[0][1])

            # Figure out if that data even exists
            table_url = '{0}race={1}&rd={2}'.format(self.ironman_html_url,
                                                    race_url_name, race_date)
            if self.get_table_from_url(table_url) is not None:

                self.race, created = Race.objects.get_or_create(title=self.race_name,
                                                                distance=self.race_distance,
                                                                date=datetime.strptime(
                                                                    race_date, '%Y%m%d').date())
                if created:
                    self.race.location = self.race_location
                    self.race.save()

                if self.race.version == WEBDRIVER_VERSION:
                    print(self.race, 'already scraped and in version', self.race.version)
                else:
                    if not created:
                        # we need to drop all race results
                        deleted_results = RaceResult.objects.filter(race_id = self.race.id).delete()
                        print('Deleted ', deleted_results[0], ' entries')
                    ok = True
                    all_athlete_list = []
                    for gender in gender_list:
                        if not ok:
                            break;
                        for age_group in age_group_list:
                            self.age_group = age_group
                            self.gender = gender
                            data_url = '{0}race={1}&rd={2}&sex={3}&agegroup={4}&ps=2000'.format(
                                self.ironman_html_url, race_url_name, race_date, gender, age_group)
                            athlete_list = self.scrape_gender_and_age_group(data_url)
                            if athlete_list == None:
                                print('athlete list None for', data_url)
                                ok = False
                                break
                            all_athlete_list.extend(athlete_list)
                    if ok:
                        RaceResult.objects.bulk_create(all_athlete_list)
                        ComputedRaceData.objects.bulk_create(self.race.get_computed_race_data())
                        print('Computed for race', self.race, 'results:', len(all_athlete_list))
                        self.race.version = WEBDRIVER_VERSION
                        self.race.save()
                    else:
                        print('Failed for ', self.race)

    def scrape_gender_and_age_group(self, data_url):
        table_body, exc = self.get_table_from_url(data_url)
        if table_body:
            return [self.create_athlete_data(row) for row in table_body.find_all("tr")]
        if not exc:
            return []
        return None

    def get_table_from_url(self, url):
        try:
            response = self.urlopen_custom(url).decode('utf8')  
        except socket.timeout:
            print('timeout for: ', url)
            return None, True
        html = json.loads(response)['body']['update']['html'][0]['value']
        if 'No Results Found' in html:
            return None, False
        soup = BeautifulSoup(html, 'lxml')
        return soup.find('tbody'), False

    def create_athlete_data(self, row):
        keys = ['athlete_name', 'athlete_country', 'division_rank',
                'gender_rank', 'overall_rank', 'swim_time', 'bike_time',
                'run_time', 'finish_time', 'points']

        values = [td.get_text().strip() for td in row.find_all("td")]

        athlete_dict = {k: v for k, v in zip(keys, values)}
        race_status = 'DNS'
        for key, value in athlete_dict.items():
            if value == '---':
                athlete_dict[key] = None
                continue
            if key in ['swim_time', 'bike_time', 'run_time', 'finish_time']:
                if key == 'finish_time':
                    if value == 'DNS' or value == 'DNF' or value == 'DQ':
                        # set the finish time to None, and set the race_status to DNS or DNF
                        athlete_dict[key] = None
                        race_status = value
                    else:
                        race_status = RaceResult.RACE_STATUSES['Finished']
                if athlete_dict[key] is not None:
                    try:
                        help = datetime.strptime(athlete_dict[key], '%H:%M:%S')
                        athlete_dict[key] = timedelta(hours = help.hour, minutes = help.minute, seconds = help.second)
                    except ValueError:  # probably a weird format
                        athlete_dict[key] = None

        return RaceResult(race_id=self.race.id,
                          race_status=race_status,
                          age_group=self.age_group,
                          sex=self.gender,
                          **athlete_dict)
    def urlopen_custom(self, url):
        req = Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        return urlopen(req, timeout = 30).read()
