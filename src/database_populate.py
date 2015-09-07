from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database_setup import Folder, Base, Event, User

engine = create_engine('sqlite:///event_manager.db')
# Bind the engine to the metadata of the Base class so that the
# declaratives can be accessed through a DBSession instance
Base.metadata.bind = engine

DBSession = sessionmaker(bind=engine)
# A DBSession() instance establishes all conversations with the database
# and represents a "staging zone" for all the objects loaded into the
# database session object. Any change made against the objects in the
# session won't be persisted into the database until you call
# session.commit(). If you're not happy about the changes, you can
# revert all of them back to the last commit by calling
# session.rollback()
session = DBSession()


# Create dummy user
User1 = User(name="Robo Barista", email="tinnyTim@udacity.com",
             picture='https://pbs.twimg.com/profile_images/2671170543/18debd694829ed78203a5a36dd364160_400x400.png')
session.add(User1)
session.commit()

# Menu for UrbanBurger
folder1 = Folder(user_id=1, name="Academic")

session.add(folder1)
session.commit()



event1 = Event(user_id=1, name="Quantum Optics seminar", description="have fun with a bunch of physicists",
                     time="7:00am", location="China", folder=folder1)

session.add(event1)
session.commit()

event2 = Event(user_id=1, name="Comuter Science seminar", description="have fun with a bunch of computer scientists",
                     time="8:00am", location="USA", folder=folder1)

session.add(event2)
session.commit()

event3 = Event(user_id=1, name="Mathematics seminar", description="have fun with a bunch of mathamatists",
                     time="9:00am", location="Japan", folder=folder1)

session.add(event3)
session.commit()

event4 = Event(user_id=1, name="Chemistry seminar", description="have fun with a bunch of chemists",
                     time="10:00am", location="UK", folder=folder1)

session.add(event4)
session.commit()





# Menu for Super Stir Fry
folder2 = Folder(user_id=1, name="Sport")

session.add(folder2)
session.commit()


event1 = Event(user_id=1, name="Football", description="play football",
                     time="9:00am", location="China", folder=folder2)

session.add(event1)
session.commit()

event2 = Event(user_id=1, name="Basketball",
                     description=" play basketball", 
                     time="3:00pm", location="USA", folder=folder2)
session.add(event2)
session.commit()



print "added menu items!"