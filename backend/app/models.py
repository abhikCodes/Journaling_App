from tortoise import fields, models

class User(models.Model):
    id = fields.IntField(pk=True)
    google_id = fields.CharField(max_length=255, unique=True)
    email = fields.CharField(max_length=255, unique=True)
    name = fields.CharField(max_length=255)
    thread_id = fields.CharField(max_length=255, null=True)
    entry_count = fields.IntField(default=0)  # Counter for total entries
    last_summary_count = fields.IntField(default=0)  # Entries count at last summary

    class Meta:
        table = "users"

class JournalEntry(models.Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="entries")
    date = fields.DateField()
    content = fields.TextField()
    tags = fields.JSONField(default=list)
    sentiment_score = fields.FloatField(null=True)  # Score from -1.0 to 1.0
    emotion_tags = fields.JSONField(default=list)  # List of detected emotions
    
    class Meta:
        table = "journal_entries"

class PeriodicSummary(models.Model):
    id = fields.IntField(pk=True)
    user = fields.ForeignKeyField("models.User", related_name="summaries")
    date_created = fields.DatetimeField(auto_now_add=True)
    start_date = fields.DateField()  # First entry date in summary
    end_date = fields.DateField()  # Last entry date in summary
    content = fields.TextField()  # AI-generated summary content
    entry_count = fields.IntField()  # Number of entries covered
    
    class Meta:
        table = "periodic_summaries"