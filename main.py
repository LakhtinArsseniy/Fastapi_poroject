from fastapi import FastAPI, HTTPException, Depends, Request, Cookie, File, Form, UploadFile, Response
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from database import get_db
from project_models import Base, User, Problem, AdminQuestion, engine, async_session

from project_models import User, Base, async_session, engine, Problem, AdminResponse, ServiceRecord, Users_in_telegram

import jwt
from datetime import datetime, timedelta, date
import bcrypt
import secrets
import string
import asyncio

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory='templates')
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

SECRET_KEY = 'kW!8729ew95P$be5j532#8Qlv;3&5tJ3'
ALGORITHM = "HS256"

async def get_session() -> AsyncSession:
    async with async_session() as session:
        yield session

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


def get_current_user(access_token: str = Cookie(None)):
    if not access_token:
        raise HTTPException(status_code=401, detail="Неавторизовано")
    try:
        payload = jwt.decode(access_token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("user_id")
        role = payload.get("role")
        if user_id is None or role is None:
            raise HTTPException(status_code=401, detail="Недійсний токен")
        return (user_id, role)
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Термін дії токена закінчився")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Недійсний токен")

def admin_required(user_data: tuple = Depends(get_current_user)) -> bool:
    user_id, role = user_data
    if role != "admin":
        raise HTTPException(status_code=403, detail="Доступ лише для адміністраторів")
    return True

def generate_code():
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(6))

async def get_problems_for_user(user_id: int, session: AsyncSession):
    result = await session.execute(select(Problem).filter_by(user_id=user_id))
    return result.scalars().all()

async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


@app.get("/")
async def home(request: Request):
    return templates.TemplateResponse('home.html', {'request': request})

@app.get("/register")
async def register_get(request: Request):
    return templates.TemplateResponse('register.html', {'request': request})

@app.post("/register")
async def register_post(request: Request, username: str = Form(), password: str = Form(), email: str = Form(), session: AsyncSession = Depends(get_session)):
    new_user = User(username=username, email=email)
    new_user.set_password(password)
    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)

    tg_code = generate_code()
    user_in_tg = Users_in_telegram(tg_code=tg_code, user_in_site=new_user.id)
    session.add(user_in_tg)
    await session.commit()

    return templates.TemplateResponse('register.html', {'request': request, 'message': 'Ви успішно створили акаунт!', "tg_message": f"Ваш код для Telegram: {tg_code}"})

@app.get("/login")
async def login_get(request: Request, error: str = None):
    return templates.TemplateResponse('login.html', {'request': request, 'error': error})

@app.post("/login")
async def login_post(response: Response, form_data: OAuth2PasswordRequestForm = Depends(), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(User).filter_by(username=form_data.username))
    user = result.scalars().first()
    if not user or not bcrypt.checkpw(form_data.password.encode(), user.password.encode()):
        return RedirectResponse(url="/login/?error=Пароль або логін невірний", status_code=302)

    token_data = {
        "user_id": user.id,
        "role": "admin" if user.is_admin else "user",
        "exp": datetime.utcnow() + timedelta(hours=72)
    }
    token = jwt.encode(token_data, SECRET_KEY, algorithm=ALGORITHM)
    response = RedirectResponse(url="/new_problem", status_code=302)
    response.set_cookie(key="access_token", value=token, httponly=True, max_age=60*60*24*3, samesite="lax")
    return response

@app.get("/logout")
def logout_get():
    response = RedirectResponse(url="/", status_code=302)
    response.delete_cookie("access_token")
    return response

@app.get('/add_my_problem')
async def add_problem_get(request: Request, current_user: tuple = Depends(get_current_user)):
    return templates.TemplateResponse('add_problem.html', {'request': request})

@app.post('/add_my_problem')
async def add_problem_post(
    request: Request, title: str = Form(), description: str = Form(), img: UploadFile = File(None),
    current_user: tuple = Depends(get_current_user), session: AsyncSession = Depends(get_session)
):
    img_path = None
    if img and getattr(img, "filename", None):
        file_location = f"user_problem_image/{img.filename}"
        with open('static/' + file_location, "wb+") as f:
            f.write(await img.read())
        img_path = file_location

    new_problem = Problem(title=title, description=description, user_id=current_user[0], image_url=img_path)
    session.add(new_problem)
    await session.commit()
    await session.refresh(new_problem)

    return templates.TemplateResponse('add_problem.html', {'request': request, 'message': f'Проблема "{title}" записана!'})

@app.get("/my_problems")
async def my_problems_page(request: Request, current_user: tuple = Depends(get_current_user), session: AsyncSession = Depends(get_session)):
    problems = await get_problems_for_user(current_user[0], session)
    return templates.TemplateResponse("my_problems.html", {"request": request, "problems": problems, "current_user": current_user})
    
@app.get("/new_problem")
async def new_problem_get(request: Request):
    return templates.TemplateResponse("new_problem.html", {"request": request})

@app.post('/new_problem')
async def create_new_problem(
    request: Request,
    title: str = Form(...),
    description: str = Form(...),
    image_url: str = Form(None),
    current_user: tuple = Depends(get_current_user),
    session: AsyncSession = Depends(get_session)
):
    new_problem = Problem(
        title=title,
        description=description,
        image_url=image_url,
        status='Нова',
        user_id=current_user[0]
    )
    session.add(new_problem)
    await session.commit()
    await session.refresh(new_problem)

    return RedirectResponse(url="/my_problems", status_code=302)

   

@app.post("/delete_problem")
async def delete_problem(id: int = Form(...), session: AsyncSession = Depends(get_session)):
    result = await session.execute(select(Problem).where(Problem.id == id))
    problem = result.scalars().first()
    if problem:
        await session.delete(problem)
        await session.commit()
    return RedirectResponse(url="/my_problems", status_code=303)


@app.get("/edit_problem", response_class=HTMLResponse)
async def edit_problem_get(request: Request, id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Problem).where(Problem.id == id))
    problem = result.scalar_one_or_none()
    if not problem:
        return RedirectResponse("/my_problems", status_code=303)
    return templates.TemplateResponse("edit_problem.html", {"request": request, "problem": problem})

@app.post("/edit_problem")
async def edit_problem_post(
    id: int = Form(...),
    title: str = Form(...),
    description: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    result = await db.execute(select(Problem).where(Problem.id == id))
    problem = result.scalar_one_or_none()
    if not problem:
        return RedirectResponse("/my_problems", status_code=303)

    problem.title = title
    problem.description = description
    await db.commit()
    return RedirectResponse("/my_problems", status_code=303)

@app.get("/send_message_to_admin")
async def send_message_to_admin_form(request: Request, problem_id: int):
    return templates.TemplateResponse("send_message_to_admin.html", {"request": request, "problem_id": problem_id})

@app.post("/send_message_to_admin")
async def send_message_to_admin(problem_id: int = Form(...), message: str = Form(...)):
    return RedirectResponse(url="/my_problems", status_code=303)