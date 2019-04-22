from django.core.management.base import BaseCommand, CommandError
from django.conf import settings
from django.contrib.staticfiles.finders import find
from django.templatetags.static import static

class Command(BaseCommand):
    help = 'Display path to "static/" directory.'

    def handle(self, *args, **options):
        print(get_static('.'))


def get_static(path):
    if settings.DEBUG:
        return find(path)
    else:
        return static(path)