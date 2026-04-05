from app.database import BaseModel
from peewee import CharField


class Url(BaseModel):
    original_url = CharField()
    short_code = CharField(unique=True)
