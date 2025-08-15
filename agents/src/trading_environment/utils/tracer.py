import os
import json

from openinference.instrumentation.openai import OpenAIInstrumentor
from openinference.semconv.resource import ResourceAttributes
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExporter
from phoenix.otel import register
from utils.logger import get_logger
from utils.span_processor import AgentSpanProcessor

logger = get_logger()


# Custom exporter to write spans to a local file
class FileSpanExporter(SpanExporter):
    def __init__(self, file_path: str):
        self.file_path = file_path

    def export(self, spans):
        # Write the spans to a local JSON file
        with open(self.file_path, "a") as f:
            for span in spans:
                span_dict = {
                    "trace_id": span.context.trace_id,
                    "span_id": span.context.span_id,
                    "name": span.name,
                    "start_time": span.start_time,
                    "end_time": span.end_time,
                    "attributes": span.attributes,
                    "events": span.events,
                    "status": span.status,
                }
                f.write(json.dumps(span_dict, default=str) + "\n")
        return True

    def shutdown(self):
        pass


def get_phoenix_tracer_provider(project_name: str):
    """
    Obtains the Phoenix tracer provider.

    Returns:
        The tracer provider instance registered by Phoenix.
    """
    otel_endpoint = os.environ.get("PHOENIX_ENDPOINT")
    msg_fwd = AgentSpanProcessor(OTLPSpanExporter(endpoint=otel_endpoint))
    local_file_exporter = FileSpanExporter(file_path="/data/logs/new_vllm.json")
    trace_provider = register(project_name=project_name, endpoint=otel_endpoint)
    trace_provider.add_span_processor(msg_fwd)
    trace_provider.add_span_processor(SimpleSpanProcessor(local_file_exporter))
    OpenAIInstrumentor().instrument(tracer_provider=trace_provider)
    return trace_provider


def set_phoenix_tracer_provider(project_name: str, session_id: str):
    """
    Obtains the Phoenix tracer provider.

    Returns:
        The tracer provider instance registered by Phoenix.
    """
    os.environ["PROJECT_NAME"] = project_name
    otel_endpoint = os.environ.get("PHOENIX_ENDPOINT")
    msg_fwd = AgentSpanProcessor(
        OTLPSpanExporter(endpoint=otel_endpoint), session_id=session_id
    )
    trace_provider = register(project_name=project_name)
    trace_provider.add_span_processor(msg_fwd)
    OpenAIInstrumentor().instrument(tracer_provider=trace_provider)
    return trace_provider


def get_otel_tracer_provider(project_name: str) -> TracerProvider:
    """
    Obtains the OpenTelemetry tracer provider.

    Returns:
        The tracer provider instance registered by OpenTelemetry.
    """
    otel_endpoint = os.environ.get("PHOENIX_ENDPOINT")

    logger.info("OpenTelemetry endpoint: %s", otel_endpoint)

    resource = Resource.create({ResourceAttributes.PROJECT_NAME: project_name})
    tracer_provider = TracerProvider(resource=resource)
    OpenAIInstrumentor().instrument(tracer_provider=tracer_provider)
    span_exporter = OTLPSpanExporter(endpoint=otel_endpoint, headers=None)
    processor = SimpleSpanProcessor(span_exporter)
    tracer_provider.add_span_processor(processor)
    trace.set_tracer_provider(tracer_provider)

    return tracer_provider
