import uuid

from django.db import migrations, models


def populate_uuids(apps, schema_editor):
    ChatRoom = apps.get_model("chat", "ChatRoom")
    for room in ChatRoom.objects.filter(uuid__isnull=True):
        room.uuid = uuid.uuid4()
        room.save(update_fields=["uuid"])


class Migration(migrations.Migration):

    dependencies = [
        ("chat", "0001_initial"),
    ]

    operations = [
        # IMPORTANT: added with NO default — a default here is evaluated
        # once for the whole ALTER TABLE, stamping every existing row with
        # the SAME uuid, which the unique index below then rejects. Adding
        # it nullable leaves existing rows NULL so the data step can give
        # each row its own value.
        migrations.AddField(
            model_name="chatroom",
            name="uuid",
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.RunPython(populate_uuids, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="chatroom",
            name="uuid",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
    ]
