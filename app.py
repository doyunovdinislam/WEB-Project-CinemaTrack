


from flask import Flask, render_template, request, redirect, url_for,  abort
from flask_login import (
    LoginManager,
    login_user,
    login_required,
    logout_user,
    current_user,
)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from difflib import get_close_matches
from datetime import datetime
import os
import uuid
import re


basedir = os.path.abspath(os.path.dirname(__file__))
app = Flask(__name__)


app.config["SECRET_KEY"] = "secret123"
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(
    basedir, "db", "db.sqlite3"
)
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["UPLOAD_FOLDER"] = os.path.join(basedir, "static/img")

from data import db
from data.allmodels import *

db.init_app(app)

login_manager = LoginManager(app)
login_manager.login_view = "login"




ADMIN_USERS = ["admin77777", "Dinislam2010"]


def is_admin():
    return current_user.is_authenticated and current_user.username in ADMIN_USERS


def can_edit_movie(movie):
    if not current_user.is_authenticated:
        return False

    if is_admin():
        return True

    return movie.user_id == current_user.id


def time_ago(dt):
    if dt is None:
        return "только что"

    diff = datetime.utcnow() - dt

    if diff.seconds < 60:
        return "только что"
    elif diff.seconds < 3600:
        return f"{diff.seconds // 60} мин назад"
    elif diff.seconds < 86400:
        return f"{diff.seconds // 3600} ч назад"
    else:
        return f"{diff.days} дн назад"



