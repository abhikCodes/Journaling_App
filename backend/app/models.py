from tortoise import fields, models

class User(models.Model):
    id = fields.IntField(pk=True)
    google_id = fields.CharField(max_length=255, unique=True)
    email = fields.CharField(max_length=255, unique=True)
    name = fields.CharField(max_length=255)
    thread_id = fields.CharField(max_length=255, null=True)

    class Meta:
        table = "users"

class JournalEntry(models.Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="entries")
    date = fields.DateField()
    content = fields.TextField()
    tags = fields.JSONField(default=list)

    class Meta:
        table = "journal_entries"