from fastapi import FastAPI, APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import StreamingResponse, FileResponse
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
import bcrypt
import jwt
from emergentintegrations.llm.openai import OpenAISpeechToText, OpenAITextToSpeech
import aiofiles
import tempfile
import io

from database import get_db, init_db, User, Account, Transaction, AuthLog

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# Initialize database
init_db()

# Initialize OpenAI services
EMERGENT_KEY = os.getenv('EMERGENT_LLM_KEY')
stt = OpenAISpeechToText(api_key=EMERGENT_KEY)
tts = OpenAITextToSpeech(api_key=EMERGENT_KEY)

JWT_SECRET = os.getenv('JWT_SECRET')
JWT_ALGORITHM = 'HS256'

app = FastAPI()
api_router = APIRouter(prefix="/api")

# Pydantic Models
class UserCreate(BaseModel):
    name: str
    phone: str
    pin: str
    language_preference: str = "en"

class UserLogin(BaseModel):
    phone: str
    pin: str

class TokenResponse(BaseModel):
    token: str
    user_id: str
    name: str

class AccountResponse(BaseModel):
    account_id: str
    account_number: str
    balance: float
    account_type: str

class TransactionCreate(BaseModel):
    recipient_phone: str
    amount: float
    description: Optional[str] = None

class BillPayment(BaseModel):
    bill_type: str
    amount: float
    description: Optional[str] = None

class TransactionResponse(BaseModel):
    transaction_id: str
    type: str
    amount: float
    recipient: Optional[str]
    description: Optional[str]
    timestamp: datetime
    status: str

class PINChange(BaseModel):
    old_pin: str
    new_pin: str

class IntentRequest(BaseModel):
    text: str

class IntentResponse(BaseModel):
    intent: str
    confidence: float
    entities: dict

# Helper Functions
def hash_pin(pin: str) -> str:
    return bcrypt.hashpw(pin.encode(), bcrypt.gensalt()).decode()

def verify_pin(pin: str, hashed: str) -> bool:
    return bcrypt.checkpw(pin.encode(), hashed.encode())

