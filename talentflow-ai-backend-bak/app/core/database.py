from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import (
    create_async_engine, 
    AsyncSession, 
    async_sessionmaker
)
import os
import asyncio

from app.core.config import settings

# 与 config.Settings.SQLALCHEMY_DATABASE_URI 保持一致（避免 MYSQL_HOST / MYSQL_SERVER 两套变量）
DATABASE_URL = settings.SQLALCHEMY_DATABASE_URI
if "?" not in DATABASE_URL:
    DATABASE_URL = f"{DATABASE_URL}?charset=utf8mb4"

engine = create_engine(
    DATABASE_URL,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ========== ========== 异步数据库引擎（新增） ========== ==========
ASYNC_DATABASE_URL = DATABASE_URL.replace("pymysql", "asyncmy")
print(f"[database.py] 异步数据库 URL: {ASYNC_DATABASE_URL}")

async_engine = create_async_engine(
    ASYNC_DATABASE_URL,
    echo=False,
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    pool_recycle=3600
)

AsyncSessionLocal = async_sessionmaker(
    async_engine, 
    class_=AsyncSession, 
    expire_on_commit=False
)


async def get_async_db():
    print(f"[get_async_db] 线程/协程 ID: {id(asyncio.current_task())}")
    async with AsyncSessionLocal() as session:
        try:
            print(f"[get_async_db] 异步 Session 创建成功: {id(session)}")
            yield session
            await session.commit()
            print(f"[get_async_db] Session commit 成功")
        except Exception as e:
            await session.rollback()
            print(f"[get_async_db] Session 异常回滚: {e}")
            raise
        finally:
            await session.close()
            print(f"[get_async_db] Session 关闭成功")

# 确保根目录下有data目录（用于存放SQLite数据库文件）
os.makedirs("./data", exist_ok=True)

# 定义SQLite的连接参数
# check_same_thread=False 用于在多线程环境下使用SQLite数据库
connect_args = {"check_same_thread": False}

def create_db_and_tables():
    # SQLModel需要在元数据中注册所有模型，得先导入所有模型
    # 可能会因为执行顺序问题，导致模型/表未注册
    from app import models
    SQLModel.metadata.create_all(engine)
    print("数据库和表创建完成")
