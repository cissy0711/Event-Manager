from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from database_setup import User,Base,Folder,Event

engine = create_engine('sqlite:///event_manager.db')
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
session = DBSession()

for user in session.query(User):
    session.delete(user)
    session.commit()

for event in session.query(Event):
    session.delete(event)
    session.commit()

for folder in session.query(Folder):
	session.delete(folder)
	session.commit()