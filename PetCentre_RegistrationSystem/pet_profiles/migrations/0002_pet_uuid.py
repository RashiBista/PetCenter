import uuid

from django.db import migrations, models


def populate_uuids(apps, schema_editor):
    # AddField with a default evaluates that default ONCE for the whole
    # ALTER TABLE, stamping every existing row with the SAME uuid — the
    # unique constraint added afterward would then reject the duplicates.
    # Adding the column nullable first and looping here gives each row
    # its own value instead (same fix as chat.0002_chatroom_uuid).
    Pet = apps.get_model("pet_profiles", "Pet")
    for pet in Pet.objects.filter(uuid__isnull=True):
        pet.uuid = uuid.uuid4()
        pet.save(update_fields=["uuid"])


class Migration(migrations.Migration):

    dependencies = [
        ("pet_profiles", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="pet",
            name="uuid",
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.RunPython(populate_uuids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="pet",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
