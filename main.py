from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired
import requests

url = "https://api.themoviedb.org/3/search/movie"
MOVIE_DB_API_KEY = "5b8d241d5bd151d3c878c2e048aee54f"  # Use your provided API key

headers = {
    'accept': 'application/json',
    'Authorization': 'Bearer eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiI1YjhkMjQxZDViZDE1MWQzYzg3OGMyZTA0OGFlZTU0ZiIsInN1YiI6IjY1YTdlNzVjNWI5NTA4MDEyZmJmMzFjMSIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.jq8NGWtoZv8t0GVp1nzRu_tjBuzefRH_xZwVuv0MBeY'
}

db = SQLAlchemy()
app = Flask(__name__)
app.config['SECRET_KEY'] = '8BYkEfBA6O6donzWlSihBXox7C0sKR6b'
Bootstrap5(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///movie.db'
db.init_app(app)

class Movie(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(250), unique=True, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(500), nullable=False)
    rating = db.Column(db.Float, nullable=True)
    ranking = db.Column(db.Integer, nullable=True)
    review = db.Column(db.String(250), nullable=True)
    img_url = db.Column(db.String(250), nullable=False)

with app.app_context():
    db.create_all()

class RateMovieForm(FlaskForm):
    rating = StringField("Your Rating 1.0 to 10.0")
    review = StringField("Your Review")
    submit = SubmitField("Done")

class FindMovieForm(FlaskForm):
    title = StringField("Movie Title", validators=[DataRequired()])
    submit = SubmitField("Add Movie")

@app.route("/")
def home():
    result = db.session.execute(db.select(Movie))
    all_movies = result.scalars()
    return render_template("index.html", movies=all_movies)


@app.route("/add", methods=["GET", "POST"])
def add_movie():
    form = FindMovieForm()

    if form.validate_on_submit():
        movie_title = form.title.data

        # Make a request to The Movie Database API to search for movies
        search_url = "https://api.themoviedb.org/3/search/movie"
        params = {
            'api_key': MOVIE_DB_API_KEY,
            'query': movie_title,
        }

        response = requests.get(search_url, params=params)
        data = response.json()["results"]
        return render_template("select.html", options=data)

    return render_template("add.html", form=form)

@app.route("/add/<int:movie_id>")
def add_selected_movie(movie_id):
    # Retrieve detailed information about the selected movie
    movie_url = f"https://api.themoviedb.org/3/movie/{movie_id}"
    params = {'api_key': MOVIE_DB_API_KEY}
    response = requests.get(movie_url, params=params)
    selected_movie = response.json()

    # Extract relevant details from the API response
    title = selected_movie.get('title', '')
    year = selected_movie.get('release_date', '')[:4]  # Extract the year from the release date
    description = selected_movie.get('overview', '')
    img_url = f"https://image.tmdb.org/t/p/w500/{selected_movie.get('poster_path', '')}"

    movie_count = Movie.query.count()
    default_rank = 10 - movie_count

    # Add the selected movie to the database
    new_movie = Movie(
        title=title,
        year=year,
        description=description,
        rating=None,  # You can set a default value or prompt the user to provide this
        ranking=default_rank if default_rank > 0 else 1,  # You can set a default value or prompt the user to provide this
        review=None,  # You can set a default value or prompt the user to provide this
        img_url=img_url,
    )

    db.session.add(new_movie)
    db.session.commit()

    return redirect(url_for("home"))


@app.route("/edit", methods=["GET", "POST"])
def rate_movie():
    form = RateMovieForm()
    movie_id = request.args.get("id")
    movie = db.get_or_404(Movie, movie_id)
    if form.validate_on_submit():
        movie.rating = float(form.rating.data)
        movie.review = form.review.data
        db.session.commit()
        return redirect(url_for('home'))
    return render_template("edit.html", movie=movie, form=form)


@app.route("/delete/<int:id>")
def delete_movie(id):
    movie_to_delete = db.get_or_404(Movie, id)
    deleted_movie_ranking = movie_to_delete.ranking

    db.session.delete(movie_to_delete)
    db.session.commit()

    max_ranking_movie = db.session.query(db.func.max(Movie.ranking)).scalar()
    if max_ranking_movie:
        # Find the vacant positions (rankings not used)
        vacant_positions = set(range(1, max_ranking_movie + 1)) - set(
            db.session.query(Movie.ranking).distinct().all()
        )

        # If there are vacant positions, fill the first one
        if vacant_positions:
            vacant_position = min(vacant_positions)
        else:
            # If no vacant positions, use the next available ranking
            vacant_position = max_ranking_movie + 1
    else:
        # If the list is empty, start from 1
        vacant_position = 1

        # Update the ranking of the next movie to be added
    db.session.execute(
        db.update(Movie)
        .where(Movie.ranking > deleted_movie_ranking)
        .values(ranking=Movie.ranking - 1)
    )

    db.session.commit()

    return redirect(url_for("home"))


if __name__ == '__main__':
    app.run(debug=True)
