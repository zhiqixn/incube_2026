import json
import os
from datetime import datetime, timezone
from pathlib import Path

from tools.tool_langgraph import get_reddit_company_news, get_YF_data_tool
from tools.render_bt import render_xml_to_image
from models.model_langgraph import llm, vlm
from configs.agents_config import (
    PLANNER_AGENT_PROMPT,
    GENERATION_AGENT_PROMPT,
    VALIDATION_AGENT_PROMPT,
)
from typing import Literal
from utils.utils_langgraph import (
    State,
    # Output,
    ValidationState,
    PlannerResponse,
)
from utils.minio_client import MinIOClient

from langchain.messages import HumanMessage, SystemMessage
from deepagents import create_deep_agent
from deepagents.backends.filesystem import FilesystemBackend
from langgraph.checkpoint.memory import MemorySaver
from utils.logger import get_logger

logger = get_logger()

# ---------------------------------------------------------------------------
# Project root (used by FilesystemBackend to resolve skill paths)
# ---------------------------------------------------------------------------
PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)

# ---------------------------------------------------------------------------
# Deep agent definitions
# Each agent is created via create_deep_agent with its skills and tools.
# The existing LLM and prompts are reused; skills augment the prompts
# with AgentSkills-compliant SKILL.md content via progressive disclosure.
# ---------------------------------------------------------------------------

planner_agent = create_deep_agent(
    model=llm,
    tools=[],
    system_prompt=PLANNER_AGENT_PROMPT,
    skills=["skills/planner-skill/"],
    backend=FilesystemBackend(root_dir=PROJECT_ROOT),
    checkpointer=MemorySaver(),
)
logger.info("Planner agent created with FilesystemBackend, root_dir=%s", PROJECT_ROOT)
logger.debug("Skills paths: skills/planner-skill/")

generator_agent = llm

# generator_agent = create_deep_agent(
#     model=llm,
#     tools=[get_reddit_company_news, get_YF_data_tool],
#     system_prompt=GENERATION_AGENT_PROMPT,
#     skills=[],
# )

# validator_agent = llm

# validator_agent = create_deep_agent(
#     model=llm,
#     tools=[],
#     system_prompt=VALIDATION_AGENT_PROMPT,
#     skills=[],
# )

# Augment the LLM with schema for structured output
validator_llm = llm.with_structured_output(ValidationState)
planner_llm = llm.with_structured_output(PlannerResponse)


# Nodes
# TODO: Add structured output for output to include explanation
def planner(state: State):
    """Planner that generates a plan for the report"""

    logger.info("Instantiating Planner...")

    if state.get("valid") is False:
        msg_content = (
            f"Previous output was invalid. \n"
            f"Previous output: \n {state['output']} \n"
            f"Feedback: {state['feedback']} \n\n"
            f"Please revise the plan accordingly.\n\n"
            f"Instructions: {state['instructions']}"
        )
    else:
        msg_content = state["instructions"]

    logger.info("Invoking planner agent with message content:\n%s", msg_content)
    result = planner_agent.invoke(
        {
            "messages": [
                HumanMessage(content=msg_content),
            ]
        },
        config={"configurable": {"thread_id": "planner"}},
    )

    raw_content = result["messages"][-1].content
    logger.info("Raw planner output:\n%s", raw_content)
    # Parse structured JSON output from planner
    try:
        parsed = json.loads(raw_content)
        plan_text = parsed.get("plan", raw_content)
        explanation_text = parsed.get("explanation", "")
    except (json.JSONDecodeError, TypeError):
        logger.warning(
            "Planner output is not valid JSON; falling back to raw content as plan"
        )
        plan_text = raw_content
        explanation_text = ""

    logger.info("Plan generated:\n%s", plan_text)
    logger.info("Explanation:\n%s", explanation_text)
    return {"plan": plan_text, "explanation": explanation_text}


def generator(state: State):

    logger.info("Instantiating Generator...")

    generated_response = llm.invoke(
        [
            SystemMessage(content=GENERATION_AGENT_PROMPT),
            HumanMessage(content=state["plan"]),
        ]
    )
    logger.info("Output generated:\n%s", generated_response.content)

    # Render the XML behaviour-tree to a PNG image in the data/ folder
    image_url = ""
    try:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        output_file = f"/data/bt_{timestamp}.png"
        rendered_path = render_xml_to_image(
            xml_text=generated_response.content,
            output_path=output_file,
        )
        logger.info("Behaviour-tree PNG saved to: %s", rendered_path)

        # Upload the rendered PNG to S3 (MinIO) and generate a presigned URL
        try:
            s3_bucket = os.getenv("S3_BUCKET", "bt-images")
            s3_object_name = f"bt_{timestamp}.png"
            minio_client = (
                MinIOClient()
            )  # reads S3_ENDPOINT, S3_ACCESS_KEY, S3_SECRET_KEY from env

            # Ensure the bucket exists before uploading
            if not minio_client.bucket_exists(s3_bucket):
                minio_client.create_bucket(s3_bucket)
                logger.info("Created S3 bucket: %s", s3_bucket)

            minio_client.upload_file(
                bucket_name=s3_bucket,
                object_name=s3_object_name,
                file_path=rendered_path,
            )
            image_url = minio_client.generate_presigned_url(
                bucket_name=s3_bucket,
                object_name=s3_object_name,
                expiration=60,  # 60 minutes
            )
            logger.info(
                "Behaviour-tree PNG uploaded to S3, presigned URL: %s", image_url
            )
        except Exception as s3_exc:
            logger.warning("Failed to upload behaviour-tree PNG to S3: %s", s3_exc)

    except Exception as exc:
        logger.warning("Failed to render behaviour-tree PNG: %s", exc)

    return {"output": generated_response.content, "image_url": image_url}


def validator(state: State):

    logger.info("Instantiating Validator...")
    resource_url = state["resource_url"]
    content = state["output"]

    logger.info(f"Validator got resource URL: {resource_url}")

    validation = validator_llm.invoke(
        [
            SystemMessage(content=VALIDATION_AGENT_PROMPT),
            HumanMessage(
                content=[
                    {"type": "image_url", "image_url": {"url": resource_url}},
                    {"type": "text", "content": content},
                ]
            ),
        ]
    )

    logger.info("Validation result:\n%s", validation["valid"])

    # TODO: Save explanation to local folder if valid is true.
    return {"valid": validation["valid"], "feedback": validation["feedback"]}
