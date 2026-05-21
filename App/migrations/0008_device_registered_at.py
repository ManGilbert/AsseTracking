from django.db import migrations, models
from django.utils import timezone


class Migration(migrations.Migration):

    dependencies = [
        ("App", "0007_seed_default_departments"),
    ]

    operations = [
        migrations.AddField(
            model_name="device",
            name="registered_at",
            field=models.DateTimeField(auto_now_add=True, default=timezone.now),
            preserve_default=False,
        ),
    ]
