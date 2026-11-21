from django.core.management.base import BaseCommand
from reconcile.importer import import_all
from reconcile.models import Location, SystemARecord, SystemBEntry


class Command(BaseCommand):
    help = "Import CSV data for Locations, System A records, and System B entries."

    def add_arguments(self, parser):
        parser.add_argument(
            "--data-dir",
            type=str,
            default=None,
            help="Directory containing locations.csv, system_a.csv, system_b.csv",
        )

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Starting data import..."))
        stats = import_all(options.get("data_dir"))

        loc = stats["locations"]
        a = stats["system_a"]
        b = stats["system_b"]

        self.stdout.write(
            self.style.SUCCESS(
                f"Locations: {loc['read']} read, {loc['saved']} saved (DB total: {Location.objects.count()})"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"System A: {a['read']} read, {a['saved']} saved; empty actors: {a['empty_actors']} (DB total: {SystemARecord.objects.count()})"
            )
        )
        self.stdout.write(
            self.style.SUCCESS(
                f"System B: {b['read']} read, {b['saved']} saved; refs cleaned: {b['cleaned_refs']}; empty values: {b['empty_values']} (DB total: {SystemBEntry.objects.count()})"
            )
        )
