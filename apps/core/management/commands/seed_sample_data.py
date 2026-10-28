"""Load clearly fake sample data, so the pages can be built and tried without real content.

    python manage.py seed_sample_data           load it (safe to repeat)
    python manage.py seed_sample_data --clear   remove it again

Everything this command creates has a name that starts with "[نمونه]" (sample),
so it cannot be mistaken for real content, and so `--clear` can find exactly
those rows and leave everything else alone. The dosages, companies and
customers are made up: in a pharmacy, invented dosage text that looks real
would be dangerous on a live site. For that reason the command refuses to run
unless DEBUG is on, which is never the case in production (config/settings/prod.py).

No photos are created. Product, expert and article photos are optional, so the
pages have to cope without them anyway.

This is a development tool, so it imports every app. That is fine for a
command; it is not a pattern for the rest of `core`.
"""
import datetime

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import ProtectedError
from django.utils import timezone

from apps.core.text import normalize_text

SAMPLE = "[نمونه]"


def sample(text: str) -> str:
    return normalize_text(f"{SAMPLE} {text}")


PRODUCT_TYPES = ["قارچ‌کش", "حشره‌کش", "علف‌کش"]

# name, other names (one per line)
CROPS = [
    ("گندم", "wheat"),
    ("کلزا", "rapeseed\ncanola"),
    ("آلو", "plum"),
    ("مرکبات", ""),
]
PESTS = [
    ("سن", "sunn pest"),
    ("زنگ زرد", ""),
    ("ساقه‌خوار", "ساقه خوار"),
    ("علف هرز پهن‌برگ", ""),
]

# trade name, type, generic name, available, has dates, crops, pests
# The generic names are invented on purpose: no real active ingredient is used.
PRODUCTS = [
    ("محصول ۱", "قارچ‌کش", "ماده مؤثره آزمایشی ۱", True, True, ["گندم"], ["زنگ زرد"]),
    ("محصول ۲", "قارچ‌کش", "ماده مؤثره آزمایشی ۲", True, True, ["گندم", "کلزا"], ["زنگ زرد"]),
    ("محصول ۳", "قارچ‌کش", "ماده مؤثره آزمایشی ۳", False, True, ["آلو"], []),
    ("محصول ۴", "قارچ‌کش", "ماده مؤثره آزمایشی ۴", True, False, [], []),
    ("محصول ۵", "حشره‌کش", "ماده مؤثره آزمایشی ۵", True, True, ["گندم"], ["سن"]),
    ("محصول ۶", "حشره‌کش", "ماده مؤثره آزمایشی ۶", True, True, ["کلزا", "مرکبات"], ["ساقه‌خوار"]),
    ("محصول ۷", "حشره‌کش", "ماده مؤثره آزمایشی ۷", False, False, ["مرکبات"], ["سن"]),
    ("محصول ۸", "حشره‌کش", "ماده مؤثره آزمایشی ۸", True, True, [], ["ساقه‌خوار"]),
    ("محصول ۹", "علف‌کش", "ماده مؤثره آزمایشی ۹", True, True, ["گندم"], ["علف هرز پهن‌برگ"]),
    ("محصول ۱۰", "علف‌کش", "ماده مؤثره آزمایشی ۱۰", True, False, ["کلزا"], ["علف هرز پهن‌برگ"]),
    ("محصول ۱۱", "علف‌کش", "ماده مؤثره آزمایشی ۱۱", False, True, [], []),
    ("محصول ۱۲", "علف‌کش", "ماده مؤثره آزمایشی ۱۲", True, True, ["گندم", "کلزا", "آلو"], ["علف هرز پهن‌برگ"]),
]

# name, degree, role, experience, specialty. The first has the shape of
# Rahmatollah's profile, the second of Habibollah's (no role, no experience).
EXPERTS = [
    ("کارشناس ۱", "مدرک آزمایشی ۱", "سمت آزمایشی", "سابقه آزمایشی", ""),
    ("کارشناس ۲", "مدرک آزمایشی ۲", "", "", "تخصص آزمایشی"),
]

FAQS = [
    ("پرسش آزمایشی ۱؟", "پاسخ آزمایشی ۱."),
    ("پرسش آزمایشی ۲؟", "پاسخ آزمایشی ۲.\n\nبند دوم پاسخ آزمایشی."),
    ("پرسش آزمایشی ۳؟", "پاسخ آزمایشی ۳."),
]

# title, season, published
ARTICLES = [
    ("مقاله بهاره", "spring", True),
    ("مقاله تابستانه", "summer", True),
    ("مقاله پاییزه", "autumn", True),
    ("مقاله زمستانه (پیش‌نویس)", "winter", False),
]
ARTICLE_BODY = "بند اول متن آزمایشی.\n\nبند دوم متن آزمایشی.\n\nبند سوم متن آزمایشی."

# name, kind, status, crop. The numbers are valid mobile numbers that belong to nobody we know.
REQUESTS = [
    ("مشتری ۱", "question", "new", "گندم", "09000000001"),
    ("مشتری ۲", "question", "handled", "", "09000000002"),
    ("مشتری ۳", "farm_visit", "new", "کلزا", "09000000003"),
    ("مشتری ۴", "farm_visit", "handled", "", "09000000004"),
]


