from django.db import migrations

import apps.core.fields


class Migration(migrations.Migration):

    dependencies = [
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="sitesettings",
            name="map_image",
            field=apps.core.fields.WebPImageField(
                blank=True,
                help_text="تصویر اسکرین‌شات نقشه با پین فروشگاه در مرکز (حداکثر ۶۰ کیلوبایت).",
                max_bytes=60000,
                max_side=800,
                quality=80,
                thumb_side=None,
                upload_to="map/",
                verbose_name="تصویر نقشه",
            ),
        ),
    ]