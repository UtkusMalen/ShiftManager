import enum
from sqlalchemy import Column, Integer, String, ForeignKey, Enum, DateTime, func, Float, BigInteger
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, relationship, foreign


class Base(AsyncAttrs, DeclarativeBase):
    pass

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, unique=True, nullable=False)
    username = Column(String, unique=True, nullable=True)

    shifts = relationship("Shift", primaryjoin="User.user_id == foreign(Shift.user_id)", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, user_id={self.user_id}, username={self.username})>"

class ShiftStatus(enum.Enum):
    FORMING = "forming"
    ACTIVE = "active"
    COMPLETED = "completed"

class ShiftEventType(enum.Enum):
    START_SHIFT = "start_shift"
    COMPLETE_SHIFT = "complete_shift"
    ADD_ORDER = "add_order"
    UPDATE_ORDER = "update_order"
    ADD_EXPENSE = "add_expense"
    ADD_TIPS = "add_tip"
    ADD_MILEAGE = "add_mileage"
    UPDATE_INITIAL_DATA = "update_initial_data"

class Shift(Base):
    __tablename__ = "shifts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(BigInteger, ForeignKey("users.user_id"), nullable=False, index=True)
    status = Column(Enum(ShiftStatus), nullable=False, default=ShiftStatus.FORMING)
    orders_count = Column(Integer, nullable=False, default=0)
    total_mileage = Column(Float, nullable=False, default=0.0)
    total_tips = Column(Float, nullable=False, default=0.0)
    total_expenses = Column(Float, nullable=False, default=0.0)
    rate = Column(Float, nullable=False, default=0)
    order_rate = Column(Float, nullable=False, default=0)
    mileage_rate = Column(Float, nullable=False, default=0)
    start_time = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=True)

    user = relationship("User", foreign_keys=[user_id], back_populates="shifts")

    events = relationship(
        "ShiftEvent",
        back_populates="shift",
        cascade="all, delete-orphan",
        order_by="ShiftEvent.timestamp"
    )

    def __repr__(self):
        return f"<Shift(id={self.id}, user_id={self.user_id}, status={self.status}, orders_count={self.orders_count}, total_mileage={self.total_mileage}, total_tips={self.total_tips}, total_expenses={self.total_expenses}, rate={self.rate}, oreder_rate={self.order_rate}, mileage_rate={self.mileage_rate}, start_time={self.start_time})>"

class ShiftEvent(Base):
    __tablename__ = "shift_events"

    id = Column(Integer, primary_key=True, index=True)
    shift_id = Column(Integer, ForeignKey("shifts.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(Enum(ShiftEventType), nullable=False)
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    details = Column(JSONB, nullable=True)

    shift = relationship("Shift", foreign_keys=[shift_id], back_populates="events")

    def __repr__(self):
        return f"<ShiftEvent(id={self.id}, shift_id={self.shift_id}, type={self.event_type}, details={self.details}, timestamp={self.timestamp})>"