class Command(BaseCommand):
    help = "Load clearly fake sample data (development only), or remove it with --clear."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help=f"Delete the sample rows (those whose name starts with {SAMPLE}) instead of loading them.",
        )

    def handle(self, *args, **options):
        if not settings.DEBUG:
            raise CommandError(
                "seed_sample_data only runs with DEBUG on (local development). "
                "It is refused here so fake data cannot reach a real site."
            )
        with transaction.atomic():
            if options["clear"]:
                counts = self._clear()
                verb = "Removed"
            else:
                counts = self._load()
                verb = "Loaded"
        for label, number in counts.items():
            self.stdout.write(f"{verb} {number} {label}")

    # ------------------------------------------------------------------ load

    def _load(self) -> dict:
        from apps.articles.models import Article
        from apps.catalog.models import Crop, Pest, Product, ProductType
        from apps.consultations.models import ConsultationRequest
        from apps.pages.models import Expert, FaqItem

        today = timezone.localdate()

        types = {}
        for order, name in enumerate(PRODUCT_TYPES):
            types[name], _ = ProductType.objects.get_or_create(
                name=sample(name), defaults={"order": order}
            )
        crops = {}
        for name, alternates in CROPS:
            crops[name], _ = Crop.objects.get_or_create(
                name=sample(name), defaults={"alternate_names": alternates}
            )
        pests = {}
        for name, alternates in PESTS:
            pests[name], _ = Pest.objects.get_or_create(
                name=sample(name), defaults={"alternate_names": alternates}
            )

        for name, type_name, generic, available, has_dates, crop_names, pest_names in PRODUCTS:
            dates = {}
            if has_dates:
                dates = {
                    "production_date": today - datetime.timedelta(days=90),
                    "expiry_date": today + datetime.timedelta(days=730),
                }
            product, _ = Product.objects.update_or_create(
                trade_name=sample(name),
                defaults={
                    "generic_name": generic,
                    "product_type": types[type_name],
                    "usage": "موارد مصرف آزمایشی.\nخط دوم آزمایشی.",
                    "dosage": "میزان مصرف آزمایشی",
                    "timing": "زمان مصرف آزمایشی",
                    "manufacturer": sample("شرکت تولیدکننده"),
                    "importer": sample("شرکت واردکننده"),
                    "country_of_origin": "کشور آزمایشی",
                    "is_available": available,
                    "production_date": dates.get("production_date"),
                    "expiry_date": dates.get("expiry_date"),
                },
            )
            product.crops.set([crops[c] for c in crop_names])
            product.pests.set([pests[p] for p in pest_names])

        for order, (name, degree, role, experience, specialty) in enumerate(EXPERTS):
            Expert.objects.update_or_create(
                name=sample(name),
                defaults={
                    "degree": degree,
                    "role": role,
                    "experience": experience,
                    "specialty": specialty,
                    "order": order,
                },
            )

        for order, (question, answer) in enumerate(FAQS):
            FaqItem.objects.update_or_create(
                question=sample(question), defaults={"answer": answer, "order": order}
            )

        for number, (title, season, published) in enumerate(ARTICLES):
            Article.objects.update_or_create(
                title=sample(title),
                defaults={
                    "season": season,
                    "body": ARTICLE_BODY,
                    "is_published": published,
                    "published_date": today - datetime.timedelta(days=30 * number) if published else None,
                },
            )

        for name, kind, status, crop_name, phone in REQUESTS:
            defaults = {
                "phone": phone,
                "status": status,
                "crop": crops.get(crop_name),
            }
            if kind == "question":
                defaults["message"] = "پرسش آزمایشی.\nخط دوم پرسش."
            else:
                defaults["village_or_address"] = "روستای آزمایشی"
            ConsultationRequest.objects.update_or_create(
                name=sample(name), kind=kind, defaults=defaults
            )

        return {
            "product types": len(PRODUCT_TYPES),
            "crops": len(CROPS),
            "pests": len(PESTS),
            "products": len(PRODUCTS),
            "experts": len(EXPERTS),
            "FAQ items": len(FAQS),
            "articles": len(ARTICLES),
            "consultation requests": len(REQUESTS),
        }

    # ----------------------------------------------------------------- clear

    def _clear(self) -> dict:
        from apps.articles.models import Article
        from apps.catalog.models import Crop, Pest, Product, ProductType
        from apps.consultations.models import ConsultationRequest
        from apps.pages.models import Expert, FaqItem

        # Products before their types: a type in use cannot be deleted (PROTECT).
        plan = [
            ("consultation requests", ConsultationRequest.objects.filter(name__startswith=SAMPLE)),
            ("products", Product.objects.filter(trade_name__startswith=SAMPLE)),
            ("articles", Article.objects.filter(title__startswith=SAMPLE)),
            ("FAQ items", FaqItem.objects.filter(question__startswith=SAMPLE)),
            ("experts", Expert.objects.filter(name__startswith=SAMPLE)),
            ("crops", Crop.objects.filter(name__startswith=SAMPLE)),
            ("pests", Pest.objects.filter(name__startswith=SAMPLE)),
            ("product types", ProductType.objects.filter(name__startswith=SAMPLE)),
        ]
        counts = {}
        for label, queryset in plan:
            counts[label] = queryset.count()
            try:
                queryset.delete()
            except ProtectedError:
                raise CommandError(
                    f"Cannot remove the sample {label}: a real row still uses them. "
                    "Nothing was removed."
                ) from None
        return counts
