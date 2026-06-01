import json
import logging
from typing import Any, Dict

from fastmcp import Client
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI
from langgraph.types import interrupt

from app.agents.resume_format import (
    RESUME_JSON_SCHEMA,
    format_resume_text,
    normalize_resume_data,
    parse_resume_json,
    resolve_candidate_name,
    strip_optimized_name_suffix,
)
from app.agents.state import AgentState
from app.core.config import settings

logger = logging.getLogger(__name__)

MCP_SERVER_URL = settings.MCP_SERVER_URL

llm = ChatOpenAI(
    api_key=settings.API_KEY,
    base_url="https://api.deepseek.com/v1",
    model="deepseek-chat",
    temperature=0.7,
)


def _parse_mcp_result(result) -> Dict[str, Any]:
    if not result or not result.content:
        raise ValueError("MCP返回结果为空")

    content_block = result.content[0]
    if hasattr(content_block, "text"):
        text_data = content_block.text
    else:
        text_data = str(content_block)

    return json.loads(text_data)


async def fetch_resume_node(state: AgentState, config: RunnableConfig):
    """节点 1: 获取简历"""
    if state.get("skip_generation") and state.get("resume_id"):
        try:
            async with Client(MCP_SERVER_URL) as client:
                result = await client.call_tool(
                    "get_resume_by_id",
                    {"resume_id": state["resume_id"]},
                )
            data = _parse_mcp_result(result)
            if not data.get("error"):
                logger.info(
                    "[fetch_resume_node] 复用模式，使用缓存简历 ID %s",
                    state["resume_id"],
                )
                return {"resume_id": state["resume_id"]}
        except Exception as e:
            logger.warning("[fetch_resume_node] 校验复用简历失败: %s", e)

        logger.warning(
            "[fetch_resume_node] 复用简历 ID %s 不存在，转为完整 AI 生成流程",
            state.get("resume_id"),
        )
        return {"skip_generation": False, "resume_id": None}

    logger.info("[fetch_resume_node] 通过 MCP 获取用户 %s 的简历", state["user_id"])
    try:
        async with Client(MCP_SERVER_URL) as client:
            result = await client.call_tool(
                "get_resume_content",
                {"user_id": state["user_id"]},
            )

        data = _parse_mcp_result(result)
        if data.get("error"):
            return {"error_message": data["error"]}

        original_resume = {
            "name": strip_optimized_name_suffix(data.get("name") or ""),
            "phone": data.get("phone"),
            "email": data.get("email"),
            "title": data.get("title"),
            "education": data.get("education"),
            "experience_years": data.get("experience_years"),
            "skills": data.get("skills") or [],
            "summary": data.get("summary"),
            "work_experience": data.get("work_experience"),
            "project_experience": data.get("project_experience"),
        }

        return {
            "resume_content": data["content"],
            "original_resume": original_resume,
            "applicant_name": strip_optimized_name_suffix(data.get("name") or "求职者"),
            "resume_id": data.get("id"),
        }
    except Exception as e:
        logger.error("fetch_resume_node 失败: %s", e, exc_info=True)
        return {"error_message": f"MCP 调用失败: {str(e)}"}


async def optimize_resume_node(state: AgentState):
    """节点 2: AI 优化简历，输出结构化 JSON"""
    logger.info("[optimize_resume_node] 正在使用 AI 优化简历")

    if state.get("error_message"):
        return {}

    optimize_prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            """
            你是一位资深 HR 专家。请根据目标职位描述，优化用户的简历内容。

            要求：
            1. 重点润色 work_experience 和 project_experience，使用 STAR 法则。
            2. 自然植入职位描述中的关键词。
            3. 量化成果，突出数据。
            4. 不要编造用户没有的经历。
            5. summary 只写个人简介，不要把工作经历或项目经验写进 summary。
            6. name 必须与原始简历完全一致，禁止修改姓名，禁止添加 _Optimized 等任何后缀。
            7. title 可润色为更贴合岗位的意向职位表述；投递职位标识由系统自动写入 title，无需在 name 中区分版本。
            8. 保留原始简历中的电话、邮箱等真实信息，仅做润色。
            9. 必须只输出一个 JSON 对象，不要输出 Markdown、解释语或代码块标记。

            JSON 字段说明：
            {schema}
            """,
        ),
        (
            "human",
            "原始姓名（JSON 的 name 必须与下列完全一致，禁止增删改）：{legal_name}\n\n"
            "目标职位：\n{job_desc}\n\n原始简历：\n{resume}",
        ),
    ])

    chain = optimize_prompt | llm

    try:
        original = state.get("original_resume") or {}
        legal_name = resolve_candidate_name(original=original, explicit_original_name=state.get("applicant_name"))
        response = await chain.ainvoke({
            "legal_name": legal_name,
            "job_desc": state["job_description"],
            "resume": state["resume_content"],
            "schema": RESUME_JSON_SCHEMA,
        })
        parsed = parse_resume_json(response.content)
        optimized = normalize_resume_data(parsed, state.get("original_resume"))

        return {
            "optimized_resume": optimized,
            "applicant_name": optimized.get("name") or state.get("applicant_name"),
        }
    except Exception as e:
        logger.error("简历优化失败: %s", e, exc_info=True)
        return {"error_message": f"简历优化失败: {str(e)}"}


