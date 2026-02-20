from django.apps import AppConfig


class RagConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "rag"

    def ready(self):
        # Preload LLM at server startup, not on first request
        from rag.services.llm_service import llm_service
        llm_service.load_model("Qwen/Qwen2-0.5B-Instruct")