def create_token(user_id: str) -> str:
    payload = {
        'user_id': user_id,
        'exp': datetime.now(timezone.utc) + timedelta(hours=24)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_token(token: str) -> str:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload['user_id']
    except:
        raise HTTPException(status_code=401, detail="Invalid token")

def recognize_intent(text: str) -> dict:
    text = text.lower()
    
    # Balance check
    if any(word in text for word in ['balance', 'check balance', 'how much', 'account balance']):
        return {'intent': 'check_balance', 'confidence': 0.9, 'entities': {}}
    
    # Transfer money
    if any(word in text for word in ['transfer', 'send money', 'send', 'pay someone']):
        return {'intent': 'transfer_money', 'confidence': 0.9, 'entities': {}}
    
    # Bill payment
    if any(word in text for word in ['pay bill', 'bill payment', 'utility', 'electricity', 'water']):
        return {'intent': 'pay_bill', 'confidence': 0.9, 'entities': {}}
    
    # Mini statement
    if any(word in text for word in ['statement', 'transactions', 'history', 'recent']):
        return {'intent': 'mini_statement', 'confidence': 0.9, 'entities': {}}
    
    # Change PIN
    if any(word in text for word in ['change pin', 'update pin', 'new pin']):
        return {'intent': 'change_pin', 'confidence': 0.9, 'entities': {}}
    
    # Help
    if any(word in text for word in ['help', 'what can you do', 'commands']):
        return {'intent': 'help', 'confidence': 0.9, 'entities': {}}
    
    return {'intent': 'unknown', 'confidence': 0.5, 'entities': {}}

# Routes
@api_router.get("/")
async def root():
    return {"message": "Voice Banking API"}

@api_router.post("/auth/register", response_model=TokenResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    # Check if phone already exists
    existing = db.query(User).filter(User.phone == user_data.phone).first()
    if existing:
        raise HTTPException(status_code=400, detail="Phone number already registered")
    
    # Create user
    user_id = str(uuid.uuid4())
    user = User(
        user_id=user_id,
        name=user_data.name,
        phone=user_data.phone,
        pin_hash=hash_pin(user_data.pin),
        language_preference=user_data.language_preference
    )
    db.add(user)
    
    # Create default account
    account_id = str(uuid.uuid4())
    account_number = f"ACC{str(uuid.uuid4())[:8].upper()}"
    account = Account(
        account_id=account_id,
        user_id=user_id,
        account_number=account_number,
        balance=10000.0,  # Demo balance
        account_type="savings"
    )
    db.add(account)
    
    # Log auth
    log = AuthLog(
        log_id=str(uuid.uuid4()),
        user_id=user_id,
        success=True,
        method="registration"
    )
    db.add(log)
    
    db.commit()
    
    token = create_token(user_id)
    return TokenResponse(token=token, user_id=user_id, name=user_data.name)

@api_router.post("/auth/login", response_model=TokenResponse)
async def login(credentials: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.phone == credentials.phone).first()
    if not user or not verify_pin(credentials.pin, user.pin_hash):
        # Log failed attempt
        if user:
            log = AuthLog(
                log_id=str(uuid.uuid4()),
                user_id=user.user_id,
                success=False,
                method="pin"
            )
            db.add(log)
            db.commit()
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Log successful attempt
    log = AuthLog(
        log_id=str(uuid.uuid4()),
        user_id=user.user_id,
        success=True,
        method="pin"
    )
    db.add(log)
    db.commit()
    
    token = create_token(user.user_id)
    return TokenResponse(token=token, user_id=user.user_id, name=user.name)

@api_router.get("/account", response_model=AccountResponse)
async def get_account(token: str, db: Session = Depends(get_db)):
    user_id = verify_token(token)
    account = db.query(Account).filter(Account.user_id == user_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    return AccountResponse(
        account_id=account.account_id,
        account_number=account.account_number,
        balance=account.balance,
        account_type=account.account_type
    )

@api_router.post("/transaction/transfer", response_model=TransactionResponse)
async def transfer_money(token: str, transfer: TransactionCreate, db: Session = Depends(get_db)):
    user_id = verify_token(token)
    
    # Get sender account
    sender_account = db.query(Account).filter(Account.user_id == user_id).first()
    if not sender_account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    # Check balance
    if sender_account.balance < transfer.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    # Get recipient
    recipient_user = db.query(User).filter(User.phone == transfer.recipient_phone).first()
    if not recipient_user:
        raise HTTPException(status_code=404, detail="Recipient not found")
    
    recipient_account = db.query(Account).filter(Account.user_id == recipient_user.user_id).first()
    
    # Deduct from sender
    sender_account.balance -= transfer.amount
    
    # Add to recipient
    recipient_account.balance += transfer.amount
    
    # Create transaction record
    transaction_id = str(uuid.uuid4())
    transaction = Transaction(
        transaction_id=transaction_id,
        account_id=sender_account.account_id,
        type="debit",
        amount=transfer.amount,
        recipient=recipient_user.name,
        description=transfer.description or f"Transfer to {recipient_user.name}",
        status="completed"
    )
    db.add(transaction)
    
    # Create credit transaction for recipient
    recipient_transaction = Transaction(
        transaction_id=str(uuid.uuid4()),
        account_id=recipient_account.account_id,
        type="credit",
        amount=transfer.amount,
        recipient=db.query(User).filter(User.user_id == user_id).first().name,
        description=transfer.description or f"Received from sender",
        status="completed"
    )
    db.add(recipient_transaction)
    
    db.commit()
    
    return TransactionResponse(
        transaction_id=transaction_id,
        type=transaction.type,
        amount=transaction.amount,
        recipient=transaction.recipient,
        description=transaction.description,
        timestamp=transaction.timestamp,
        status=transaction.status
    )

@api_router.post("/transaction/bill-pay", response_model=TransactionResponse)
async def pay_bill(token: str, bill: BillPayment, db: Session = Depends(get_db)):
    user_id = verify_token(token)
    
    account = db.query(Account).filter(Account.user_id == user_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    if account.balance < bill.amount:
        raise HTTPException(status_code=400, detail="Insufficient balance")
    
    # Deduct amount
    account.balance -= bill.amount
    
    # Create transaction
    transaction_id = str(uuid.uuid4())
    transaction = Transaction(
        transaction_id=transaction_id,
        account_id=account.account_id,
        type="debit",
        amount=bill.amount,
        recipient=bill.bill_type,
        description=bill.description or f"{bill.bill_type} bill payment",
        status="completed"
    )
    db.add(transaction)
    db.commit()
    
    return TransactionResponse(
        transaction_id=transaction_id,
        type=transaction.type,
        amount=transaction.amount,
        recipient=transaction.recipient,
        description=transaction.description,
        timestamp=transaction.timestamp,
        status=transaction.status
    )

@api_router.get("/transactions", response_model=List[TransactionResponse])
async def get_transactions(token: str, limit: int = 10, db: Session = Depends(get_db)):
    user_id = verify_token(token)
    
    account = db.query(Account).filter(Account.user_id == user_id).first()
    if not account:
        raise HTTPException(status_code=404, detail="Account not found")
    
    transactions = db.query(Transaction).filter(
        Transaction.account_id == account.account_id
    ).order_by(Transaction.timestamp.desc()).limit(limit).all()
    
    return [TransactionResponse(
        transaction_id=t.transaction_id,
        type=t.type,
        amount=t.amount,
        recipient=t.recipient,
        description=t.description,
        timestamp=t.timestamp,
        status=t.status
    ) for t in transactions]

@api_router.post("/auth/change-pin")
async def change_pin(token: str, pin_change: PINChange, db: Session = Depends(get_db)):
    user_id = verify_token(token)
    
    user = db.query(User).filter(User.user_id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    if not verify_pin(pin_change.old_pin, user.pin_hash):
        raise HTTPException(status_code=401, detail="Invalid old PIN")
    
    user.pin_hash = hash_pin(pin_change.new_pin)
    db.commit()
    
    return {"message": "PIN changed successfully"}

@api_router.post("/voice/transcribe")
async def transcribe_audio(file: UploadFile = File(...)):
    try:
        # Read file content
        content = await file.read()
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.webm') as temp_file:
            temp_file.write(content)
            temp_file_path = temp_file.name
        
        # Transcribe
        with open(temp_file_path, 'rb') as audio_file:
            response = await stt.transcribe(
                file=audio_file,
                model="whisper-1",
                response_format="json"
            )
        
        # Clean up temp file
        os.unlink(temp_file_path)
        
        return {"text": response.text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

@api_router.post("/voice/synthesize")
async def synthesize_speech(text: str, voice: str = "nova"):
    try:
        audio_bytes = await tts.generate_speech(
            text=text,
            model="tts-1",
            voice=voice,
            response_format="mp3"
        )
        
        return StreamingResponse(
            io.BytesIO(audio_bytes),
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=speech.mp3"}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Speech synthesis failed: {str(e)}")

@api_router.post("/intent/recognize", response_model=IntentResponse)
async def recognize_intent_endpoint(request: IntentRequest):
    result = recognize_intent(request.text)
    return IntentResponse(**result)

app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=os.environ.get('CORS_ORIGINS', '*').split(','),
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)