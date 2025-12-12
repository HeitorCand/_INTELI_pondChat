# core/vectorstore.py
import faiss
import numpy as np
import pickle
from pathlib import Path
from typing import List, Dict

class FaissIndex:
    def __init__(self, dim:int, index_path:Path, meta_path:Path):
        self.dim = dim
        self.index_path = Path(index_path)
        self.meta_path = Path(meta_path)
        self.index = None
        self.meta = []
        if self.index_path.exists() and self.meta_path.exists():
            self._load()

    def _load(self):
        self.index = faiss.read_index(str(self.index_path))
        with open(self.meta_path, "rb") as f:
            self.meta = pickle.load(f)

    def save(self):
        faiss.write_index(self.index, str(self.index_path))
        with open(self.meta_path, "wb") as f:
            pickle.dump(self.meta, f)

    def build(self, vectors:List[List[float]], metas:List[Dict]):
        arr = np.array(vectors).astype("float32")
        self.index = faiss.IndexFlatL2(self.dim)
        self.index.add(arr)
        self.meta = metas
        self.save()

    def add(self, vector, meta):
        if self.index is None:
            self.index = faiss.IndexFlatL2(len(vector))
        self.index.add(np.array([vector]).astype("float32"))
        self.meta.append(meta)
        self.save()

    def query(self, vector, k=5):
        if self.index is None:
            return []
        D, I = self.index.search(np.array([vector]).astype("float32"), k)
        results = []
        for dist, idx in zip(D[0], I[0]):
            if idx < 0 or idx >= len(self.meta): continue
            results.append({"score": float(dist), "meta": self.meta[idx]})
        return results
