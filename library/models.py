from django.db import models
from django.urls import reverse
import uuid


class Author(models.Model):
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    
    class Meta:
        ordering = ['last_name', 'first_name']
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"


class Publisher(models.Model):
    name = models.CharField(max_length=200)
    website = models.URLField(blank=True, null=True)
    
    def __str__(self):
        return self.name


class BookGenre(models.Model):
    name = models.CharField(max_length=100, unique=True)
    
    def __str__(self):
        return self.name


class Book(models.Model):
    ISBN_CHOICES = [
        ('isbn13', 'ISBN-13'),
        ('isbn10', 'ISBN-10'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=200)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='books')
    publisher = models.ForeignKey(Publisher, on_delete=models.SET_NULL, null=True, blank=True, related_name='books')
    isbn_type = models.CharField(max_length=10, choices=ISBN_CHOICES)
    isbn_number = models.CharField(max_length=20, unique=True)
    genre = models.ManyToManyField(BookGenre, blank=True)
    publication_year = models.IntegerField()
    pages = models.PositiveIntegerField(blank=True, null=True)
    language = models.CharField(max_length=50, default='Italiano')
    description = models.TextField(blank=True, null=True)
    cover_image = models.ImageField(upload_to='book_covers/', blank=True, null=True)
    rating = models.DecimalField(max_digits=2, decimal_places=1, default=0.0)
    is_available = models.BooleanField(default=True)
    added_date = models.DateField(auto_now_add=True)
    
    class Meta:
        ordering = ['-added_date']
    
    def __str__(self):
        return f"{self.title} by {self.author}"
    
    def get_absolute_url(self):
        return reverse('library:book_detail', kwargs={'pk': str(self.id)})


class BookRecord(models.Model):
    STATUS_CHOICES = [
        ('unread', 'Non letto'),
        ('reading', 'In lettura'),
        ('read', 'Letto'),
        ('want_to_read', 'Voglio leggere'),
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
