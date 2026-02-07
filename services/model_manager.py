import threading
from collections import OrderedDict

from config import MODELS

MAX_CACHED_MODELS = 2


class ModelManager:
    """Thread-safe lazy model loader with LRU eviction."""

    def __init__(self):
        self._cache: OrderedDict[str, object] = OrderedDict()
        self._lock = threading.Lock()

    def get_model(self, model_name: str):
        """Return a loaded model, loading it if necessary."""
        with self._lock:
            if model_name in self._cache:
                self._cache.move_to_end(model_name)
                return self._cache[model_name]

        # Load outside the lock (can be slow)
        model_cfg = MODELS[model_name]
        from mlx_audio.tts.utils import load_model
        model = load_model(model_cfg["repo_id"])

        with self._lock:
            # Evict LRU if over capacity
            while len(self._cache) >= MAX_CACHED_MODELS:
                evicted_name, evicted_model = self._cache.popitem(last=False)
                del evicted_model
            self._cache[model_name] = model
            return model

    def is_loaded(self, model_name: str) -> bool:
        with self._lock:
            return model_name in self._cache


# Singleton
manager = ModelManager()
