from langchain_openai import ChatOpenAI
import os

# 单例模式：全局 LLM 实例
_llm_instance = None


def get_llm():
    global _llm_instance
    if _llm_instance is None:
        _llm_instance = ChatOpenAI(
            api_key=os.getenv("OPENAI_API_KEY"),
            base_url=os.getenv("OPENAI_API_BASE"),
            model="deepseek-chat",
            temperature=0.7,
            streaming=True  # 启用流式输出
        )
    return _llm_instance
