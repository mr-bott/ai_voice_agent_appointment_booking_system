"""
MetricsStore tracks and reports latency for the AI processing pipeline.
Provides a simple in-memory store for STT, LLM, and TTS performance data.
"""
class MetricsStore:
    def __init__(self):
        self.stt_latency = 0
        self.llm_latency = 0
        self.tts_latency = 0

    def update_stt(self, val): self.stt_latency = val
    def update_llm(self, val): self.llm_latency = val
    def update_tts(self, val): self.tts_latency = val

    def get_metrics(self):
        return {
            "stt_ms_avg": round(self.stt_latency, 2),
            "llm_ms_avg": round(self.llm_latency, 2),
            "tts_ms_avg": round(self.tts_latency, 2),
            "total_latency_ms_avg": round(self.stt_latency + self.llm_latency + self.tts_latency, 2)
        }

metrics_store = MetricsStore()
