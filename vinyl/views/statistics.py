from django.db.models import Count
from django.shortcuts import render

from ..models import Artist, Vinyl, VinylGenre


def statistics(request):
    total_vinyls = Vinyl.objects.count()
    available_vinyls = Vinyl.objects.filter(is_available=True).count()
    total_artists = Artist.objects.count()

    genres = VinylGenre.objects.annotate(vinyl_count=Count('vinyl'))

    context = {
        'total_vinyls': total_vinyls,
        'available_vinyls': available_vinyls,
        'total_artists': total_artists,
        'genres': genres,
    }
    return render(request, 'vinyl/statistics.html', context)
