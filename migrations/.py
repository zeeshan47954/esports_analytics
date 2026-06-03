from sqlalchemy import create_engine, text,Column,String,UUID
from sqlalchemy.orm import sessionmaker,declarative_base
import os
from dotenv import load_dotenv

import uuid

load_dotenv()
url=os.getenv("fullpath")
engine=create_engine(url)
Base=declarative_base()

class Matches(Base):
    __tablename__="matches"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    created_by=Column(String,nullable=False)



