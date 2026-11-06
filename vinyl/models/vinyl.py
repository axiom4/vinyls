import uuid

from django.db import models
from django.urls import reverse

from .artist import Artist
from .genre import VinylGenre
from .record_label import RecordLabel


class Vinyl(models.Model):
    SIZE_CHOICES = [
        ('12', '12"'),
        ('10', '10"'),
        ('7', '7"'),
    ]

    SPEED_CHOICES = [
        ('33', '33 giri'),
        ('45', '45 giri'),
        ('78', '78 giri'),
    ]

    CONDITION_CHOICES = [
        ('M', 'Mint'),
        ('NM', 'Near Mint'),
        ('VG+', 'Very Good Plus'),
        ('VG', 'Very Good'),
        ('G', 'Good'),
        ('F', 'Fair'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    artist = models.ForeignKey(Artist, on_delete=models.CASCADE, related_name='vinyls')
    label = models.ForeignKey(RecordLabel, on_delete=models.SET_NULL, null=True, blank=True, related_name='vinyls')
    genre = models.ManyToManyField(VinylGenre, blank=True)
    release_year = models.IntegerField()
    size = models.CharField(max_length=2, choices=SIZE_CHOICES, default='12')
    speed = models.CharField(max_length=2, choices=SPEED_CHOICES, default='33')
    condition = models.CharField(max_length=3, choices=CONDITION_CHOICES, default='VG+')
    catalog_number = models.CharField(max_length=50, blank=True, null=True)
    tracks = models.PositiveIntegerField(blank=True, null=True)
    tracklist = models.TextField(blank=True, null=True, help_text='Una canzone per riga')
    description = models.TextField(blank=True, null=True)
    cover_image = models.ImageField(upload_to='vinyl_covers/', blank=True, null=True)
    rating = models.DecimalField(max_digits=2, decimal_places=1, default=0.0)
    is_available = models.BooleanField(default=True)
    added_date = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ['title']
        verbose_name_plural = 'Vinyls'

    def __str__(self):
        return f"{self.title} - {self.artist}"

    def get_absolute_url(self):
        return reverse('vinyl:vinyl_detail', kwargs={'pk': str(self.id)})