async def save_optimized_resume_node(state: AgentState):
    """节点 3: 保存优化后的简历"""
    logger.info("[save_optimized_resume_node] 正在保存优化后的简历")

    if state.get("error_message"):
        return {}

    optimized = dict(state.get("optimized_resume") or {})
    if not optimized:
        return {"error_message": "没有可保存的优化简历"}

    original = state.get("original_resume") or {}
    legal_name = resolve_candidate_name(
        optimized,
        original,
        state.get("applicant_name"),
    )
    optimized["name"] = legal_name

    try:
        async with Client(MCP_SERVER_URL) as client:
            result = await client.call_tool(
                "save_optimized_resume",
                {
                    "user_id": state["user_id"],
                    "job_id": state["job_id"],
                    "resume_data": optimized,
                    "original_name": legal_name,
                },
            )

        data = _parse_mcp_result(result)
        if data.get("status") == "success":
            new_resume_id = data["data"]["new_resume_id"]
            return {"resume_id": new_resume_id, "resume_saved_in_run": True}

        return {"error_message": data.get("message", "保存优化简历失败")}
    except Exception as e:
        logger.error("保存优化简历异常: %s", e, exc_info=True)
        return {"error_message": f"保存异常: {str(e)}"}


async def generate_letter_node(state: AgentState):
    """节点 4: 生成求职信"""
    logger.info("[generate_letter_node] 正在生成求职信")

    if state.get("error_message"):
        return {}

    prompt = ChatPromptTemplate.from_messages([
        (
            "system",
            "你是一名求职专家。根据简历和职位描述写一封简短有力的求职信。"
            "落款处使用姓名: {applicant_name}。",
        ),
        ("human", "简历:\n{resume}\n\n职位:\n{job_desc}\n\n求职信:"),
    ])

    chain = prompt | llm

    try:
        optimized = state.get("optimized_resume")
        if optimized:
            final_resume = format_resume_text(optimized)
        else:
            final_resume = state.get("resume_content", "")

        response = await chain.ainvoke({
            "resume": final_resume,
            "job_desc": state["job_description"],
            "applicant_name": state.get("applicant_name", "求职者"),
        })
        return {"cover_letter": response.content}
    except Exception as e:
        logger.error("生成求职信失败: %s", e, exc_info=True)
        return {"error_message": f"生成求职信失败: {str(e)}"}


async def review_optimized_resume_node(state: AgentState):
    """人工审核：确认 AI 优化后的简历（LangGraph interrupt）。"""
    if state.get("error_message") or state.get("skip_generation"):
        return {}
    if not state.get("optimized_resume"):
        return {}
    if not settings.SMART_APPLY_HUMAN_REVIEW:
        return {}

    logger.info("[review_optimized_resume_node] 等待用户确认优化简历")
    user_input = interrupt({
        "review_type": "optimized_resume",
        "message": "请确认或修改 AI 优化后的简历，确认后将保存并生成求职信",
    })
    if isinstance(user_input, dict) and user_input.get("optimized_resume"):
        optimized = normalize_resume_data(
            user_input["optimized_resume"],
            state.get("original_resume"),
        )
        return {
            "optimized_resume": optimized,
            "applicant_name": optimized.get("name") or state.get("applicant_name"),
        }
    return {}


async def review_cover_letter_node(state: AgentState):
    """人工审核：确认求职信（LangGraph interrupt）。"""
    if state.get("error_message"):
        return {}
    if not state.get("cover_letter"):
        return {}
    if not settings.SMART_APPLY_HUMAN_REVIEW:
        return {}

    logger.info("[review_cover_letter_node] 等待用户确认求职信")
    user_input = interrupt({
        "review_type": "cover_letter",
        "message": "请确认或修改求职信，确认后将提交投递",
    })
    if isinstance(user_input, dict) and user_input.get("cover_letter"):
        return {"cover_letter": str(user_input["cover_letter"]).strip()}
    return {}


async def _rollback_optimized_resume(state: AgentState):
    """投递失败时删除本次新生成的优化简历，避免脏数据。"""
    if state.get("skip_generation") or not state.get("resume_saved_in_run"):
        return

    resume_id = state.get("resume_id")
    if not resume_id:
        return

    try:
        async with Client(MCP_SERVER_URL) as client:
            await client.call_tool(
                "delete_optimized_resume",
                {"resume_id": resume_id},
            )
        logger.info("[rollback] 已回滚优化简历 ID %s", resume_id)
    except Exception as e:
        logger.warning("[rollback] 回滚优化简历失败: %s", e)


async def save_record_node(state: AgentState):
    """节点 5: 保存投递记录"""
    logger.info("[save_record_node] 正在保存投递记录")

    if state.get("error_message"):
        return {}

    try:
        cover_letter = state.get("cover_letter")
        if not cover_letter:
            cover_letter = (
                "您好，我对该职位非常感兴趣，这是我的最新简历，"
                "期待与您进一步沟通。"
            )
            logger.warning("[save_record_node] 未找到求职信，使用默认文本")

        async with Client(MCP_SERVER_URL) as client:
            result = await client.call_tool(
                "create_application_record",
                {
                    "user_id": state["user_id"],
                    "job_id": str(state["job_id"]),
                    "cover_letter": cover_letter,
                    "resume_id": state.get("resume_id"),
                },
            )

        data = _parse_mcp_result(result)
        application_id = data.get("application_id") or data.get("id")
        if not application_id:
            error_msg = data.get("message", "创建投递记录失败")
            await _rollback_optimized_resume(state)
            return {"error_message": error_msg}

        return {"application_id": application_id}
    except Exception as e:
        logger.error("保存投递记录失败: %s", e, exc_info=True)
        await _rollback_optimized_resume(state)
        return {"error_message": f"保存记录异常: {str(e)}"}
