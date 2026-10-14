import os
from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import RedirectResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from sqlalchemy import Column, Integer, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker
# from passlib.context import CryptContext
from fastapi import Request
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from fastapi import Path

# -----------------------
# Database configuration
# -----------------------

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = os.getenv("POSTGRES_PORT", "5432")
POSTGRES_DB = os.getenv("POSTGRES_DB", "postgres")
POSTGRES_USER = os.getenv("POSTGRES_USER", "postgres")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "postgres")

DATABASE_URL = (
    f"postgresql+psycopg://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

engine = create_engine(DATABASE_URL, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False)
Base = declarative_base()

# -----------------------
# Password hashing setup
# -----------------------
# pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
import bcrypt
# Remove: from passlib.context import CryptContext
# Remove: pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Add these helper functions instead:
def hash_password(password: str) -> str:
    """Hash a password for storing."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a stored password against one provided by user."""
    return bcrypt.checkpw(
        plain_password.encode('utf-8'), 
        hashed_password.encode('utf-8')
    )

# -----------------------
# FastAPI app
# -----------------------
app = FastAPI()
templates = Jinja2Templates(directory="templates")
# app.mount("/static", StaticFiles(directory="static"), name="static")


# @app.get("/")
# def index():
#     return FileResponse("static/index.html")


@app.get("/")
def index(request: Request):
    with SessionLocal() as db:
        # order by stars DESC, then views DESC
        stmt = select(Paste).order_by(Paste.stars.desc(), Paste.views.desc())
        pastes = db.execute(stmt).scalars().all()
    return templates.TemplateResponse(
    request=request,
    name="index.html",
    context={"pastes": pastes},
)

# -----------------------
# Database model
# -----------------------
class Paste(Base):
    __tablename__ = "pastes"

    slug = Column(String(255), primary_key=True)
    content = Column(Text, nullable=False)
    password_hash = Column(String(255), nullable=True)  # optional hashed password

    # NEW FIELDS
    views = Column(Integer, default=0)  # how many times viewed
    stars = Column(Integer, default=0)  # number of stars / likes


Base.metadata.create_all(bind=engine)

# -----------------------
# Routes
# -----------------------
@app.get("/{slug}")
def read_paste(request: Request, slug: str, password: str | None = None):
    if slug in {"static", "favicon.ico"}:
        raise HTTPException(status_code=404)

    slug_lowercase = slug.lower()
    if slug != slug_lowercase:
        return RedirectResponse(f"/{slug_lowercase}")

    with SessionLocal() as db:
        paste = db.get(Paste, slug_lowercase)
    
        if not paste:
            return templates.TemplateResponse(
    request=request,
    name="edit.html",
    context={"slug": slug_lowercase},
)

        content = paste.content
        password_hash = paste.password_hash

        # Check password if required
        if password_hash:
            if not password or not verify_password(password,password_hash): #pwd_context.verify(password, password_hash):
                return templates.TemplateResponse(
    request=request,
    name="password.html",
    context={"slug": slug_lowercase, "error": bool(password)},
)

        # Increment views
        paste.views += 1
        db.commit()  # commit the updated views

    

    return templates.TemplateResponse(
    request=request,
    name="view.html",
    context={"slug": slug_lowercase, "content": content},
)


@app.post("/{slug}")
def create_paste(
    slug: str,
    content: str = Form(...),
    password: str | None = Form(None)  # optional
):
    with SessionLocal() as db:
        if db.get(Paste, slug):
            raise HTTPException(status_code=409, detail="Paste already exists")

        # password_hash = pwd_context.hash(password) if password else None
        password_hash = hash_password(password) if password else None
        db.add(Paste(slug=slug, content=content, password_hash=password_hash))
        db.commit()

    return RedirectResponse(f"/{slug}", status_code=303)



@app.post("/{slug}/star")
def star_paste(slug: str = Path(...)):
    slug_lowercase = slug.lower()
    with SessionLocal() as db:
        paste = db.get(Paste, slug_lowercase)
        if not paste:
            raise HTTPException(status_code=404, detail="Paste not found")
        
        paste.stars += 1
        db.commit()

    return RedirectResponse(f"/{slug_lowercase}", status_code=303)
