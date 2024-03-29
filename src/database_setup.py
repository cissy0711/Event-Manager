from sqlalchemy import Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
 
Base = declarative_base()

class User(Base):
    __tablename__ = 'user'
    
    id = Column(Integer, primary_key = True)
    name = Column(String(250),nullable = False)
    email = Column(String(250),nullable= False)
    picture = Column(String(250))

class Folder(Base):
    __tablename__ = 'folder'
   
    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    user_id = Column(Integer,ForeignKey('user.id'))
    user = relationship(User)

    @property
    def serialize(self):
       """Return object data in easily serializeable format"""
       return {
           'name'         : self.name,
           'id'           : self.id,
       }
 
class Event(Base):
    __tablename__ = 'event'


    name = Column(String(80), nullable = False)
    id = Column(Integer, primary_key = True)
    description = Column(String(250))
    time = Column(String(8))
    location = Column(String(250))
    folder_id = Column(Integer,ForeignKey('folder.id'))
    folder = relationship(Folder)
    user_id = Column(Integer,ForeignKey('user.id'))
    user = relationship(User)


    @property
    def serialize(self):
       """Return object data in easily serializeable format"""
       return {
           'name'         : self.name,
           'description'         : self.description,
           'id'         : self.id,
           'time'         : self.time,
           'location'         : self.location,
       }



engine = create_engine('sqlite:///event_manager.db')
 

Base.metadata.create_all(engine)
