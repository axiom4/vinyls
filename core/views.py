from django.shortcuts import redirect


def index(request):
    return redirect('vinyl:vinyl_list')
