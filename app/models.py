from sqlalchemy import Column
from sqlalchemy import String
from sqlalchemy import Integer
from sqlalchemy import BigInteger

from database import Base

class File(Base):

    __tablename__ = "files"

    id = Column(String, primary_key=True)

    filename = Column(String)

    storage_key = Column(String)

    size = Column(BigInteger)
