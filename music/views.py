from django.contrib.auth import authenticate, login
from django.contrib.auth import logout
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, render_to_response
from django.db.models import Q
from .forms import AlbumForm, SongForm, UserForm
from .models import Album, Song, Feedback
import sqlite3

AUDIO_FILE_TYPES = ['wav', 'mp3', 'ogg']
IMAGE_FILE_TYPES = ['png', 'jpg', 'jpeg']

def sqlconnection():
    conn = sqlite3.connect('pybass.db')
    return conn

def create_album(request):
    if not request.user.is_authenticated():
        return render(request, 'music/login.html')
    else:
        form = AlbumForm(request.POST or None, request.FILES or None)
        if form.is_valid():
            album = form.save(commit=False)
            album.user = request.user
            album.album_logo = request.FILES['album_logo']
            file_type = album.album_logo.url.split('.')[-1]
            file_type = file_type.lower()
            if file_type not in IMAGE_FILE_TYPES:
                context = {
                    'album': album,
                    'form': form,
                    'error_message': 'Image file must be PNG, JPG, or JPEG',
                }
                return render(request, 'music/create_album.html', context)
            album.save()
            return render(request, 'music/detail.html', {'album': album})
        context = {
            "form": form,
        }
        return render(request, 'music/create_album.html', context)


def create_song(request, album_id):
    form = SongForm(request.POST or None, request.FILES or None)
    album = get_object_or_404(Album, pk=album_id)
    if form.is_valid():
        albums_songs = album.song_set.all()
        for s in albums_songs:
            if s.song_title == form.cleaned_data.get("song_title"):
                context = {
                    'album': album,
                    'form': form,
                    'error_message': 'You already added that song',
                }
                return render(request, 'music/create_song.html', context)
        song = form.save(commit=False)
        song.album = album
        song.audio_file = request.FILES['audio_file']
        file_type = song.audio_file.url.split('.')[-1]
        file_type = file_type.lower()
        if file_type not in AUDIO_FILE_TYPES:
            context = {
                'album': album,
                'form': form,
                'error_message': 'Audio file must be WAV, MP3, or OGG',
            }
            return render(request, 'music/create_song.html', context)

        song.save()
        return render(request, 'music/detail.html', {'album': album})
    context = {
        'album': album,
        'form': form,
    }
    return render(request, 'music/create_song.html', context)


def delete_album(request, album_id):
    album = Album.objects.get(pk=album_id)
    album.delete()
    albums = Album.objects.filter(user=request.user)
    return render(request, 'music/index.html', {'albums': albums})


def delete_song(request, album_id, song_id):
    album = get_object_or_404(Album, pk=album_id)
    song = Song.objects.get(pk=song_id)
    song.delete()
    return render(request, 'music/detail.html', {'album': album})


def detail(request, album_id):
    if not request.user.is_authenticated():
        return render(request, 'music/login.html')
    else:
        user = request.user
        album = get_object_or_404(Album, pk=album_id)
        return render(request, 'music/detail.html', {'album': album, 'user': user})


def favorite(request, song_id):
    song = get_object_or_404(Song, pk=song_id)
    try:
        if song.is_favorite:
            song.is_favorite = False
        else:
            song.is_favorite = True
        song.save()
    except (KeyError, Song.DoesNotExist):
        return JsonResponse({'success': False})
    else:
        return JsonResponse({'success': True})


def favorite_album(request, album_id):
    album = get_object_or_404(Album, pk=album_id)
    try:
        if album.is_favorite:
            album.is_favorite = False
        else:
            album.is_favorite = True
        album.save()
    except (KeyError, Album.DoesNotExist):
        return JsonResponse({'success': False})
    else:
        return JsonResponse({'success': True})


def index(request):
    if not request.user.is_authenticated():
        return render(request, 'music/login.html')
    else:
        albums = Album.objects.filter(user=request.user)
        song_results = Song.objects.all()
        query = request.GET.get("q")
        if query:
            albums = albums.filter(
                Q(album_title__icontains=query) |
                Q(artist__icontains=query)
            ).distinct()
            song_results = song_results.filter(
                Q(song_title__icontains=query)
            ).distinct()
            return render(request, 'music/index.html', {
                'albums': albums,
                'songs': song_results,
            })
        else:
            return render(request, 'music/index.html', {'albums': albums})


def logout_user(request):
    logout(request)
    form = UserForm(request.POST or None)
    context = {
        "form": form,
    }
    return render(request, 'music/login.html', context)


