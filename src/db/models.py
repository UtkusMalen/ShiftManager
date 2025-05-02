import enum
from sqlalchemy import Column, Integer, String, ForeignKey, Enum, DateTime, func
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, relationship, foreign


class Base(AsyncAttrs, DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, unique=True, nullable=False)
    username = Column(String, unique=True, nullable=True)

    shifts = relationship("Shift", primaryjoin="User.user_id == foreign(Shift.user_id)", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, user_id={self.user_id}, username={self.username})>"

class ShiftStatus(enum.Enum):
    FORMING = "forming"
    ACTIVE = "active"
    COMPLETED = "completed"

class Shift(Base):
    __tablename__ = "shifts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False, index=True)
    status = Column(Enum(ShiftStatus), nullable=False, default=ShiftStatus.FORMING)
    start_time = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", foreign_keys=[user_id], back_populates="shifts")

    def __repr__(self):
        return f"<Shift(id={self.id}, user_id={self.user_id}, status={self.status}, start_time={self.start_time})>"