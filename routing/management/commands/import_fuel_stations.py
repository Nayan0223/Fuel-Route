import csv

from django.conf import settings
from django.core.management.base import BaseCommand

from routing.models import FuelStation
from routing.services.geo import city_state_to_coords


class Command(BaseCommand):
    help = "Import fuel stations from the assessment CSV and attach city coordinates."

    def handle(self, *args, **options):
        csv_path = settings.FUEL_PRICES_CSV
        FuelStation.objects.all().delete()

        created = 0
        geocoded = 0
        missing = 0

        with csv_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                city = row["City"].strip()
                state = row["State"].strip().upper()
                coords = city_state_to_coords(city, state)
                latitude = longitude = None
                if coords:
                    latitude, longitude = coords
                    geocoded += 1
                else:
                    missing += 1

                FuelStation.objects.create(
                    opis_id=int(row["OPIS Truckstop ID"]),
                    name=row["Truckstop Name"].strip(),
                    address=row["Address"].strip(),
                    city=city,
                    state=state,
                    rack_id=int(row["Rack ID"]),
                    retail_price=float(row["Retail Price"]),
                    latitude=latitude,
                    longitude=longitude,
                )
                created += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Imported {created} stations ({geocoded} geocoded, {missing} missing coordinates)."
            )
        )