def login_user(request):
    if request.method == "POST":
        username = request.POST['username']
        password = request.POST['password']
        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                albums = Album.objects.filter(user=request.user)
                return render(request, 'music/index.html', {'albums': albums})
            else:
                return render(request, 'music/login.html', {'error_message': 'Your account has been disabled'})
        else:
            return render(request, 'music/login.html', {'error_message': 'Invalid login'})
    return render(request, 'music/login.html')


def register(request):
    form = UserForm(request.POST or None)
    if form.is_valid():
        user = form.save(commit=False)
        username = form.cleaned_data['username']
        password = form.cleaned_data['password']
        user.set_password(password)
        user.save()
        user = authenticate(username=username, password=password)
        if user is not None:
            if user.is_active:
                login(request, user)
                albums = Album.objects.filter(user=request.user)
                return render(request, 'music/index.html', {'albums': albums})
    context = {
        "form": form,
    }
    return render(request, 'music/register.html', context)


def songs(request, filter_by):
    if not request.user.is_authenticated():
        return render(request, 'music/login.html')
    else:
        try:
            song_ids = []
            for album in Album.objects.filter(user=request.user):
                for song in album.song_set.all():
                    song_ids.append(song.pk)
            users_songs = Song.objects.filter(pk__in=song_ids)
            if filter_by == 'favorites':
                users_songs = users_songs.filter(is_favorite=True)
        except Album.DoesNotExist:
            users_songs = []
        return render(request, 'music/songs.html', {
            'song_list': users_songs,
            'filter_by': filter_by,
        })


def feedback(request):
    if not request.user.is_authenticated():
        return render(request, 'music/login.html')
    else:
        if request.method == "POST":
            conn = sqlconnection()
            presentation = request.POST.get("presentation", None)
            collaboration = request.POST.get("collaboration", None)
            objectives = request.POST.get("objectives", None)
            if request.POST.get("review", None).strip() != "":
                suggestion = request.POST.get("review", None)
            else:
                suggestion = "No Suggestions "

            conn.execute(
                '''INSERT  INTO  music_Feedback(fname, lname, presentation,
                   collaboration, objectives, suggestion)
                   VALUES ('{}', '{}', '{}', '{}','{}', '{}')''' \
                    .format(request.POST.get("fname", None),
                            request.POST.get("lname", None),
                            presentation, collaboration, objectives, suggestion
                            )
            )
            conn.commit()
            conn.close()
            return index(request)
        elif request.method == "GET":
            return render_to_response("music/feedback.html")
            
            
def q1(request):
    conn = sqlconnection()
    cursor = conn.execute("select username , email , date_joined from auth_user").fetchall()

    context = {"cursor": cursor}
    conn.close()
    return render(request, "music/demo1.html", context)


def q2(request):
    conn = sqlconnection()
    cursor = conn.execute(
        '''select s.song_title, a.album_title, a.artist
            from music_album a, music_song s, auth_user u where a.id = s.album_id 
            and a.user_id = u.id and u.is_superuser = 1
            order by a.album_title, a.artist''' \
    ).fetchall()

    context = {"cursor": cursor}
    conn.close()
    return render(request, "music/demo2.html", context)


def q3(request):
    conn = sqlconnection()
    cursor = conn.execute("select * from music_feedback").fetchall()

    context = {"cursor": cursor}
    conn.close()
    return render(request, "music/demo3.html", context)


def q4(request):
    conn = sqlconnection()

    cursor = conn.execute("drop view userview")
    conn.commit()
    cursor.close()

    cursor = conn.execute(
        '''create view userview as 
           select u.username, count(distinct(a.album_title)), count(distinct(s.song_title))
           from music_album a, music_song s, auth_user u 
           where s.album_id in 
           (select a1.id from music_album a1 where a1.user_id in 
              (select u1.id from auth_user u1 where u1.last_login in 
                (select max(last_login) from auth_user)
              )
           )''' \
    )
    conn.commit()
    cursor = cursor.execute("select * from userview").fetchall()

    context = {"cursor": cursor}
    conn.close()
    return render(request, "music/demo4.html", context)


def q5(request):
    conn = sqlconnection()
    cursor = conn.execute(
        '''select s.song_title , a.genre from music_album a , music_song s , auth_user u 
          where  s.album_id = a.id and  a.user_id = u.id and 
          u.last_login = (select max(last_login) from auth_user)''' \
    ).fetchall()

    context = {"cursor": cursor}
    conn.close()
    return render(request, "music/demo5.html", context)
