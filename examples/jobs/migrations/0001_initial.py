from django.db import migrations
from django.db import models


class Migration(migrations.Migration):
    initial = True
    dependencies: list = []

    operations = [
        migrations.CreateModel(
            name="Job",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("name", models.CharField(max_length=255)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("status", models.CharField(default="idle", max_length=32)),
            ],
        ),
    ]
