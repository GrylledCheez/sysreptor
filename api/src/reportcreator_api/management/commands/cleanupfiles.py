from django.core.management.base import BaseCommand
from django.db import transaction
from reportcreator_api.pentests.models import UploadedAsset, UploadedImage


class Command(BaseCommand):
    help = 'Clean up file entries from the DB where the files do not exist on the fielsystem.'

    def file_exists(self, f):
        try:
            with f.open():
                return True
        except Exception:
            return False

    @transaction.atomic
    def handle(self, *args, **options):
        UploadedAsset.objects \
            .filter(pk__in=[o.pk for o in UploadedAsset.objects.iterator() if not self.file_exists(o.file)]) \
            .delete()
        UploadedImage.objects \
            .filter(pk__in=[o.pk for o in UploadedImage.objects.iterator() if not self.file_exists(o.file)]) \
            .delete()