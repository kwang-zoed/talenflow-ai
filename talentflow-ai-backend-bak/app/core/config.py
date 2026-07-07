from pathlib import Path

from pydantic_settings import BaseSettings
from dotenv import load_dotenv
import os

_BACKEND_ROOT = Path(__file__).resolve().parents[2]
_REPO_ROOT = _BACKEND_ROOT.parent

# 先读仓库根 .env（Docker Compose env_file），再读 backend-bak/.env（本地开发密钥优先）
load_dotenv(_REPO_ROOT / ".env")
load_dotenv(_BACKEND_ROOT / ".env", override=True)


class Settings(BaseSettings):
    # 项目配置
    PROJECT_NAME: str = "TalentFlow AI"
    API_V1_STR: str = "/api/v1"

    # 数据库配置
    DATABASE_URL: str = os.getenv("MYSQL_SERVER", "localhost")
    MYSQL_USER: str = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD: str = os.getenv("MYSQL_PASSWORD", "123456")
    MYSQL_DATABASE: str = os.getenv("MYSQL_DATABASE", "dandelion_tribe")

    # 向量数据库配置
    FAISS_DB_PATH: str = os.getenv("FAISS_DB_PATH","./FAISS_DB")

    PROJIECT_ROOT: str = r"C:\Users\kzd\Desktop\talentflow-ai\talentflow-ai-backend-bak"

    # 安全配置
    SECRET_KEY: str = os.getenv("SECRET_KEY", "your_secret_key")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    REFRESH_TOKEN_EXPIRE_DAYS: int = int(os.getenv("REFRESH_TOKEN_EXPIRE_DAYS", "7"))
    API_KEY: str = os.getenv("OPENAI_API_KEY", "")

    # LangSmith（监控 LangGraph / LangChain 调用链）
    # https://smith.langchain.com → Settings → API Keys
    LANGSMITH_TRACING_ENABLED: bool = os.getenv("LANGSMITH_TRACING", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    LANGSMITH_API_KEY: str = os.getenv("LANGSMITH_API_KEY", os.getenv("LANGCHAIN_API_KEY", ""))
    LANGSMITH_PROJECT: str = os.getenv("LANGSMITH_PROJECT", os.getenv("LANGCHAIN_PROJECT", "talentflow-smart-apply"))
    LANGSMITH_ENDPOINT: str = os.getenv("LANGSMITH_ENDPOINT", "")

    REDIS_URL: str = os.getenv("REDIS_URL", "redis://:123456@localhost:6379/0")
    MCP_SERVER_URL: str = os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8002/mcp")
    # LangGraph 检查点: auto | redis | sqlite | memory
    # auto: 优先 Redis Stack；若仅有普通 Redis（无 RediSearch）则回退 SQLite
    CHECKPOINTER_BACKEND: str = os.getenv("CHECKPOINTER_BACKEND", "sqlite")
    SQLITE_CHECKPOINT_PATH: str = os.getenv(
        "SQLITE_CHECKPOINT_PATH",
        os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "data", "langgraph_checkpoints.sqlite"),
    )
    # 为 false 时启动快、接口立即可用；为 true 时在后台预热 embedding/LangGraph（reranker 仅在 Celery Worker 中按需加载）
    PRELOAD_MODELS_ON_STARTUP: bool = os.getenv("PRELOAD_MODELS_ON_STARTUP", "false").lower() in (
        "1",
        "true",
        "yes",
    )
    # 智能投递是否在优化简历 / 求职信后暂停，等待用户确认（LangGraph interrupt）
    SMART_APPLY_HUMAN_REVIEW: bool = os.getenv("SMART_APPLY_HUMAN_REVIEW", "true").lower() in (
        "1",
        "true",
        "yes",
    )
    # api | worker；未设置时由 reranker 模块按进程命令行自动判断
    APP_PROCESS_ROLE: str = os.getenv("APP_PROCESS_ROLE", "")
    RERANKER_LOAD_TIMEOUT: int = int(os.getenv("RERANKER_LOAD_TIMEOUT", "90"))

    AMAP_WEB_KEY: str = os.getenv("AMAP_WEB_KEY", "")
    AMAP_GEOCODE_ENABLED: bool = os.getenv("AMAP_GEOCODE_ENABLED", "true").lower() in (
        "1", "true", "yes",
    )

    @property
    def SQLALCHEMY_DATABASE_URI(self) -> str:
        return f"mysql+pymysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.DATABASE_URL}/{self.MYSQL_DATABASE}"


settings = Settings()
