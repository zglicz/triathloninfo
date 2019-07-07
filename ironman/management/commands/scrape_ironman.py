from django.core.management.base import BaseCommand
from ironman.webdriver import Webdriver


class Command(BaseCommand):
    help = 'Scrapes ironman.com for all the data. All of it.'

    def add_arguments(self, parser):
            parser.add_argument('--race_url', nargs='+', type=str, default=False)

    def handle(self, *args, **options):
        webdriver = Webdriver()
        race_url = options.get('race_url', None)
        if race_url:
            webdriver.scrape_race(race_url[0], validate_url=False)
        else:
            webdriver.run()
