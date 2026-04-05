from app import create_app
from app.database import db
from app.models.url import Url

app = create_app()

with app.app_context():
    db.create_tables([Url], safe=True)

if __name__ == "__main__":
    app.run(debug=True)