def normalize(text):
    if not text:
        return ""

    text = text.lower()
    text = re.sub(r"[^a-zа-я0-9 ]", "", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text


def time_ago(dt):
    diff = datetime.utcnow() - dt

    if diff.seconds < 60:
        return "только что"

    if diff.seconds < 3600:
        return f"{diff.seconds // 60} мин назад"

    if diff.seconds < 86400:
        return f"{diff.seconds // 3600} ч назад"

    return f"{diff.days} дн назад"



@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@app.context_processor
def inject_permissions():
    return dict(can_edit_movie=can_edit_movie, is_admin=is_admin)


@app.route("/")
def index():
    sort = request.args.get("sort")

    q = request.args.get("q", "").strip()
    selected_genres = request.args.getlist("genre")

    all_movies = Movie.query.all()

    if q and len(q) < 2:
        return render_template(
            "index.html",
            movies=all_movies,
            selected_genres=selected_genres,
            suggestion=None,
        )

    movies = all_movies

    if q:
        normalized_q = normalize(q)
        words = normalized_q.split()

        exact_matches = []
        partial_matches = []

        for m in all_movies:
            title_norm = normalize(m.title)
            desc_norm = normalize(m.description)
            genre_norm = normalize(m.genre)

            full_text = f"{title_norm} {desc_norm} {genre_norm}"

            if normalized_q in title_norm and len(normalized_q) > 5:
                if title_norm.startswith(normalized_q):
                    exact_matches.append(m)
                else:
                    partial_matches.append(m)
                continue

            if all(word in full_text for word in words):
                partial_matches.append(m)
                continue

            for word in words:
                if word in title_norm:
                    partial_matches.append(m)
                    break

        movies = exact_matches if exact_matches else partial_matches

    if selected_genres:
        movies = [
            m
            for m in movies
            if any(g.lower() in (m.genre or "").lower() for g in selected_genres)
        ]

    if sort == "rating":
        movies = sorted(movies, key=lambda m: m.avg_rating or 0, reverse=True)

    elif sort == "views":
        movies = sorted(movies, key=lambda m: m.views or 0, reverse=True)

    elif sort == "new":
        movies = sorted(movies, key=lambda m: m.id, reverse=True)

    suggestion = None
    all_titles = [m.title.lower() for m in all_movies]

    if q and not movies:
        match = get_close_matches(q.lower(), all_titles, n=1, cutoff=0.4)
        if match:
            suggestion = match[0].title()

    if current_user.is_authenticated:
        favorite_ids = {
            f.movie_id for f in Favorite.query.filter_by(user_id=current_user.id).all()
        }

        for m in movies:
            m.is_favorite = m.id in favorite_ids
    else:
        for m in movies:
            m.is_favorite = False

    return render_template(
        "index.html",
        movies=movies,
        selected_genres=selected_genres,
        suggestion=suggestion,
    )


@app.route("/register", methods=["GET", "POST"])
def register():
    error = None

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        confirm = request.form.get("confirm")
        display_name = request.form.get("display_name")

        if not username or len(username) < 6:
            error = "Логин минимум 6 символов"

        elif password != confirm:
            error = "Пароли не совпадают"

        elif User.query.filter_by(username=username).first():
            error = "Пользователь уже существует"

        else:
            user = User(
                username=username,
                password=generate_password_hash(password),
                display_name=display_name,
            )

            db.session.add(user)
            db.session.commit()

            login_user(user)
            return redirect("/")

    return render_template("register.html", error=error)


@app.route("/login", methods=["GET", "POST"])
def login():
    error = None

    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = User.query.filter_by(username=username).first()

        if not user or not check_password_hash(user.password, password):
            error = "Неверный логин или пароль"
        else:
            login_user(user)
            return redirect("/")

    return render_template("login.html", error=error)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect("/")


@app.route("/settings", methods=["GET", "POST"])
@login_required
def settings():

    if request.method == "POST":

        desc = request.form.get("description")

        if desc and len(desc) > 120:
            desc = desc[:120]

        current_user.description = desc

        if "remove_avatar" in request.form:
            current_user.avatar = "default.png"
            db.session.commit()
            return redirect(url_for("settings"))

        file = request.files.get("avatar")

        if file and file.filename != "":
            filename = secure_filename(file.filename)

            filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
            file.save(filepath)

            current_user.avatar = filename

        db.session.commit()
        return redirect(url_for("settings"))

    return render_template("settings.html")


@app.route("/my_movies", methods=["GET", "POST"])
@login_required
def my_movies():

    if request.method == "POST":

        title = request.form.get("title")

        if title:
            title = title.strip()

        description = request.form.get("description")

        genre = request.form.get("genre")

        if genre:
            genre = request.form.get("genre")
            country = request.form.get("country")
            director = request.form.get("director")
            duration = request.form.get("duration")

            genre = genre.lower()

        poster_file = request.files.get("poster")
        poster2_file = request.files.get("poster2")
        video_file = request.files.get("video")

        poster_name = None
        poster2_name = None
        video_name = None

        if poster_file and poster_file.filename != "":
            ext = poster_file.filename.rsplit(".", 1)[-1]
            poster_name = f"{uuid.uuid4().hex}.{ext}"

            path = os.path.join("static/uploads/posters", poster_name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            poster_file.save(path)

        if poster2_file and poster2_file.filename != "":
            ext = poster2_file.filename.rsplit(".", 1)[-1]
            poster2_name = f"{uuid.uuid4().hex}.{ext}"

            path = os.path.join("static/uploads/posters", poster2_name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            poster2_file.save(path)

        if video_file and video_file.filename != "":
            ext = video_file.filename.rsplit(".", 1)[-1]
            video_name = f"{uuid.uuid4().hex}.{ext}"

            path = os.path.join("static/uploads/movies", video_name)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            video_file.save(path)

        movie = Movie(
            title=title,
            description=description,
            poster=poster_name,
            poster2=poster2_name,
            video=video_name,
            genre=genre,  # ВАЖНО
            country=country,
            director=director,
            duration=duration,
            user_id=current_user.id,
        )

        db.session.add(movie)
        db.session.commit()

        return redirect("/my_movies")

    movies = Movie.query.filter_by(user_id=current_user.id).all()

    return render_template("my_movies.html", movies=movies)


@app.route("/edit_movie/<int:id>", methods=["GET", "POST"])
@login_required
def edit_movie(id):

    movie = Movie.query.get_or_404(id)

    if not can_edit_movie(movie):
        abort(403)

    if request.method == "POST":

        genre = request.form.get("genre")
        country = request.form.get("country")
        director = request.form.get("director")
        duration = request.form.get("duration")

        movie.title = request.form.get("title")
        movie.description = request.form.get("description")

        movie.genre = genre
        movie.country = country
        movie.director = director
        movie.duration = duration

        poster_file = request.files.get("poster")
        poster2_file = request.files.get("poster2")

        if poster_file and poster_file.filename != "":
            ext = poster_file.filename.rsplit(".", 1)[-1]
            filename = f"{uuid.uuid4().hex}.{ext}"

            path = os.path.join("static/uploads/posters", filename)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            poster_file.save(path)

            movie.poster = filename

        if poster2_file and poster2_file.filename != "":
            ext = poster2_file.filename.rsplit(".", 1)[-1]
            filename = f"{uuid.uuid4().hex}.{ext}"

            path = os.path.join("static/uploads/posters", filename)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            poster2_file.save(path)

            movie.poster2 = filename

        db.session.commit()

        return redirect("/my_movies")

    return render_template("edit_movie.html", movie=movie)


@app.route("/movie/<int:id>")
def movie_page(id):

    watched_ids = []

    if current_user.is_authenticated:
        watched_ids = [
            w.movie_id for w in Watched.query.filter_by(user_id=current_user.id).all()
        ]

    movie = Movie.query.get_or_404(id)

    if current_user.is_authenticated:

        already_watched = Watched.query.filter_by(
            user_id=current_user.id, movie_id=id
        ).first()

        if not already_watched:
            watched = Watched(user_id=current_user.id, movie_id=id)
            db.session.add(watched)

            movie.views += 1

            db.session.commit()

    favorites_count = Favorite.query.filter_by(movie_id=id).count()

    if current_user.is_authenticated:
        exists = Watched.query.filter_by(user_id=current_user.id, movie_id=id).first()

        if exists:
            exists.created_at = datetime.utcnow()
        else:
            watched = Watched(user_id=current_user.id, movie_id=id)
            db.session.add(watched)

        db.session.commit()

    user = User.query.get(movie.user_id)

    comments = Comment.query.filter_by(movie_id=id).all()

    for c in comments:
        likes = CommentLike.query.filter_by(comment_id=c.id, value=1).count()
        dislikes = CommentLike.query.filter_by(comment_id=c.id, value=-1).count()

        c.likes_count = likes
        c.dislikes_count = dislikes

        if current_user.is_authenticated:
            user_reaction = CommentLike.query.filter_by(
                comment_id=c.id, user_id=current_user.id
            ).first()

            c.user_reaction = user_reaction.value if user_reaction else 0
        else:
            c.user_reaction = 0

    is_favorite = False
    if current_user.is_authenticated:
        fav = Favorite.query.filter_by(user_id=current_user.id, movie_id=id).first()
        is_favorite = True if fav else False

    ratings = Rating.query.filter_by(movie_id=id).all()

    avg_rating = 0
    if ratings:
        avg_rating = round(sum(r.value for r in ratings) / len(ratings), 1)

    user_rating = 0
    if current_user.is_authenticated:
        r = Rating.query.filter_by(user_id=current_user.id, movie_id=id).first()
        if r:
            user_rating = r.value

    ratings_count = Rating.query.filter_by(movie_id=id).count()

    return render_template(
        "movie.html",
        movie=movie,
        user=user,
        is_favorite=is_favorite,
        avg_rating=avg_rating,
        user_rating=user_rating,
        comments=comments,
        favorites_count=favorites_count,
        watched_ids=watched_ids,
        time_ago=time_ago,
        ratings_count=ratings_count,
    )


@app.route("/add_favorite/<int:id>")
@login_required
def add_favorite(id):

    exists = Favorite.query.filter_by(user_id=current_user.id, movie_id=id).first()

    if not exists:
        fav = Favorite(user_id=current_user.id, movie_id=id)
        db.session.add(fav)
        db.session.commit()

    return redirect("/")


@app.route("/favorites")
@login_required
def favorites():

    favorite_links = Favorite.query.filter_by(user_id=current_user.id).all()

    movie_ids = [f.movie_id for f in favorite_links]

    movies = Movie.query.filter(Movie.id.in_(movie_ids)).all()

    favorites_count = len(movies)

    return render_template(
        "favorites.html", movies=movies, favorites_count=favorites_count
    )


@app.route("/rate/<int:id>/<int:value>")
@login_required
def rate_movie(id, value):

    if value < 1 or value > 5:
        return redirect(url_for("movie_page", id=id))

    rating = Rating.query.filter_by(user_id=current_user.id, movie_id=id).first()

    if rating:
        rating.value = value
    else:
        new_rating = Rating(user_id=current_user.id, movie_id=id, value=value)
        db.session.add(new_rating)

    movie = Movie.query.get_or_404(id)

    ratings = Rating.query.filter_by(movie_id=id).all()

    if ratings:
        avg = sum(r.value for r in ratings) / len(ratings)
    else:
        avg = 0

    movie.avg_rating = round(avg, 1)

    db.session.commit()

    return redirect(url_for("movie_page", id=id))


@app.route("/add_comment/<int:id>", methods=["POST"])
@login_required
def add_comment(id):

    text = request.form.get("text")

    if text and text.strip() != "":
        comment = Comment(text=text, user_id=current_user.id, movie_id=id)
        db.session.add(comment)
        db.session.commit()

    return redirect(url_for("movie_page", id=id))


@app.route("/delete_comment/<int:id>")
@login_required
def delete_comment(id):

    comment = Comment.query.get_or_404(id)

    if not (is_admin() or comment.user_id == current_user.id):
        abort(403)

    db.session.delete(comment)
    db.session.commit()

    return redirect(request.referrer or "/")


@app.route("/live_search")
def live_search():
    q = request.args.get("q", "").strip()

    if not q or len(q) < 2:
        return {"movies": []}

    normalized_q = normalize(q)
    all_movies = Movie.query.all()

    exact_matches = []
    partial_matches = []

    for m in all_movies:
        title_norm = normalize(m.title)

        if title_norm == normalized_q:
            exact_matches = [m]
            break

        if normalized_q in title_norm and len(normalized_q) > 5:
            if title_norm.startswith(normalized_q):
                exact_matches.append(m)
            else:
                partial_matches.append(m)
            continue

        if normalized_q in title_norm:
            partial_matches.append(m)

    if exact_matches:
        movies = exact_matches
    else:
        movies = partial_matches

    return {
        "movies": [{"id": m.id, "title": m.title, "poster": m.poster} for m in movies]
    }


@app.route("/watched")
@login_required
def watched():

    watched = Watched.query.filter_by(user_id=current_user.id).all()

    for w in watched:
        ratings = Rating.query.filter_by(movie_id=w.movie.id).all()

        if ratings:
            w.movie.avg_rating = round(sum(r.value for r in ratings) / len(ratings), 1)
        else:
            w.movie.avg_rating = 0

    return render_template("watched.html", watched=watched)


@app.route("/react_comment/<int:id>/<value>")
@login_required
def react_comment(id, value):

    try:
        value = int(value)
    except:
        return {"status": "error"}

    if value not in [1, -1]:
        return {"status": "error"}

    reaction = CommentLike.query.filter_by(
        user_id=current_user.id, comment_id=id
    ).first()

    if reaction:
        if reaction.value == value:
            db.session.delete(reaction)
        else:
            reaction.value = value
    else:
        db.session.add(CommentLike(user_id=current_user.id, comment_id=id, value=value))

    db.session.commit()

    likes = CommentLike.query.filter_by(comment_id=id, value=1).count()

    dislikes = CommentLike.query.filter_by(comment_id=id, value=-1).count()

    user_reaction = CommentLike.query.filter_by(
        user_id=current_user.id, comment_id=id
    ).first()

    return {
        "status": "ok",
        "likes": likes,
        "dislikes": dislikes,
        "user_reaction": user_reaction.value if user_reaction else 0,
    }


@app.route("/toggle_favorite/<int:movie_id>", methods=["POST"])
@login_required
def toggle_favorite(movie_id):

    favorites = Favorite.query.filter_by(
        user_id=current_user.id, movie_id=movie_id
    ).all()

    if favorites:
        for fav in favorites:
            db.session.delete(fav)

        db.session.commit()

        return {"status": "removed"}

    else:
        new_fav = Favorite(user_id=current_user.id, movie_id=movie_id)

        db.session.add(new_fav)
        db.session.commit()

        return {"status": "added"}


@app.route("/delete_movie/<int:id>")
@login_required
def delete_movie(id):

    movie = Movie.query.get_or_404(id)

    if not can_edit_movie(movie):
        abort(403)

    db.session.delete(movie)
    db.session.commit()

    return redirect("/")


@app.context_processor
def inject_time():
    return dict(time_ago=time_ago)


@app.route("/clear_favorites", methods=["POST"])
@login_required
def clear_favorites():

    Favorite.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()

    return {"status": "cleared"}


@app.route("/user/<int:user_id>")
def user_profile(user_id):

    user = User.query.get_or_404(user_id)
    movies = Movie.query.filter_by(user_id=user.id).all()

    for m in movies:
        ratings = Rating.query.filter_by(movie_id=m.id).all()

        if ratings:
            m.avg_rating = round(sum(r.value for r in ratings) / len(ratings), 1)
        else:
            m.avg_rating = 0

    user_ratings = UserRating.query.filter_by(user_id=user.id).all()

    if user_ratings:
        avg_user_rating = round(
            sum(r.value for r in user_ratings) / len(user_ratings), 1
        )
    else:
        avg_user_rating = 0

    user_rating = None
    if current_user.is_authenticated:
        r = UserRating.query.filter_by(
            user_id=user.id, rater_id=current_user.id
        ).first()

        if r:
            user_rating = r.value

    return render_template(
        "user_profile.html",
        user=user,
        movies=movies,
        avg_user_rating=avg_user_rating,
        user_rating=user_rating,
        ADMIN_USERS=ADMIN_USERS,
    )


@app.route("/rate_user/<int:user_id>/<int:value>")
@login_required
def rate_user(user_id, value):

    if value < 1 or value > 5:
        return redirect(request.referrer)

    if current_user.id == user_id:
        return redirect(request.referrer)

    rating = UserRating.query.filter_by(
        user_id=user_id, rater_id=current_user.id
    ).first()

    if rating:
        rating.value = value
    else:
        rating = UserRating(user_id=user_id, rater_id=current_user.id, value=value)
        db.session.add(rating)

    db.session.commit()

    return redirect(request.referrer)


@app.context_processor
def inject_utils():
    return dict(time_ago=time_ago)


@app.context_processor
def inject_admin():
    return dict(is_admin=is_admin)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)
