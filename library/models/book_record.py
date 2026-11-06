import uuid

from django.db import models
from django.utils.translation import gettext_lazy as _

from .book import Book


class BookRecord(models.Model):
    STATUS_CHOICES = [
        ('unread', _('Non letto')),
        ('reading', _('In lettura')),
        ('read', _('Letto')),
        ('want_to_read', _('Voglio leggere')),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='records')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='want_to_read')
    rating_given = models.DecimalField(max_digits=2, decimal_places=1, blank=True, null=True)
    notes = models.TextField(blank=True, null=True)
    date_added = models.DateField(auto_now_add=True)
    date_finished = models.DateField(blank=True, null=True)
    
    class Meta:
        ordering = ['-date_added']
    
    def __str__(self):
        return f"{self.book.title} - {self.get_status_display()}"
