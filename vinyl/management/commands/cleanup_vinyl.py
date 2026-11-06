from django.conf import settings
from django.core.management.base import BaseCommand
from django.db import transaction

from vinyl.models import Artist, RecordLabel, Vinyl, VinylGenre


class Command(BaseCommand):
    help = (
        'Rimuove artisti, etichette e generi senza vinili e le copertine in '
        'media/vinyl_covers non usate da nessun vinile. Senza --apply simula soltanto.'
    )

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true', help='Esegue davvero la pulizia (default: simulazione).')

    def handle(self, *args, **options):
        apply = options['apply']
        prefix = '' if apply else '[simulazione] '

        orphans = {
            'artisti': Artist.objects.filter(vinyls__isnull=True),
            'etichette': RecordLabel.objects.filter(vinyls__isnull=True),
            'generi': VinylGenre.objects.filter(vinyl__isnull=True),
        }
        with transaction.atomic():
            for label, qs in orphans.items():
                names = list(qs.values_list('name', flat=True))
                self.stdout.write(f'{prefix}{label} senza vinili: {len(names)}' + (f' ({", ".join(names)})' if names else ''))
                if apply:
                    qs.delete()

        covers_dir = settings.MEDIA_ROOT / 'vinyl_covers'
        if not covers_dir.is_dir():
            self.stdout.write(f'{covers_dir} non esiste: nessuna copertina da controllare.')
            return
        used = {v.cover_image.name.rsplit('/', 1)[-1] for v in Vinyl.objects.exclude(cover_image='')}
        unused = [f for f in covers_dir.iterdir() if f.is_file() and f.name not in used and '_t' not in f.stem[-6:]]
        size_kb = sum(f.stat().st_size for f in unused) // 1024
        self.stdout.write(f'{prefix}copertine non usate: {len(unused)} ({size_kb} KB)')
        for f in unused:
            self.stdout.write(f'  {f.name}')
            if apply:
                f.unlink()

        if not apply:
            self.stdout.write(self.style.WARNING('Nessuna modifica fatta. Usa --apply per eseguire.'))
