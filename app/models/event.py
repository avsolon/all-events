from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, Float, ForeignKey, Table
from sqlalchemy.orm import relationship
from app.database import Base


event_categories = Table(
    "event_categories",
    Base.metadata,
    Column("event_id", Integer, ForeignKey("events.id"), primary_key=True),
    Column("category_id", Integer, ForeignKey("categories.id"), primary_key=True),
)


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)
    source_id = Column(String(50), nullable=False)
    external_id = Column(String(200), nullable=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    url = Column(String(500), nullable=True)
    image_url = Column(String(500), nullable=True)
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=True)
    city = Column(String(100), default="Новосибирск")
    address = Column(String(500), nullable=True)
    venue = Column(String(300), nullable=True)
    price = Column(Float, nullable=True)
    price_text = Column(String(100), nullable=True)
    is_free = Column(Boolean, default=False)
    is_online = Column(Boolean, default=False)
    organizer = Column(String(300), nullable=True)
    contact_phone = Column(String(50), nullable=True)
    contact_email = Column(String(100), nullable=True)
    tags = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)

    categories = relationship("Category", secondary=event_categories, lazy="selectin")

    def __repr__(self):
        return f"<Event {self.title}>"
