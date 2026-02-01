from sqlalchemy import create_engine, Column, String, Float, Integer, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

load_dotenv()

# Use SQLite for simplicity (file-based SQL database)
DATABASE_URL = "sqlite:///./voice_banking.db"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class User(Base):
    __tablename__ = "users"
    
    user_id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    phone = Column(String, unique=True, nullable=False, index=True)
    pin_hash = Column(String, nullable=False)
    language_preference = Column(String, default="en")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    accounts = relationship("Account", back_populates="user")
    auth_logs = relationship("AuthLog", back_populates="user")

class Account(Base):
    __tablename__ = "accounts"
    
    account_id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    account_number = Column(String, unique=True, nullable=False, index=True)
    balance = Column(Float, default=0.0)
    account_type = Column(String, default="savings")
    
    user = relationship("User", back_populates="accounts")
    transactions = relationship("Transaction", back_populates="account")

class Transaction(Base):
    __tablename__ = "transactions"
    
    transaction_id = Column(String, primary_key=True, index=True)
    account_id = Column(String, ForeignKey("accounts.account_id"), nullable=False)
    type = Column(String, nullable=False)  # debit/credit
    amount = Column(Float, nullable=False)
    recipient = Column(String)
    description = Column(String)
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    status = Column(String, default="completed")
    
    account = relationship("Account", back_populates="transactions")

class AuthLog(Base):
    __tablename__ = "auth_logs"
    
    log_id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.user_id"), nullable=False)
    attempt_time = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    success = Column(Boolean, nullable=False)
    method = Column(String, default="pin")
    
    user = relationship("User", back_populates="auth_logs")

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def init_db():
    Base.metadata.create_all(bind=engine)