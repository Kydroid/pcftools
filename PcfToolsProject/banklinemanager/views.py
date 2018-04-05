from django.shortcuts import render
from django.http import HttpResponse

# Create your views here.
def index(request):
    # albums = Album.objects.filter(available=True).order_by('-created_at')[:12]
    # context = {
    #     'albums': albums
    # }
    # return render(request, 'store/index.html', context)
    pass

def listing(request):
    # albums_list = Album.objects.filter(available=True)
    # paginator = Paginator(albums_list, 9)
    # page = request.GET.get('page')
    # try:
    #     albums = paginator.page(page)
    # except PageNotAnInteger:
    #     albums = paginator.page(1)
    # except EmptyPage:
    #     albums = paginator.page(paginator.num_pages)
    # context = {
    #     'albums': albums,
    #     'paginate': True
    # }
    # return render(request, 'store/listing.html', context)
    message = "Bienvenue sur banklinemanager!"
    return HttpResponse(message) #renvoi un objet http simple