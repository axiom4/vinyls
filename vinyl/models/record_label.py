from django.db import models


class RecordLabel(models.Model):
    name = models.CharField(max_length=200)
    website = models.URLField(blank=True, null=True)

    def __str__(self):
        return self.name
