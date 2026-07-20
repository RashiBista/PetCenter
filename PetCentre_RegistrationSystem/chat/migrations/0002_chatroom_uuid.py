import uuid

from django.db import migrations, models


def populate_uuids(apps, schema_editor):
    # AddField's default would hand every existing row the SAME uuid (the
    # default callable is evaluated once for the whole ALTER), which the
    # unique constraint below would then reject — so assign one per row.
    ChatRoom = apps.get_model("chat", "ChatRoom")
    for room in ChatRoom.objects.filter(uuid__isnull=True):
        room.uuid = uuid.uuid4()
        room.save(update_fields=["uuid"])


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="chatroom",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, editable=False, null=True),
        ),
        migrations.RunPython(populate_uuids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="chatroom",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
