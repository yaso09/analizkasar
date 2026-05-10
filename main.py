#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════╗
║         ANALİZKASAR v0.1              ║
║   Iterative Web Research & LLM Synthesis     ║
║           Yasir Eymen KAYABAŞI               ║
╚══════════════════════════════════════════════╝
"""

import argparse
import json
import os
import re
import sys
import time
import threading
from datetime import datetime, timedelta
from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from docx import Document

# ─────────────────────────────────────────────────────────────────────────────
# RICH
# ─────────────────────────────────────────────────────────────────────────────
try:
    from rich.console import Console
    from rich.progress import (
        BarColumn,
        MofNCompleteColumn,
        Progress,
        SpinnerColumn,
        TaskProgressColumn,
        TextColumn,
        TimeElapsedColumn,
        TimeRemainingColumn,
    )
    from rich.panel import Panel
    from rich.table import Table
    from rich.rule import Rule
    from rich.align import Align
    from rich import box
except ImportError:
    print("❌ 'rich' paketi bulunamadı: pip install rich")
    sys.exit(1)

console = Console(highlight=False)

# ─────────────────────────────────────────────────────────────────────────────
# BACKEND REGISTRY
# ─────────────────────────────────────────────────────────────────────────────
BACKENDS = ["ollama", "openai", "anthropic", "groq", "lmstudio", "mistral"]

DEFAULT_MODELS = {
    "ollama":    "gemma3:12b",
    "openai":    "gpt-4o",
    "anthropic": "claude-opus-4-5",
    "groq":      "llama-3.3-70b-versatile",
    "lmstudio":  "local-model",
    "mistral":   "mistral-large-latest",
}

BACKEND_COLORS = {
    "ollama":    "bright_green",
    "openai":    "bright_cyan",
    "anthropic": "bright_magenta",
    "groq":      "bright_yellow",
    "lmstudio":  "bright_blue",
    "mistral":   "orange1",
}

OUTPUT_FORMATS = ["pdf", "docx", "md", "txt", "json"]

# ─────────────────────────────────────────────────────────────────────────────
# LOGGER
# ─────────────────────────────────────────────────────────────────────────────

class Logger:
    LEVELS = {
        "DEBUG":   ("dim white",       "◦"),
        "INFO":    ("bright_white",    "·"),
        "SUCCESS": ("bright_green",    "✓"),
        "WARNING": ("bright_yellow",   "⚠"),
        "ERROR":   ("bright_red",      "✗"),
        "STEP":    ("bright_cyan",     "→"),
        "LLM":     ("bright_magenta",  "🧠"),
        "FETCH":   ("steel_blue1",     "🌐"),
        "LINK":    ("yellow",          "🔗"),
        "SAVE":    ("bright_green",    "💾"),
        "STAT":    ("bright_white",    "📊"),
    }

    def __init__(self, quiet=False, verbose=False):
        self.quiet   = quiet
        self.verbose = verbose
        self._lock   = threading.Lock()

    def _ts(self):
        return datetime.now().strftime("%H:%M:%S")

    def _emit(self, level, msg, indent=0):
        if self.quiet and level != "ERROR":
            return
        if level == "DEBUG" and not self.verbose:
            return
        color, icon = self.LEVELS.get(level, ("white", "·"))
        pad = "  " * indent
        with self._lock:
            console.print(
                f"[dim]{self._ts()}[/dim] [{color}]{icon}[/{color}] {pad}{msg}",
                highlight=False,
            )

    def debug(self,   m, i=0): self._emit("DEBUG",   m, i)
    def info(self,    m, i=0): self._emit("INFO",    m, i)
    def success(self, m, i=0): self._emit("SUCCESS", m, i)
    def warning(self, m, i=0): self._emit("WARNING", m, i)
    def error(self,   m, i=0): self._emit("ERROR",   m, i)
    def step(self,    m, i=0): self._emit("STEP",    m, i)
    def llm(self,     m, i=0): self._emit("LLM",     m, i)
    def fetch(self,   m, i=0): self._emit("FETCH",   m, i)
    def link(self,    m, i=0): self._emit("LINK",    m, i)
    def save(self,    m, i=0): self._emit("SAVE",    m, i)
    def stat(self,    m, i=0): self._emit("STAT",    m, i)

    def rule(self, title="", style="bright_black"):
        if not self.quiet:
            console.print(Rule(title, style=style))

    def section(self, title, style="bold bright_cyan"):
        if not self.quiet:
            console.print()
            console.print(Rule(f"[{style}] {title} [/{style}]", style="bright_black"))

log: Logger


# ─────────────────────────────────────────────────────────────────────────────
# İSTATİSTİK
# ─────────────────────────────────────────────────────────────────────────────

class Stats:
    def __init__(self):
        self.start_time        = time.time()
        self.total_fetched     = 0
        self.total_failed      = 0
        self.total_chars       = 0
        self.total_new_urls    = 0
        self.total_linked_urls = 0
        self.batches_done      = 0
        self.llm_calls         = 0
        self.llm_total_secs    = 0.0
        self.fetch_total_secs  = 0.0
        self.batch_stats: list[dict] = []

    def elapsed(self):
        return str(timedelta(seconds=int(time.time() - self.start_time)))

    def print_batch_table(self):
        if not self.batch_stats:
            return
        t = Table(
            title="📋 Batch Detayları",
            box=box.SIMPLE_HEAVY,
            border_style="bright_black",
            header_style="bold bright_white",
        )
        t.add_column("Batch",      justify="center", style="cyan",           width=7)
        t.add_column("Fetch ✓",    justify="right",  style="bright_green",   width=8)
        t.add_column("Fetch ✗",    justify="right",  style="bright_red",     width=8)
        t.add_column("Karakter",   justify="right",  style="white",          width=12)
        t.add_column("Link req.",  justify="right",  style="yellow",         width=10)
        t.add_column("Yeni URL",   justify="right",  style="bright_yellow",  width=10)
        t.add_column("LLM süresi", justify="right",  style="bright_magenta", width=12)
        t.add_column("Süre",       justify="right",  style="bright_black",   width=10)
        for r in self.batch_stats:
            t.add_row(
                str(r["batch"]),
                str(r["fetched"]),
                str(r["failed"]),
                f"{r['chars']:,}",
                str(r["link_reqs"]),
                str(r["new_urls"]),
                f"{r['llm_secs']:.1f}s",
                f"{r['secs']:.1f}s",
            )
        console.print()
        console.print(t)

    def print_summary(self):
        t = Table(
            title="📊 Çalışma Özeti",
            box=box.ROUNDED,
            border_style="bright_black",
            header_style="bold cyan",
        )
        t.add_column("Metrik", style="bright_white", min_width=32)
        t.add_column("Değer",  style="bright_green", justify="right", min_width=14)
        avg_llm   = self.llm_total_secs / self.llm_calls if self.llm_calls else 0
        avg_fetch = self.fetch_total_secs / max(self.total_fetched, 1)
        rows = [
            ("Toplam süre",                    self.elapsed()),
            ("Tamamlanan batch",               str(self.batches_done)),
            ("Başarılı fetch",                 str(self.total_fetched)),
            ("Başarısız fetch",                f"[bright_red]{self.total_failed}[/bright_red]"),
            ("İşlenen toplam karakter",        f"{self.total_chars:,}"),
            ("Model tarafından keşfedilen URL",str(self.total_new_urls)),
            ("Model tarafından talep edilen bağlantı", str(self.total_linked_urls)),
            ("LLM çağrı sayısı",              str(self.llm_calls)),
            ("Ort. LLM yanıt süresi",         f"{avg_llm:.1f}s"),
            ("Ort. fetch süresi",              f"{avg_fetch:.2f}s"),
        ]
        for k, v in rows:
            t.add_row(k, v)
        console.print()
        console.print(t)


@dataclass
class UserIntent:
    """
    Kullanıcının araştırma niyetini yapısal olarak tutar.
    Tüm LLM çağrılarına enjekte edilerek modelin odağını sabitler.
    """
    topic:       str   # Araştırma konusu / hedef
    output_type: str   # Çıktı türü (akademik makale, teknik rapor vb.)
    audience:    str   # Hedef kitle
    focus:       str   # Odak noktaları / öncelikler
    constraints: str   # Kaçınılması gerekenler / kısıtlar

    def is_empty(self) -> bool:
        return not self.topic.strip()

    def to_prompt_block(self) -> str:
        """LLM prompt'una eklenecek kullanıcı niyet bloğu üretir."""
        lines = [
            "KULLANICI NİYETİ (tüm çıktı bu hedefi karşılamak için üretilir):",
            f"  Konu / Hedef   : {self.topic}",
            f"  Çıktı Türü     : {self.output_type}",
        ]
        if self.audience.strip():
            lines.append(f"  Hedef Kitle    : {self.audience}")
        if self.focus.strip():
            lines.append(f"  Odak Noktaları : {self.focus}")
        if self.constraints.strip():
            lines.append(f"  Kısıtlar       : {self.constraints}")
        return "\n".join(lines)


_OUTPUT_TYPES = [
    ("Akademik Makale",   "Hakemli dergi standardında, bölümlü, atıflı akademik metin"),
    ("Teknik Rapor",      "Mühendislik odaklı, mimari ve implementasyon detaylarıyla"),
    ("Yönetici Özeti",    "Karar verici için kısa, bulgular ve öneriler ağırlıklı"),
    ("Kapsamlı Analiz",   "Derinlemesine inceleme, karşılaştırma ve eleştirel değerlendirme"),
    ("Literatür Taraması","Kaynak karşılaştırması ve alan haritası odaklı"),
]


def collect_user_intent(preset_topic: str = "") -> UserIntent:
    """
    Kullanıcıdan araştırma niyetini interaktif olarak toplar.
    preset_topic verilmişse konu sorusu atlanır (--prompt bayrağı için).
    """
    console.print()
    console.print(Panel(
        "[bold bright_white]Araştırma ajanı başlamadan önce ne istediğini anlayalım.[/bold bright_white]\n"
        "[dim]Boş bırakabileceğin alanlar var — sadece Enter'a basarak geçebilirsin.[/dim]",
        title="[bold bright_cyan]🎯 Araştırma Niyeti[/bold bright_cyan]",
        border_style="bright_cyan",
        padding=(0, 2),
    ))
    console.print()

    # ── 1. Konu ──────────────────────────────────────────────────────────────
    if preset_topic:
        topic = preset_topic.strip()
        console.print(
            f"  [bright_cyan]Konu:[/bright_cyan] [bright_white]{topic}[/bright_white] "
            f"[dim](--prompt ile belirlendi)[/dim]"
        )
        console.print()
    else:
        console.print(Panel(
            "[bold]Bu araştırmadan ne elde etmek istiyorsun?[/bold]\n"
            "[dim]Örnek: \"Transformer modelleri ile protein yapı tahmini\", "
            "\"GPT-4 ve Claude'un kod üretme karşılaştırması\"[/dim]",
            title="[bold bright_yellow]1 / 5  Araştırma Konusu[/bold bright_yellow]",
            border_style="bright_yellow",
            padding=(0, 2),
        ))
        try:
            topic = input("  ✏  Konu / Hedef: ").strip()
        except EOFError:
            topic = ""
        if not topic:
            topic = "Genel araştırma"
        console.print()

    # ── 2. Çıktı Türü ────────────────────────────────────────────────────────
    console.print(Panel(
        "[bold]Sonuç nasıl bir belge olsun?[/bold]\n\n"
        + "\n".join(
            f"  [bright_yellow]{i+1}[/bright_yellow]. [bright_white]{name}[/bright_white]"
            f"  [dim]— {desc}[/dim]"
            for i, (name, desc) in enumerate(_OUTPUT_TYPES)
        ),
        title="[bold bright_yellow]2 / 5  Çıktı Türü[/bold bright_yellow]",
        border_style="bright_yellow",
        padding=(0, 2),
    ))
    try:
        choice_raw = input(f"  ✏  Seçim (1–{len(_OUTPUT_TYPES)}, varsayılan 1): ").strip()
        choice_idx = int(choice_raw) - 1 if choice_raw.isdigit() else 0
        choice_idx = max(0, min(choice_idx, len(_OUTPUT_TYPES) - 1))
    except (EOFError, ValueError):
        choice_idx = 0
    output_type = _OUTPUT_TYPES[choice_idx][0]
    console.print(f"  [bright_green]✓[/bright_green] {output_type}")
    console.print()

    # ── 3. Hedef Kitle ───────────────────────────────────────────────────────
    console.print(Panel(
        "[bold]Bu raporu kim okuyacak?[/bold]\n"
        "[dim]Örnek: \"Doktora öğrencileri\", \"Yazılım mühendisleri\", "
        "\"C-level yöneticiler\", \"Genel kitle\"[/dim]",
        title="[bold bright_yellow]3 / 5  Hedef Kitle[/bold bright_yellow]",
        border_style="bright_yellow",
        padding=(0, 2),
    ))
    try:
        audience = input("  ✏  Hedef kitle (boş bırakabilirsin): ").strip()
    except EOFError:
        audience = ""
    console.print()

    # ── 4. Odak Noktaları ────────────────────────────────────────────────────
    console.print(Panel(
        "[bold]Özellikle vurgulanmasını istediğin konular var mı?[/bold]\n"
        "[dim]Örnek: \"Performans karşılaştırması ve benchmark sonuçları\", "
        "\"Güvenlik açıkları\", \"Maliyet analizi\"[/dim]",
        title="[bold bright_yellow]4 / 5  Odak Noktaları[/bold bright_yellow]",
        border_style="bright_yellow",
        padding=(0, 2),
    ))
    try:
        focus = input("  ✏  Odak noktaları (boş bırakabilirsin): ").strip()
    except EOFError:
        focus = ""
    console.print()

    # ── 5. Kısıtlar ──────────────────────────────────────────────────────────
    console.print(Panel(
        "[bold]Raporda olmamasını istediğin bir şey var mı?[/bold]\n"
        "[dim]Örnek: \"Ticari ürün reklamı yapılmasın\", "
        "\"Python dışı kod örneği verilmesin\", \"Spekülasyon yapılmasın\"[/dim]",
        title="[bold bright_yellow]5 / 5  Kısıtlar[/bold bright_yellow]",
        border_style="bright_yellow",
        padding=(0, 2),
    ))
    try:
        constraints = input("  ✏  Kısıtlar (boş bırakabilirsin): ").strip()
    except EOFError:
        constraints = ""
    console.print()

    intent = UserIntent(
        topic=topic,
        output_type=output_type,
        audience=audience,
        focus=focus,
        constraints=constraints,
    )

    # ── Özet paneli ──────────────────────────────────────────────────────────
    summary_lines = [
        f"[bright_cyan]Konu:[/bright_cyan]        {intent.topic}",
        f"[bright_cyan]Çıktı Türü:[/bright_cyan]  {intent.output_type}",
    ]
    if intent.audience:
        summary_lines.append(f"[bright_cyan]Kitle:[/bright_cyan]       {intent.audience}")
    if intent.focus:
        summary_lines.append(f"[bright_cyan]Odak:[/bright_cyan]        {intent.focus}")
    if intent.constraints:
        summary_lines.append(f"[bright_cyan]Kısıtlar:[/bright_cyan]    {intent.constraints}")

    console.print(Panel(
        "\n".join(summary_lines),
        title="[bold bright_green]✅ Araştırma Niyeti Kaydedildi[/bold bright_green]",
        border_style="bright_green",
        padding=(0, 2),
    ))
    console.print()

    return intent


# ─────────────────────────────────────────────────────────────────────────────
# RAG: VEKTÖR DEPOSU + CHUNK YÖNETİMİ
# ─────────────────────────────────────────────────────────────────────────────

class RAGStore:
    """
    Backend-agnostic RAG (Retrieval-Augmented Generation) deposu.

    Öncelik sırası:
      1. sentence-transformers  → semantik embedding (cosine benzerliği)
      2. numpy TF-IDF           → kelime frekansı tabanlı geri dönüş

    Kullanım:
        store = RAGStore(chunk_size=1000, chunk_overlap=200, top_k=5)
        store.add_document(url, text)     # belgeyi chunk'la ve göm
        results = store.query("sorgu")    # ilgili chunk'ları al
    """

    def __init__(
        self,
        chunk_size: int       = 1000,
        chunk_overlap: int    = 200,
        embedding_model: str  = "all-MiniLM-L6-v2",
        top_k: int            = 5,
    ):
        self.chunk_size     = chunk_size
        self.chunk_overlap  = chunk_overlap
        self.top_k          = top_k
        self._chunks: list[dict] = []   # [{"url": str, "text": str}]
        self._embeddings    = None      # np.ndarray (N, dim)  — lazy
        self._dirty         = False     # yeni chunk eklendiyse True
        self._use_sbert     = False
        self._encoder       = None
        self._np            = None

        # ── Embedding backend seçimi ─────────────────────────────────────────
        try:
            import numpy as np
            from sentence_transformers import SentenceTransformer
            self._encoder   = SentenceTransformer(embedding_model)
            self._use_sbert = True
            self._np        = np
            log.success(
                f"[bright_green]RAG:[/bright_green] sentence-transformers hazır "
                f"[dim]({embedding_model})[/dim]"
            )
        except ImportError:
            try:
                import numpy as np
                self._np = np
                log.warning(
                    "[bright_yellow]RAG:[/bright_yellow] sentence-transformers bulunamadı "
                    "— TF-IDF (numpy) geri dönüşü aktif. "
                    "[dim]pip install sentence-transformers[/dim]"
                )
            except ImportError:
                log.error(
                    "RAG için en az numpy gereklidir: pip install numpy"
                )
                raise SystemExit("❌ pip install numpy")

        # TF-IDF yardımcı alanları
        self._vocab: list[str] = []
        self._v2i:  dict[str, int] = {}
        self._idf:  dict[str, float] = {}

    # ── Yardımcı: metin parçalama ────────────────────────────────────────────

    def _split(self, text: str) -> list[str]:
        """Metni örtüşen chunk'lara böl."""
        pieces, start = [], 0
        while start < len(text):
            end = min(start + self.chunk_size, len(text))
            pieces.append(text[start:end])
            if end == len(text):
                break
            start += self.chunk_size - self.chunk_overlap
        return pieces

    # ── Belge ekleme ─────────────────────────────────────────────────────────

    def add_document(self, url: str, text: str) -> int:
        """Belgeyi chunk'la, kaydet. Eklenen chunk sayısını döndürür."""
        if not text.strip():
            return 0
        for piece in self._split(text):
            self._chunks.append({"url": url, "text": piece})
        self._dirty = True          # embedding yeniden hesaplanmalı
        return len(self._split(text))

    # ── TF-IDF embedding (fallback) ──────────────────────────────────────────

    @staticmethod
    def _tokenize(text: str) -> list[str]:
        return re.findall(r'\w+', text.lower())

    def _build_tfidf(self, texts: list[str]):
        import math
        from collections import Counter
        N = len(texts)
        tok_lists = [self._tokenize(t) for t in texts]
        df: dict[str, int] = {}
        for toks in tok_lists:
            for w in set(toks):
                df[w] = df.get(w, 0) + 1
        self._idf  = {w: math.log((N + 1) / (v + 1)) for w, v in df.items()}
        self._vocab = list(self._idf.keys())
        self._v2i   = {v: i for i, v in enumerate(self._vocab)}
        np = self._np
        mat = np.zeros((N, len(self._vocab)), dtype=np.float32)
        for i, toks in enumerate(tok_lists):
            tf = Counter(toks)
            total = len(toks) or 1
            for w, c in tf.items():
                if w in self._v2i:
                    mat[i, self._v2i[w]] = (c / total) * self._idf[w]
        return mat

    def _tfidf_vec(self, query: str):
        from collections import Counter
        np = self._np
        toks = self._tokenize(query)
        tf   = Counter(toks)
        total = len(toks) or 1
        vec  = np.zeros(len(self._vocab), dtype=np.float32)
        for w, c in tf.items():
            if w in self._v2i:
                vec[self._v2i[w]] = (c / total) * self._idf.get(w, 0.0)
        return vec

    # ── Embedding inşası (lazy) ───────────────────────────────────────────────

    def _build_embeddings(self):
        if not self._chunks:
            return
        texts = [c["text"] for c in self._chunks]
        if self._use_sbert:
            self._embeddings = self._encoder.encode(
                texts, show_progress_bar=False, batch_size=64
            )
        else:
            self._embeddings = self._build_tfidf(texts)
        self._dirty = False

    # ── Sorgulama ────────────────────────────────────────────────────────────

    def query(self, query_text: str, top_k: int | None = None) -> list[dict]:
        """
        En ilgili chunk'ları döndürür.
        Her sonuç: {"url": str, "text": str, "score": float}
        """
        k = top_k or self.top_k
        if not self._chunks:
            return []
        if self._dirty or self._embeddings is None:
            self._build_embeddings()

        np = self._np
        if self._use_sbert:
            q_vec = self._encoder.encode([query_text])[0]
        else:
            q_vec = self._tfidf_vec(query_text)

        q_norm = np.linalg.norm(q_vec)
        if q_norm == 0:
            return []

        mat   = self._embeddings
        norms = np.linalg.norm(mat, axis=1, keepdims=True)
        norms = np.where(norms == 0, 1.0, norms)
        sims  = (mat / norms) @ (q_vec / q_norm)

        top_idx = np.argsort(sims)[::-1][:k]
        return [
            {
                "url":   self._chunks[int(i)]["url"],
                "text":  self._chunks[int(i)]["text"],
                "score": float(sims[int(i)]),
            }
            for i in top_idx
        ]

    def format_context(self, results: list[dict]) -> str:
        """Retrieval sonuçlarını LLM prompt'una eklenecek metin bloğuna çevir."""
        if not results:
            return ""
        parts = []
        for r in results:
            score_str = f"{r['score']:.3f}"
            parts.append(
                f"[RAG CHUNK | benzerlik={score_str} | kaynak={r['url']}]\n{r['text']}"
            )
        return "\n\n".join(parts)

    def rag_stats(self) -> dict:
        return {
            "chunk_sayisi":   len(self._chunks),
            "embedding_tipi": "sentence-transformers" if self._use_sbert else "TF-IDF",
        }


# ─────────────────────────────────────────────────────────────────────────────
# LLM BACKENDS
# ─────────────────────────────────────────────────────────────────────────────


# ─────────────────────────────────────────────────────────────────────────────
# STREAMING HELPERS
# ─────────────────────────────────────────────────────────────────────────────

_THINK_WIDTH = 88  # düşünce bloğu panel genişliği


def _stream_to_console(
    token_iter,          # iterator: str token'ları yield eder
    thinking_iter=None,  # iterator (opsiyonel): thinking token'ları yield eder
) -> str:
    """
    Token'ları canlı olarak terminale basar.
    - thinking_iter varsa önce dim bir panel içinde düşünce akışı gösterilir.
    - Sonra ana yanıt token token yazılır.
    Tüm yanıt metni (thinking hariç) döndürülür.
    """
    from rich.live import Live
    from rich.text import Text

    # ── Düşünce akışı ────────────────────────────────────────────────────────
    if thinking_iter is not None:
        thought_buf = []
        with Live(console=console, refresh_per_second=12, transient=True) as live:
            for chunk in thinking_iter:
                thought_buf.append(chunk)
                preview = "".join(thought_buf)
                # Son ~800 karakter göster
                display = preview[-800:] if len(preview) > 800 else preview
                panel_text = Text(display, style="dim italic")
                from rich.panel import Panel as _Panel
                live.update(
                    _Panel(
                        panel_text,
                        title="[dim]🧠 Düşünce akışı[/dim]",
                        border_style="bright_black",
                        width=_THINK_WIDTH,
                    )
                )
        # Düşünce tamamlandı — özet satır
        thought_full = "".join(thought_buf)
        console.print(
            f"  [dim]🧠 Düşünce: {len(thought_full):,} karakter[/dim]"
        )

    # ── Ana yanıt akışı ───────────────────────────────────────────────────────
    result_chunks = []
    console.print()
    for chunk in token_iter:
        result_chunks.append(chunk)
        console.print(chunk, end="", highlight=False)
    console.print()   # satır sonu

    return "".join(result_chunks)


# ─────────────────────────────────────────────────────────────────────────────
# BACKEND STREAMING IMPLEMENTATIONS
# ─────────────────────────────────────────────────────────────────────────────

def ask_ollama(system: str, user: str, model: str, host: str) -> str:
    try:
        import ollama as _ol
        client = _ol.Client(host=host)

        def _tokens():
            for part in client.chat(
                model=model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
                stream=True,
            ):
                yield part["message"]["content"]

        return _stream_to_console(_tokens())
    except ImportError:
        raise SystemExit("❌ pip install ollama")


def ask_openai(system: str, user: str, model: str, api_key: str, base_url) -> str:
    try:
        from openai import OpenAI
        client = OpenAI(api_key=api_key, base_url=base_url or None)
        stream = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            stream=True,
        )

        def _tokens():
            for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    yield delta

        return _stream_to_console(_tokens())
    except ImportError:
        raise SystemExit("❌ pip install openai")


def ask_anthropic(system: str, user: str, model: str, api_key: str) -> str:
    """
    Anthropic API'si system parametresini ayrı alır (messages dışında).
    Extended thinking destekli modellerde thinking akışı gösterilir.
    """
    try:
        import anthropic as _ant
        client = _ant.Anthropic(api_key=api_key)

        thinking_chunks: list[str] = []
        text_chunks:     list[str] = []

        try:
            with client.messages.stream(
                model=model,
                max_tokens=16000,
                system=system,
                thinking={"type": "enabled", "budget_tokens": 10000},
                messages=[{"role": "user", "content": user}],
            ) as stream:
                from rich.live import Live
                from rich.text import Text
                from rich.panel import Panel as _Panel

                thinking_active = False

                with Live(console=console, refresh_per_second=12,
                          transient=True) as live:
                    for event in stream:
                        etype = type(event).__name__

                        if etype == "ContentBlockStart":
                            block_type = getattr(event.content_block, "type", "")
                            thinking_active = block_type == "thinking"

                        elif etype == "ContentBlockDelta":
                            delta = event.delta
                            dtype = getattr(delta, "type", "")

                            if dtype == "thinking_delta":
                                tok = getattr(delta, "thinking", "")
                                thinking_chunks.append(tok)
                                preview = "".join(thinking_chunks)[-800:]
                                live.update(_Panel(
                                    Text(preview, style="dim italic"),
                                    title="[dim]🧠 Düşünce akışı[/dim]",
                                    border_style="bright_black",
                                    width=_THINK_WIDTH,
                                ))

                            elif dtype == "text_delta":
                                tok = getattr(delta, "text", "")
                                text_chunks.append(tok)
                                live.update(_Panel(
                                    Text("".join(thinking_chunks)[-400:],
                                         style="dim italic"),
                                    title=(
                                        f"[dim]🧠 Düşünce tamamlandı · "
                                        f"{len(''.join(thinking_chunks)):,} kar[/dim]"
                                    ),
                                    border_style="bright_black",
                                    width=_THINK_WIDTH,
                                ))

                        elif etype == "ContentBlockStop":
                            thinking_active = False

                if thinking_chunks:
                    console.print(
                        f"  [dim]🧠 Düşünce: "
                        f"{len(''.join(thinking_chunks)):,} karakter[/dim]"
                    )

                console.print()
                for tok in text_chunks:
                    console.print(tok, end="", highlight=False)
                console.print()
                return "".join(text_chunks)

        except Exception as thinking_err:
            err_str = str(thinking_err).lower()
            if "thinking" in err_str or "unknown" in err_str or "invalid" in err_str:
                log.warning(
                    "[dim]Bu model extended-thinking desteklemiyor "
                    "— düz streaming ile devam ediliyor.[/dim]"
                )
            else:
                raise

        with client.messages.stream(
            model=model,
            max_tokens=4096,
            system=system,
            messages=[{"role": "user", "content": user}],
        ) as stream:
            def _tokens():
                for tok in stream.text_stream:
                    yield tok
            return _stream_to_console(_tokens())

    except ImportError:
        raise SystemExit("❌ pip install anthropic")


def ask_groq(system: str, user: str, model: str, api_key: str) -> str:
    try:
        from groq import Groq
        client = Groq(api_key=api_key)
        stream = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user",   "content": user},
            ],
            stream=True,
        )

        def _tokens():
            for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    yield delta

        return _stream_to_console(_tokens())
    except ImportError:
        raise SystemExit("❌ pip install groq")


def ask_lmstudio(system: str, user: str, model: str, base_url: str) -> str:
    import json as _json

    def _tokens():
        with requests.post(
            f"{base_url.rstrip('/')}/v1/chat/completions",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
                "stream": True,
            },
            headers={"Content-Type": "application/json"},
            timeout=120,
            stream=True,
        ) as resp:
            resp.raise_for_status()
            for raw_line in resp.iter_lines():
                if not raw_line:
                    continue
                line = raw_line.decode("utf-8") if isinstance(raw_line, bytes) else raw_line
                if line.startswith("data:"):
                    line = line[5:].strip()
                if line in ("", "[DONE]"):
                    continue
                try:
                    data  = _json.loads(line)
                    delta = data["choices"][0].get("delta", {}).get("content") or ""
                    if delta:
                        yield delta
                except (_json.JSONDecodeError, KeyError):
                    continue

    return _stream_to_console(_tokens())


# ─────────────────────────────────────────────────────────────────────────────
# BACKEND DISPATCHER
# ─────────────────────────────────────────────────────────────────────────────

def _call_backend(system: str, user: str, backend: str, model: str, cfg: dict) -> str:
    if backend == "ollama":
        return ask_ollama(system, user, model,
                          cfg.get("ollama_host", "http://localhost:11434"))
    elif backend == "openai":
        key = cfg.get("openai_api_key") or os.getenv("OPENAI_API_KEY", "")
        if not key: raise SystemExit("❌ OPENAI_API_KEY eksik")
        return ask_openai(system, user, model, key, cfg.get("openai_base_url"))
    elif backend == "anthropic":
        key = cfg.get("anthropic_api_key") or os.getenv("ANTHROPIC_API_KEY", "")
        if not key: raise SystemExit("❌ ANTHROPIC_API_KEY eksik")
        return ask_anthropic(system, user, model, key)
    elif backend == "groq":
        key = cfg.get("groq_api_key") or os.getenv("GROQ_API_KEY", "")
        if not key: raise SystemExit("❌ GROQ_API_KEY eksik")
        return ask_groq(system, user, model, key)
    elif backend == "lmstudio":
        return ask_lmstudio(system, user, model,
                            cfg.get("lmstudio_url", "http://localhost:1234"))
    raise SystemExit(f"❌ Bilinmeyen backend: {backend}")


def ask_llm(prompt_tuple: tuple[str, str], cfg: dict, stats) -> str:
    system, user = prompt_tuple
    t0 = time.time()
    bc = BACKEND_COLORS.get(cfg["backend"], "white")
    log.llm(
        f"[{bc}]{cfg['backend']}[/{bc}] · "
        f"[dim]{cfg['model']}[/dim] · "
        f"system [dim]{len(system):,} kar[/dim]  "
        f"user [dim]{len(user):,} kar[/dim]",
        i=1,
    )
    console.rule("[dim bright_black]── akış başlıyor ──[/dim bright_black]")

    result = _call_backend(system, user, cfg["backend"], cfg["model"], cfg)

    elapsed = time.time() - t0
    stats.llm_calls      += 1
    stats.llm_total_secs += elapsed

    console.rule("[dim bright_black]── akış bitti ──[/dim bright_black]")
    log.llm(
        f"Yanıt: [bright_green]{len(result):,} karakter[/bright_green]  "
        f"[dim]({elapsed:.1f}s)[/dim]",
        i=1,
    )
    return result


# ─────────────────────────────────────────────────────────────────────────────
# WEB SCRAPER + BAĞLANTI ÇIKARICI
# ─────────────────────────────────────────────────────────────────────────────

def fetch_url(url, timeout=15, max_chars=20_000, stats=None):
    """(content, elapsed, char_count, page_links) döndürür."""
    t0 = time.time()
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Analizkasar/0.1)"}
        resp = requests.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        soup = BeautifulSoup(resp.text, "html.parser")

        base = f"{urlparse(url).scheme}://{urlparse(url).netloc}"
        page_links = []
        for a in soup.find_all("a", href=True):
            href = a["href"].strip()
            if href.startswith("http"):
                page_links.append(href)
            elif href.startswith("/"):
                page_links.append(base + href)

        for tag in soup(["script", "style", "noscript"]):
            tag.decompose()
        text    = soup.get_text(separator="\n", strip=True)[:max_chars]
        elapsed = time.time() - t0
        if stats:
            stats.total_fetched    += 1
            stats.total_chars      += len(text)
            stats.fetch_total_secs += elapsed
        return text, elapsed, len(text), page_links
    except Exception:
        elapsed = time.time() - t0
        if stats:
            stats.total_failed += 1
        return "", elapsed, 0, []

def extract_urls_from_text(text):
    return re.findall(r'https?://[^\s)"\'<>]+', text)

def parse_link_requests(llm_output):
    return re.findall(r'LINK_REQUEST:\s*(https?://[^\s\n]+)', llm_output)


# ─────────────────────────────────────────────────────────────────────────────
# EXPORT: PDF (Markdown → ReportLab)
# ─────────────────────────────────────────────────────────────────────────────

def _escape_rl(text: str) -> str:
    """ReportLab Paragraph XML için özel karakterleri kaçır."""
    return (
        text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
    )

def _inline_md(text: str) -> str:
    """**bold**, *italic*, `code` → ReportLab XML tagları."""
    # bold + italic
    text = re.sub(r'\*\*\*(.+?)\*\*\*', r'<b><i>\1</i></b>', text)
    # bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text)
    text = re.sub(r'__(.+?)__',     r'<b>\1</b>', text)
    # italic
    text = re.sub(r'\*(.+?)\*',     r'<i>\1</i>', text)
    text = re.sub(r'_(.+?)_',       r'<i>\1</i>', text)
    # inline code
    text = re.sub(r'`(.+?)`',       r'<font name="Courier">\1</font>', text)
    return text

def save_pdf(md_text: str, path: str) -> None:
    """
    Markdown metnini ayrıştırıp ReportLab Platypus ile PDF'e dönüştürür.

    Desteklenen öğeler:
        - # / ## / ### başlıklar
        - Paragraflar
        - **bold**, *italic*, `code` satır içi biçimlendirme
        - - / * / + ile madde listeleri
        - 1. 2. ile numaralı listeler
        - ``` kod blokları
        - --- yatay çizgi
        - > alıntı blokları
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
    from reportlab.lib import colors
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, HRFlowable,
        Preformatted, ListFlowable, ListItem,
    )
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont

    # ── Sayfa yapısı ──────────────────────────────────────────────────────────
    doc = SimpleDocTemplate(
        path,
        pagesize=A4,
        leftMargin=2.5 * cm,
        rightMargin=2.5 * cm,
        topMargin=2.5 * cm,
        bottomMargin=2.5 * cm,
        title="Analizkasar Raporu",
        author="Analizkasar v0.1",
    )

    # ── Stil paleti ───────────────────────────────────────────────────────────
    base = getSampleStyleSheet()

    def _ps(name, parent="Normal", **kw):
        return ParagraphStyle(name, parent=base[parent], **kw)

    styles = {
        "h1": _ps("RA_H1", "Heading1",
                  fontSize=20, leading=26, spaceAfter=10,
                  textColor=colors.HexColor("#1a1a2e")),
        "h2": _ps("RA_H2", "Heading2",
                  fontSize=15, leading=20, spaceAfter=7,
                  textColor=colors.HexColor("#16213e")),
        "h3": _ps("RA_H3", "Heading3",
                  fontSize=12, leading=16, spaceAfter=5,
                  textColor=colors.HexColor("#0f3460")),
        "body": _ps("RA_Body",
                    fontSize=10, leading=15, spaceAfter=6,
                    alignment=TA_JUSTIFY),
        "code": _ps("RA_Code",
                    fontName="Courier", fontSize=8.5, leading=12,
                    backColor=colors.HexColor("#f4f4f4"),
                    leftIndent=12, rightIndent=12,
                    spaceBefore=4, spaceAfter=4,
                    borderColor=colors.HexColor("#cccccc"),
                    borderWidth=0.5, borderPadding=6),
        "quote": _ps("RA_Quote",
                     fontSize=10, leading=14, leftIndent=18,
                     textColor=colors.HexColor("#555555"),
                     borderColor=colors.HexColor("#cccccc"),
                     borderWidth=0, leftPadding=8,
                     italics=True),
        "bullet": _ps("RA_Bullet",
                      fontSize=10, leading=14, leftIndent=16,
                      spaceAfter=3),
        "meta": _ps("RA_Meta",
                    fontSize=8, textColor=colors.HexColor("#888888"),
                    alignment=TA_CENTER, spaceAfter=14),
    }

    # ── Satır ayrıştırıcı ─────────────────────────────────────────────────────
    story = []

    # Üst bilgi
    story.append(Paragraph("Analizkasar Raporu", styles["h1"]))
    story.append(Paragraph(
        f"Oluşturulma: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  ·  Analizkasar v0.1",
        styles["meta"],
    ))
    story.append(HRFlowable(width="100%", thickness=1,
                             color=colors.HexColor("#cccccc"), spaceAfter=14))

    lines      = md_text.splitlines()
    i          = 0
    list_items = []          # bekleyen liste öğeleri
    list_type  = None        # "bullet" | "ordered"

    def _flush_list():
        nonlocal list_items, list_type
        if not list_items:
            return
        bullet_char = "•" if list_type == "bullet" else None
        flowables = []
        for idx, (ltype, content) in enumerate(list_items):
            para = Paragraph(_inline_md(_escape_rl(content)), styles["bullet"])
            if ltype == "ordered":
                flowables.append(ListItem(para, value=idx + 1))
            else:
                flowables.append(ListItem(para, bulletText="•"))
        story.append(ListFlowable(
            flowables,
            bulletType="bullet" if list_type == "bullet" else "I",
            leftIndent=16,
            bulletFontSize=10,
        ))
        story.append(Spacer(1, 4))
        list_items = []
        list_type  = None

    while i < len(lines):
        line = lines[i]

        # ── Kod bloğu (```) ───────────────────────────────────────────────────
        if line.strip().startswith("```"):
            _flush_list()
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            code_text = "\n".join(code_lines)
            story.append(Preformatted(code_text, styles["code"]))
            story.append(Spacer(1, 4))
            i += 1
            continue

        # ── Yatay çizgi ───────────────────────────────────────────────────────
        if re.match(r'^[-*_]{3,}\s*$', line):
            _flush_list()
            story.append(HRFlowable(width="100%", thickness=0.5,
                                     color=colors.HexColor("#dddddd"),
                                     spaceBefore=6, spaceAfter=6))
            i += 1
            continue

        # ── Başlıklar ─────────────────────────────────────────────────────────
        h_match = re.match(r'^(#{1,3})\s+(.*)', line)
        if h_match:
            _flush_list()
            level = len(h_match.group(1))
            text  = _escape_rl(h_match.group(2).strip())
            skey  = {1: "h1", 2: "h2", 3: "h3"}[min(level, 3)]
            story.append(Paragraph(text, styles[skey]))
            i += 1
            continue

        # ── Alıntı (>) ────────────────────────────────────────────────────────
        if line.startswith(">"):
            _flush_list()
            content = line.lstrip("> ").strip()
            story.append(Paragraph(
                f"<i>{_escape_rl(content)}</i>", styles["quote"]
            ))
            i += 1
            continue

        # ── Madde listesi (- / * / +) ─────────────────────────────────────────
        bullet_m = re.match(r'^(\s*)[-*+]\s+(.*)', line)
        if bullet_m:
            if list_type and list_type != "bullet":
                _flush_list()
            list_type = "bullet"
            list_items.append(("bullet", bullet_m.group(2).strip()))
            i += 1
            continue

        # ── Numaralı liste ────────────────────────────────────────────────────
        num_m = re.match(r'^(\s*)\d+[.)]\s+(.*)', line)
        if num_m:
            if list_type and list_type != "ordered":
                _flush_list()
            list_type = "ordered"
            list_items.append(("ordered", num_m.group(2).strip()))
            i += 1
            continue

        # ── Boş satır ─────────────────────────────────────────────────────────
        if not line.strip():
            _flush_list()
            story.append(Spacer(1, 6))
            i += 1
            continue

        # ── Normal paragraf ───────────────────────────────────────────────────
        _flush_list()
        para_lines = [line]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(
            r'^(#{1,3}\s|[-*+]\s|\d+[.)]\s|```|>|[-*_]{3,}\s*$)', lines[i]
        ):
            para_lines.append(lines[i])
            i += 1
        content = " ".join(para_lines).strip()
        if content:
            story.append(Paragraph(
                _inline_md(_escape_rl(content)), styles["body"]
            ))

    _flush_list()

    doc.build(story)


# ─────────────────────────────────────────────────────────────────────────────
# EXPORT: DOCX / TXT / JSON
# ─────────────────────────────────────────────────────────────────────────────

def save_docx(text, path):
    doc = Document()
    doc.add_heading("Analizkasar Raporu", 0)
    doc.add_paragraph(f"Oluşturulma: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    doc.add_paragraph("")
    for line in text.split("\n"):
        if line.strip():
            doc.add_paragraph(line.strip())
    doc.save(path)

def save_txt(text, path):
    Path(path).write_text(text, encoding="utf-8")

def save_json(data, path):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# PROMPTS  — her fonksiyon (system_prompt, user_prompt) tuple döndürür.
# system: modelin kimliğini ve davranış kurallarını belirler (kesinlikle uyulması gereken)
# user:   görev verisini taşır (kaynaklar, analizler vb.)
# ─────────────────────────────────────────────────────────────────────────────

# Tüm çağrılarda ortak sistem direktifleri
def _make_core_rules(intent: "UserIntent | None" = None) -> str:
    """_CORE_RULES metnini üretir; varsa UserIntent niyet bloğunu başa ekler."""
    intent_block = ""
    if intent and not intent.is_empty():
        intent_block = intent.to_prompt_block() + "\n\n"

    return intent_block + """\
GÖREV PROTOKOLÜ (hiçbir koşulda çiğnenemez):
- Bu bir analiz görevi; sohbet, karşılama, teşekkür veya özür YOK.
- Soru sorma, ek bilgi isteme, seçenek sunma YOK.
- Yanıt yalnızca istenen çıktıdan oluşur; başka hiçbir şey ekleme.

KAYNAK BAĞLAMA PROTOKOLÜ (NotebookLM ilkesi — mutlak kural):
- Yalnızca sana verilen kaynak belgelerindeki bilgileri kullan.
- Genel eğitim bilgini, harici varsayımları veya kaynaklarda geçmeyen iddiaları
  metne enjekte ETME. Kaynakların dışına çıkan her cümle bu protokolü ihlal eder.
- Her somut iddia, veri veya teknik ifade, cümle sonunda köşeli parantez içinde
  kaynak numarasıyla işaretlenir: [K:1], [K:2] vb. (batch analizleri için) veya
  [1], [2] vb. (final rapor için).
- Kaynakta açıkça geçmeyen bir bilgiyi "genel kabul" veya "bilindiği üzere"
  ifadesiyle sunmak yasaktır. Eğer bir bilgi kaynaklarda yoksa, o bilgi yazılmaz.

YAZIM BİÇİMİ — AKADEMİK MAKALE STANDARDI:
Aşağıdaki kurallar mutlaktır ve tek istisnası yoktur.

1. PARAGRAF AKIŞI
   Her düşünce, kendi içinde tam ve bağımsız bir paragraf olarak yazılır.
   Paragraflar arasında argüman akışı kopmamalı; her paragraf bir öncekinden
   mantıksal olarak türemelidir.

2. MADDE LİSTESİ YASAĞI
   Tire (-), yıldız (*), ok (→ ► •) veya numaralandırma ile başlayan satır
   KESİNLİKLE YAZILMAZ. Listelenmesi gereken unsurlar cümle içine entegre edilir.
   Örnek (yanlış): "Üç temel bileşen vardır:\\n- Algı\\n- Bellek\\n- Eylem"
   Örnek (doğru): "Sistem algı, bellek ve eylem bileşenleri üzerine inşa edilmiştir;
   algı katmanı ortamdan girdi alırken, bellek modülü geçmiş gözlemleri saklar ve
   eylem birimi çıktıyı üretir."

3. EMOJİ VE GÖRSEL SİMGE YASAĞI
   🧠 ✅ ❌ 🚀 📌 gibi simgeler hiçbir koşulda kullanılmaz.

4. TABLO KULLANIMI
   Tablo yalnızca karşılaştırmalı sayısal veya kategorik veri için kullanılır;
   fikir veya argüman listesi asla tablo içine yerleştirilmez.

5. BOLD / KURSIV DENETİMİ
   **Bold** yalnızca teknik terim veya özel isim için kullanılır; vurgu veya
   dekorasyon amacıyla kullanılmaz. *İtalik* yalnızca yabancı dil ifadesi için.

6. BÖLÜM BAŞLIKLARI
   ## ve ### başlıklar yalnızca zorunlu yapı bölümleri için kullanılır;
   her alt fikre başlık açılmaz.

7. TON
   Akademik, nesnel, teknik. Kişisel yorum veya öneri cümleleri ("şunu öneririm",
   "dikkat edin") YOK. İddia kanıtla desteklenir; kanıtsız genelleme yapılmaz.\
"""


def build_analysis_prompt(chunk: str, language: str,
                          rag_context: str = "",
                          source_index: dict[str, int] | None = None,
                          intent: "UserIntent | None" = None) -> tuple[str, str]:
    rag_section = ""
    if rag_context:
        rag_section = f"""
RAG BAĞLAMI (önceki batch'lerden retrieval edilen ilgili içerik):
Bu bölümdeki bilgileri mevcut kaynakları analiz ederken referans al;
çelişen noktaları ve destekleyen bulguları karşılaştır.

{rag_context}

---
"""
    # Kaynak numaralarını prompt başına ekle (NotebookLM kaynak indeksi)
    source_index_block = ""
    if source_index:
        lines = "\n".join(f"  K:{num}  {url}" for url, num in sorted(source_index.items(), key=lambda x: x[1]))
        source_index_block = f"""
KAYNAK İNDEKSİ (bu batch'te geçen kaynakların numaraları):
{lines}

Her somut iddia veya teknik ifade, cümle sonunda [K:N] etiketiyle işaretlenmelidir.
Kaynak indeksinde olmayan bir bilgi metne eklenmez.

---
"""

    system = f"""\
Sen otonom çalışan bir araştırma yapay zekâsısın (Research Agent).
Görevin: verilen web kaynaklarını analiz edip yapılandırılmış akademik metin üretmek.

{_make_core_rules(intent)}

ÇIKTI YAPISI (bu sıraya kesinlikle uy; her bölüm paragraf olarak yazılır):

## Teknik Analiz
Her kaynağın içeriği sistem, algoritma ve yöntem düzeyinde yorumlanır. Kaynak
sayısına bakılmaksızın tüm içerik tek bir sürekli akademik metin olarak akar.
Her somut iddia [K:N] etiketiyle kaynak numarasına bağlanır.

## Kavramsal Sentez
Kaynaklar arasındaki bağlantılar, yaklaşım varyasyonları ve çelişkiler tek bir
tutarlı argüman akışında sentezlenir. Atıflar korunur.

## Açık Problemler
Yanıtsız kalan sorular ve eksik teknik detaylar düz paragraf olarak yazılır.

Ardından varsa LINK_REQUEST ve NEW_SOURCE satırları (bunlar liste formatındadır,
istisna olarak kabul edilir):
LINK_REQUEST: https://...
NEW_SOURCE: https://...

Rapor dili: {language}\
"""

    user = f"""\
Aşağıdaki web kaynaklarını analiz et.
Her kaynak "SOURCE: <url>" başlığıyla başlar; sayfa bağlantıları "PAGE_LINKS:" bölümündedir.
{source_index_block}{rag_section}
Kritik bağlantı talep formatı (her biri ayrı satır, maks. 10):
LINK_REQUEST: https://...

Yeni kaynak öneri formatı (maks. 5):
NEW_SOURCE: https://...

---
KAYNAKLAR:
{chunk}\
"""
    return system, user


def build_final_prompt(n_batches: int, n_sources: int, n_chars: str,
                       all_outputs: str, language: str,
                       rag_context: str = "",
                       user_answers: str = "",
                       source_registry: dict[str, int] | None = None,
                       intent: "UserIntent | None" = None) -> tuple[str, str]:
    rag_section = ""
    if rag_context:
        rag_section = f"""
RAG DESTEĞİ (tüm kaynaklardan retrieval edilen kritik bölümler):
Bu içerikleri akademik makalenin argümanlarını güçlendirmek için kullan.

{rag_context}

---
"""
    qa_section = ""
    if user_answers:
        qa_section = f"""
KULLANICI CEVAPLARI (clarification fazından — bunları raporda öncelikli kaynak olarak kullan):

{user_answers}

---
"""
    # Global kaynak sicili (tüm run)
    registry_block = ""
    if source_registry:
        lines = "\n".join(
            f"  [{num}] {url}"
            for url, num in sorted(source_registry.items(), key=lambda x: x[1])
        )
        registry_block = f"""
GLOBAL KAYNAK SİCİLİ ({len(source_registry)} kaynak):
{lines}

Makale boyunca her somut iddia, veri veya teknik ifade [N] formatında
bu listedeki numarayla işaretlenmelidir. Kaynakça bölümü aynı numaralama
şemasını kullanır. Sicilde olmayan bir bilgi makaleye eklenmez.

---
"""

    system = f"""\
Sen uluslararası hakemli bir dergiye makale yazan kıdemli bir araştırmacısın.
Görevin: sana verilen analizleri tek bir bütünlüklü akademik araştırma makalesi
olarak yazmak. Çıktı, doğrudan bir akademik dergiye gönderilebilecek kalitede
olmalıdır.

{_make_core_rules(intent)}

ZORUNLU MAKALE YAPISI (Markdown başlıkları, başka başlık ekleme):
# Araştırma Raporu
## 1. Abstract
## 2. Giriş
## 3. Literatür Sentezi
## 4. Teknik Mimari Analiz
## 5. Bulgular
## 6. Tartışma
## 7. Sonuç
## Kaynakça

Her bölüm en az iki dolu paragraf içerir. Paragraflar birbirinden mantıksal olarak
türer; bölüm içi akış kopmamalıdır. Kısa ve yüzeysel cümleler yerine, iddiayı
kuran ve kanıtla destekleyen uzun, yoğun cümleler tercih edilir.

KAYNAKÇA BÖLÜMÜ:
Makale sonundaki ## Kaynakça bölümünde kayıtlı tüm kaynaklar şu formatta listelenir:
[N] Başlık veya kısa açıklama. URL. (Erişim tarihi: {__import__('datetime').date.today()})
Yalnızca metinde atıf yapılan kaynaklar listelenir; gereksiz kaynak eklenmez.

Rapor dili: {language}

YANIT FORMATI — KESİNLİKLE UYULMALI:
Yanıtını yalnızca geçerli bir JSON nesnesi olarak döndür.
JSON dışında hiçbir şey yazma; açıklama, giriş veya ``` bloğu KULLANMA.

Başarılı rapor:
{{"is_final_report": true, "report": "<Markdown makale>"}}

Tamamlanamama durumu:
{{"is_final_report": false, "message": "<neden>", "needed_input": "<kullanıcıdan ne istiyorsun>"}}\
"""

    user = f"""\
{n_batches} araştırma döngüsünden elde edilmiş analizler ({n_sources} kaynak, {n_chars} karakter).
Bu analizleri yukarıdaki yapıda, tam atıflı akademik bir makaleye dönüştür.
{registry_block}{qa_section}{rag_section}
---
{all_outputs}\
"""
    return system, user


def build_rag_final_prompt(
    n_sources: int,
    rag_context: str,
    language: str,
    user_answers: str = "",
    source_registry: dict[str, int] | None = None,
    intent: "UserIntent | None" = None,
) -> tuple[str, str]:
    """
    RAG moduna özgü final rapor promptu.
    Girdi olarak batch analizi değil, doğrudan retrieval edilen ham chunk'lar kullanılır.
    """
    qa_section = ""
    if user_answers:
        qa_section = f"""
KULLANICI CEVAPLARI (clarification fazından — öncelikli kaynak olarak kullan):

{user_answers}

---
"""
    registry_block = ""
    if source_registry:
        lines = "\n".join(
            f"  [{num}] {url}"
            for url, num in sorted(source_registry.items(), key=lambda x: x[1])
        )
        registry_block = f"""
KAYNAK SİCİLİ ({len(source_registry)} kaynak — makale boyunca [N] formatında atıf yapılır):
{lines}

---
"""

    system = f"""\
Sen uluslararası hakemli bir dergiye makale yazan kıdemli bir araştırmacısın.
Sana {n_sources} farklı kaynaktan retrieval edilmiş ham içerik verilecek.
Görevin: bu içerikleri sentezleyerek tek bir bütünlüklü akademik araştırma makalesi
yazmak. Çıktı, doğrudan bir akademik dergiye gönderilebilecek kalitede olmalıdır.

{_make_core_rules(intent)}

ZORUNLU MAKALE YAPISI (Markdown başlıkları, başka başlık ekleme):
# Araştırma Raporu
## 1. Abstract
## 2. Giriş
## 3. Literatür Sentezi
## 4. Teknik Mimari Analiz
## 5. Bulgular
## 6. Tartışma
## 7. Sonuç
## Kaynakça

Her bölüm en az iki dolu paragraf içerir. Ham kaynak chunk'larını birer birer
özetleme; bunları sentezleyerek tutarlı bir argüman akışı oluştur. Kısa ve yüzeysel
cümleler yerine, iddiayı kuran ve kanıtla destekleyen uzun, yoğun cümleler yaz.

KAYNAKÇA BÖLÜMÜ:
[N] Başlık veya kısa açıklama. URL. (Erişim tarihi: {__import__('datetime').date.today()})
Yalnızca metinde atıf yapılan kaynaklar listelenir.

Rapor dili: {language}

YANIT FORMATI — KESİNLİKLE UYULMALI:
Yanıtını yalnızca geçerli bir JSON nesnesi olarak döndür.
JSON dışında hiçbir şey yazma; açıklama, giriş veya ``` bloğu KULLANMA.

Başarılı rapor:
{{"is_final_report": true, "report": "<Markdown makale>"}}

Tamamlanamama durumu:
{{"is_final_report": false, "message": "<neden>", "needed_input": "<ne istiyorsun>"}}\
"""

    user = f"""\
{n_sources} kaynaktan retrieval edilen içerik aşağıdadır.
Bu chunk'ları sentezleyerek yukarıdaki yapıda tam atıflı akademik bir makale yaz.
{registry_block}{qa_section}
---
RAG İÇERİĞİ:
{rag_context}\
"""
    return system, user


def build_clarification_prompt(
    n_batches: int,
    n_sources: int,
    all_outputs: str,
    language: str,
) -> tuple[str, str]:
    """
    Modelden final raporu yazmadan önce ihtiyaç duyduğu soruları istemesi için kullanılır.
    _CORE_RULES'daki 'soru sorma yasağı' bu prompt için UYGULANMAZ — çünkü görevin
    kendisi soru üretmektir.
    """
    system = f"""\
Sen kıdemli bir akademik araştırma editörüsün.
Sana {n_batches} araştırma döngüsünden ({n_sources} kaynak) derlenen analizler verilecek.
Bu analizleri okuyacak ve ardından yazacağın akademik final raporu için eksik gördüğün
bilgileri kullanıcıya sorular hâlinde ileteceksin.

KURALLAR:
- Yalnızca gerçekten belirsiz veya eksik olan noktaları sor; analizlerden çıkarılabilecek
  bilgileri sorma.
- Soru sayısı en fazla 7 olmalı; önemine göre sırala (en kritik önce).
- Her sorunun neden sorulduğunu kısaca açıkla (1 cümle).
- Akademik, nesnel ton kullan.

YANIT FORMATI — sadece geçerli JSON, başka hiçbir şey:
{{"questions": [{{"id": 1, "question": "...", "why": "..."}}]}}

Rapor dili: {language}\
"""

    user = f"""\
Aşağıdaki {n_batches} batch analizini oku ve final akademik raporu en iyi şekilde
yazabilmek için kullanıcıya sormak istediğin soruları belirle.

---
{all_outputs}\
"""
    return system, user


def collect_user_answers(questions: list[dict], language: str) -> str:
    """
    Soruları terminalde gösterir, cevapları toplar ve birleşik bir metin bloğu döndürür.
    Boş bırakılan sorular atlanır.
    """
    console.print()
    console.print(Panel(
        f"[bold bright_cyan]Model final raporu yazmadan önce {len(questions)} soru soruyor.[/bold bright_cyan]\n"
        f"[dim]Boş bırakabilirsiniz; o soru atlanır. Çıkmak için Ctrl+C.[/dim]",
        title="[bold]📋 Kullanıcı Girdisi Gerekiyor[/bold]",
        border_style="bright_cyan",
        padding=(0, 2),
    ))
    console.print()

    qa_pairs: list[str] = []

    for q in questions:
        qid   = q.get("id", "?")
        qtext = q.get("question", "").strip()
        why   = q.get("why", "").strip()

        if not qtext:
            continue

        # Soru paneli
        console.print(Panel(
            f"[bold bright_white]{qtext}[/bold bright_white]\n"
            f"[dim italic]{why}[/dim italic]",
            title=f"[bold bright_yellow]Soru {qid}/{len(questions)}[/bold bright_yellow]",
            border_style="bright_yellow",
            padding=(0, 2),
        ))

        try:
            answer = input("  ✏  Cevabınız (boş bırakmak için Enter): ").strip()
        except EOFError:
            answer = ""

        if answer:
            qa_pairs.append(f"S{qid}: {qtext}\nCevap: {answer}")
            log.success(f"Soru {qid} cevaplandı.", i=1)
        else:
            log.info(f"Soru {qid} atlandı.", i=1)

        console.print()

    if not qa_pairs:
        return ""

    return "KULLANICI CEVAPLARI:\n\n" + "\n\n".join(qa_pairs)


def build_thematic_cluster_prompt(batch_analyses: list[str], language: str,
                                   intent: "UserIntent | None" = None) -> tuple[str, str]:
    system = f"""\
Sen bir araştırma editörüsün.
Görevin: batch analizlerini tematik gruplara ayırmak ve sonucu JSON olarak döndürmek.

{_make_core_rules(intent)}

GRUPLAMA KURALLARI:
Grup sayısı 2–7 arasında olmalı; içeriğe göre doğal belirle.
Her batch en az bir gruba ait olmalı; bir batch birden fazla gruba girebilir.
batch_indices sıfırdan başlar (batch 1 → indeks 0).

YANIT FORMATI — sadece JSON, başka hiçbir şey:
{{"clusters": [{{"theme": "...", "description": "...", "batch_indices": [0, 2]}}]}}

Dil: {language}\
"""

    numbered = "\n\n".join(
        f"=== BATCH {i+1} ===\n{txt}" for i, txt in enumerate(batch_analyses)
    )
    user = f"""\
Aşağıdaki {len(batch_analyses)} batch analizini tematik olarak gruplandır:

{numbered}\
"""
    return system, user


def build_cluster_synthesis_prompt(
    theme: str,
    description: str,
    cluster_analyses: list[str],
    language: str,
    intent: "UserIntent | None" = None,
) -> tuple[str, str]:
    system = f"""\
Sen uluslararası hakemli bir dergiye makale yazan kıdemli bir araştırmacısın.
Görevin: sana verilen batch analizlerini tek bir tematik bölüm olarak yazmak.
Bu bölüm, daha büyük bir araştırma makalesine entegre edilecektir.

{_make_core_rules(intent)}

ZORUNLU YAPI (Markdown, başka başlık ekleme):
## {theme}
### Teknik Çerçeve
### Metodolojik Yaklaşımlar
### Karşılaştırmalı Değerlendirme
### Açık Problemler ve Sınırlılıklar

Her alt bölüm en az iki dolu paragraf içerir. Paragraflar tek bir tutarlı argüman
akışı oluşturur; alt bölüm içinde akış kopmamalıdır.
Girdi analizlerindeki [K:N] atıfları korunur ve metinde kullanılmaya devam edilir.

Dil: {language}\
"""

    combined = "\n\n---\n\n".join(cluster_analyses)
    user = f"""\
Tema: {theme}
Açıklama: {description}

Aşağıdaki {len(cluster_analyses)} batch analizini bu temaya odaklanarak
akademik bir bölüm olarak yaz. [K:N] atıflarını koru:

{combined}\
"""
    return system, user





# ─────────────────────────────────────────────────────────────────────────────
# BANNER
# ─────────────────────────────────────────────────────────────────────────────

def print_banner(cfg, n_urls, batch_size, output_path, fmt):
    bc = BACKEND_COLORS.get(cfg["backend"], "white")
    n_batches_est = (n_urls + batch_size - 1) // batch_size
    fmt_label = {
        "pdf":  "📄 PDF  [dim](Markdown → ReportLab)[/dim]",
        "docx": "📝 DOCX",
        "md":   "📃 Markdown",
        "txt":  "📋 Düz metin",
        "json": "🗄️  JSON",
    }.get(fmt, fmt)
    content = (
        f"  Backend    : [{bc}]{cfg['backend']}[/{bc}]  ·  Model: [{bc}]{cfg['model']}[/{bc}]\n"
        f"  Toplam URL : [bright_white]{n_urls}[/bright_white]  ·  "
        f"Batch boyutu: [bright_white]{batch_size}[/bright_white]  ·  "
        f"Tahmini batch: [bright_white]~{n_batches_est}[/bright_white]\n"
        f"  Çıktı      : [bright_white]{output_path}[/bright_white]  ·  {fmt_label}\n"
        f"  [dim]Model, sayfa bağlantılarını takip edebilir (LINK_REQUEST)[/dim]"
    )
    console.print(Panel(
        content,
        title="[bold]🔬 Analizkasar v0.1[/bold]",
        border_style="bright_cyan",
        padding=(0, 2),
    ))
    console.print()


# ─────────────────────────────────────────────────────────────────────────────
# ANA AGENT DÖNGÜSÜ
# ─────────────────────────────────────────────────────────────────────────────

def run_agent(
    initial_urls: list,
    cfg: dict,
    batch_size: int,
    delay: float,
    output_path: str,
    output_format: str,
    scrape_timeout: int,
    max_chars: int,
    save_intermediate: bool,
    max_extra_links: int,
    language: str = "Turkish",
    thematic_synthesis: bool = True,
    # ── RAG parametreleri ──────────────────────────────────────────────────
    rag: bool                = False,
    rag_chunk_size: int      = 1000,
    rag_chunk_overlap: int   = 200,
    rag_top_k: int           = 5,
    rag_embedding_model: str = "all-MiniLM-L6-v2",
    # ── Clarification parametresi ──────────────────────────────────────────
    clarification: bool      = True,
    # ── Kullanıcı niyeti ───────────────────────────────────────────────────
    intent: "UserIntent | None" = None,
):
    stats = Stats()

    # ── RAG deposu (isteğe bağlı) ──────────────────────────────────────────
    rag_store: RAGStore | None = None
    if rag:
        log.section("RAG BAŞLATILIYOR", style="bold bright_yellow")
        rag_store = RAGStore(
            chunk_size      = rag_chunk_size,
            chunk_overlap   = rag_chunk_overlap,
            embedding_model = rag_embedding_model,
            top_k           = rag_top_k,
        )

    queue: list[str]    = list(dict.fromkeys(initial_urls))
    processed: set[str] = set()
    history: list[str]  = []
    all_batch_data: list[dict] = []

    # ── Kaynak sicili: URL → global atıf numarası (NotebookLM ilkesi) ─────────
    source_registry: dict[str, int] = {}
    _src_counter = 0

    if not log.quiet:
        print_banner(cfg, len(queue), batch_size, output_path, output_format)

    batch_no = 0

    while queue:
        batch_no += 1
        batch_t0   = time.time()
        llm_before = stats.llm_total_secs

        batch = []
        while queue and len(batch) < batch_size:
            url = queue.pop(0)
            if url not in processed:
                batch.append(url)
                processed.add(url)

        if not batch:
            break

        remaining = len(queue)
        log.section(
            f"BATCH {batch_no}  ·  {len(batch)} URL işlenecek  ·  "
            f"kuyrukta {remaining} bekliyor",
            style="bold bright_cyan",
        )

        texts: list[str] = []
        batch_fetched = batch_failed = batch_chars = 0
        all_page_links: dict[str, list[str]] = {}

        log.rule("Scraping", style="steel_blue1")

        with Progress(
            SpinnerColumn(spinner_name="dots", style="steel_blue1"),
            TextColumn("[bold steel_blue1]{task.description}[/bold steel_blue1]"),
            BarColumn(bar_width=28, style="steel_blue1", complete_style="bright_green"),
            MofNCompleteColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
            console=console,
            expand=False,
        ) as progress:
            ftask = progress.add_task("İndiriliyor…", total=len(batch))

            for url in batch:
                short = (url[:60] + "…") if len(url) > 62 else url
                progress.update(ftask, description=f"[dim]{short}[/dim]")

                content, elapsed, nchars, plinks = fetch_url(
                    url, scrape_timeout, max_chars, stats
                )

                if content:
                    link_block = ""
                    if plinks:
                        shown = plinks[:30]
                        link_block = "\nPAGE_LINKS:\n" + "\n".join(shown)
                        if len(plinks) > 30:
                            link_block += f"\n… ({len(plinks) - 30} bağlantı daha var)"

                    texts.append(f"SOURCE: {url}\n{content}{link_block}")
                    all_page_links[url] = plinks
                    batch_fetched += 1
                    batch_chars   += nchars

                    # ── Kaynak sicili: URL'e global numara ata ────────────────
                    if url not in source_registry:
                        _src_counter += 1
                        source_registry[url] = _src_counter

                    # ── RAG: belgeyi depoya ekle ───────────────────────────
                    if rag_store is not None:
                        n_chunks = rag_store.add_document(url, content)
                        log.fetch(
                            f"[bright_green]✓[/bright_green] [dim]{short}[/dim]  "
                            f"[bright_white]{nchars:,}[/bright_white] kar  "
                            f"[dim]({elapsed:.2f}s)[/dim]  "
                            f"[dim]{len(plinks)} link  "
                            f"[bright_yellow]{n_chunks} RAG chunk[/bright_yellow][/dim]",
                            i=1,
                        )
                    else:
                        log.fetch(
                            f"[bright_green]✓[/bright_green] [dim]{short}[/dim]  "
                            f"[bright_white]{nchars:,}[/bright_white] kar  "
                            f"[dim]({elapsed:.2f}s)[/dim]  "
                            f"[dim]{len(plinks)} link bulundu[/dim]",
                            i=1,
                        )
                else:
                    batch_failed += 1
                    log.fetch(
                        f"[bright_red]✗[/bright_red] [dim]{short}[/dim]  "
                        f"[bright_red]başarısız ({elapsed:.2f}s)[/bright_red]",
                        i=1,
                    )

                progress.advance(ftask)

        log.stat(
            f"Fetch tamamlandı  ·  "
            f"[bright_green]{batch_fetched} başarılı[/bright_green]  "
            f"[bright_red]{batch_failed} başarısız[/bright_red]  ·  "
            f"[bright_white]{batch_chars:,}[/bright_white] karakter"
        )

        if not texts:
            log.warning("Bu batch için hiç içerik alınamadı — atlanıyor.")
            continue

        # ── RAG MODU: LLM analizi atla, sadece depola ───────────────────────
        if rag_store is not None:
            # Sayfa linklerini otomatik kuyruğa ekle (LLM'in LINK_REQUEST'i yok)
            auto_added = 0
            for plinks in all_page_links.values():
                for lurl in plinks:
                    if (lurl not in processed and lurl not in queue
                            and auto_added < max_extra_links):
                        queue.append(lurl)
                        auto_added += 1
                        stats.total_linked_urls += 1
            if auto_added:
                log.info(
                    f"[bright_yellow]RAG:[/bright_yellow] "
                    f"{auto_added} sayfa linki otomatik kuyruğa eklendi.",
                    i=1,
                )

            batch_secs = time.time() - batch_t0
            bdata = {
                "batch": batch_no, "urls": batch,
                "fetched": batch_fetched, "failed": batch_failed,
                "chars": batch_chars,
                "link_reqs": 0, "new_urls": auto_added,
                "llm_secs": 0.0,
                "secs": round(batch_secs, 2),
                "analysis": "",        # RAG modunda LLM analizi yok
            }
            all_batch_data.append(bdata)
            stats.batch_stats.append(bdata)
            stats.batches_done += 1
            log.success(
                f"Batch {batch_no} depolandı  [dim]({batch_secs:.1f}s)[/dim]  ·  "
                f"kuyrukta [bright_white]{len(queue)}[/bright_white] URL kaldı"
            )
            if delay > 0 and queue:
                time.sleep(delay)
            continue          # ← LLM analizi bloğunu atla

        # ── NORMAL MOD: LLM Batch Analizi ────────────────────────────────────
        log.rule("LLM Analiz", style="bright_magenta")

        chunk = "\n\n---\n\n".join(texts)

        # Bu batch'teki URL → kaynak numarası haritası
        batch_source_index = {url: source_registry[url] for url in batch if url in source_registry}

        result = ask_llm(
            build_analysis_prompt(chunk, language,
                                  source_index=batch_source_index,
                                  intent=intent),
            cfg, stats,
        )
        history.append(result)

        link_requests = parse_link_requests(result)
        if link_requests:
            added_links = 0
            for lurl in link_requests:
                if lurl not in processed and lurl not in queue:
                    queue.insert(0, lurl)
                    added_links += 1
                    stats.total_linked_urls += 1
                    log.link(
                        f"[yellow]Bağlantı talep edildi:[/yellow] [dim]{lurl[:70]}[/dim]",
                        i=1,
                    )
            if added_links:
                log.success(
                    f"[yellow]{added_links}[/yellow] bağlantılı sayfa kuyruğa eklendi "
                    f"[dim](öncelikli)[/dim]",
                )

        new_sources = re.findall(r'NEW_SOURCE:\s*(https?://[^\s\n]+)', result)
        added_new = 0
        for nurl in new_sources:
            if nurl not in processed and nurl not in queue:
                queue.append(nurl)
                added_new += 1
                stats.total_new_urls += 1
        if added_new:
            log.success(
                f"[bright_yellow]{added_new}[/bright_yellow] yeni kaynak kuyruğa eklendi "
                f"[dim](normal öncelik)[/dim]"
            )

        if save_intermediate:
            inter = output_path + f".batch{batch_no}.txt"
            save_txt(result, inter)
            log.save(f"Ara çıktı: [underline]{inter}[/underline]")

        batch_secs = time.time() - batch_t0
        llm_secs   = stats.llm_total_secs - llm_before

        bdata = {
            "batch": batch_no, "urls": batch,
            "fetched": batch_fetched, "failed": batch_failed,
            "chars": batch_chars,
            "link_reqs": len(link_requests),
            "new_urls": added_new,
            "llm_secs": round(llm_secs, 2),
            "secs": round(batch_secs, 2),
            "analysis": result,
        }
        all_batch_data.append(bdata)
        stats.batch_stats.append(bdata)
        stats.batches_done += 1

        log.success(
            f"Batch {batch_no} tamamlandı  [dim]({batch_secs:.1f}s)[/dim]  ·  "
            f"kuyrukta [bright_white]{len(queue)}[/bright_white] URL kaldı  ·  "
            f"toplam geçen: [dim]{stats.elapsed()}[/dim]"
        )

        if delay > 0 and queue:
            time.sleep(delay)

    # ── FINAL RAPOR ────────────────────────────────────────────────────────────
    if not history and rag_store is None:
        log.error("Hiçbir içerik işlenemedi — çıkılıyor.")
        sys.exit(1)

    if rag_store is not None and stats.total_fetched == 0:
        log.error("RAG deposu boş — hiçbir URL getirilemedi.")
        sys.exit(1)

    log.section("FINAL RAPOR", style="bold bright_green")

    # ── Tematik Sentez (normal mod, batch sayısı ≥ 2) ─────────────────────────
    if thematic_synthesis and len(history) >= 2 and rag_store is None:
        log.step(
            f"Tematik gruplama başlıyor  ·  "
            f"{len(history)} batch analizi sınıflandırılıyor…"
        )

        cluster_prompt = build_thematic_cluster_prompt(history, language, intent=intent)
        raw_clusters   = ask_llm(cluster_prompt, cfg, stats)

        # JSON parse
        cleaned_c = raw_clusters.strip()
        if cleaned_c.startswith("```"):
            cleaned_c = re.sub(r'^```[a-zA-Z]*\n?', '', cleaned_c)
            cleaned_c = re.sub(r'\n?```$', '', cleaned_c.strip())

        clusters = None
        try:
            parsed_c = json.loads(cleaned_c)
            clusters = parsed_c.get("clusters")
        except json.JSONDecodeError:
            log.warning(
                "[bright_yellow]Tematik gruplama JSON parse hatası — "
                "düz birleştirmeye geçiliyor.[/bright_yellow]"
            )

        if clusters:
            # Tablo göster
            from rich.table import Table
            from rich import box as _box
            ct = Table(
                title="🗂  Tematik Gruplar",
                box=_box.SIMPLE_HEAVY,
                border_style="bright_black",
                header_style="bold bright_white",
            )
            ct.add_column("Tema",          style="bright_cyan",   min_width=28)
            ct.add_column("Batch'ler",     style="bright_yellow", min_width=14)
            ct.add_column("Açıklama",      style="dim white",     min_width=40)
            for cl in clusters:
                batch_list = ", ".join(
                    str(i + 1) for i in cl.get("batch_indices", [])
                )
                ct.add_row(cl["theme"], batch_list, cl.get("description", ""))
            console.print()
            console.print(ct)
            console.print()

            # Her tema için derinleştirilmiş sentez
            cluster_syntheses: list[str] = []
            for idx, cl in enumerate(clusters, 1):
                theme       = cl["theme"]
                description = cl.get("description", "")
                indices     = cl.get("batch_indices", [])

                # İndeks sınır kontrolü
                valid_analyses = [
                    history[i] for i in indices if 0 <= i < len(history)
                ]
                if not valid_analyses:
                    log.warning(
                        f"[bright_yellow]Tema '{theme}' için geçerli batch bulunamadı — "
                        f"atlanıyor.[/bright_yellow]"
                    )
                    continue

                log.section(
                    f"Tema Sentezi {idx}/{len(clusters)}: {theme}",
                    style="bold bright_magenta",
                )

                synth_prompt = build_cluster_synthesis_prompt(
                    theme, description, valid_analyses, language, intent=intent
                )
                synthesis = ask_llm(synth_prompt, cfg, stats)
                cluster_syntheses.append(synthesis)

                if save_intermediate:
                    inter = output_path + f".tema{idx}.txt"
                    save_txt(synthesis, inter)
                    log.save(f"Tema ara çıktısı: [underline]{inter}[/underline]")

            # Final prompt için girdi: tema sentezleri
            synthesis_input = "\n\n═══\n\n".join(cluster_syntheses)
            log.step(
                f"{len(cluster_syntheses)} tema sentezi final rapora aktarılıyor…"
            )
        else:
            # Gruplama başarısız → düz birleştir
            synthesis_input = "\n\n".join(history)
            log.step(
                f"{stats.batches_done} batch düz birleştirilerek final rapora aktarılıyor…"
            )
    else:
        # Tematik sentez kapalı veya batch sayısı yetersiz
        synthesis_input = "\n\n".join(history)
        log.step(
            f"{stats.batches_done} batch, "
            f"{stats.total_fetched} kaynak, "
            f"{stats.total_chars:,} karakter birleştiriliyor…"
        )

    # ── RAG MODU: multi-query retrieval ile final içerik oluştur ─────────────
    if rag_store is not None:
        rs = rag_store.rag_stats()
        log.info(
            f"[bright_yellow]RAG deposu:[/bright_yellow] "
            f"{rs['chunk_sayisi']} chunk  ·  "
            f"[dim]embedding: {rs['embedding_tipi']}[/dim]"
        )

        # Rapor bölümleriyle eşleşen çok yönlü sorgular
        rag_queries = [
            "teknik mimari sistem tasarımı algoritma",
            "metodoloji araştırma yöntemi yaklaşım",
            "temel bulgular deneysel sonuçlar performans",
            "karşılaştırmalı analiz değerlendirme kıyaslama",
            "sınırlılıklar açık problemler gelecek çalışma",
            "literatür arka plan teorik çerçeve",
        ]

        all_hits: list[dict] = []
        seen_keys: set[tuple] = set()
        for q in rag_queries:
            for hit in rag_store.query(q, top_k=rag_top_k):
                key = (hit["url"], hit["text"][:80])
                if key not in seen_keys:
                    seen_keys.add(key)
                    all_hits.append(hit)

        # Skora göre sırala ve en iyi chunk'ları al
        all_hits.sort(key=lambda h: h["score"], reverse=True)
        synthesis_input = rag_store.format_context(all_hits)
        log.info(
            f"[bright_yellow]RAG:[/bright_yellow] "
            f"{len(all_hits)} chunk retrieval edildi "
            f"({len(rag_queries)} farklı sorgu)",
            i=1,
        )

    # ── CLARIFICATION: model ne bilmesi gerektiğini sorar ─────────────────
    user_qa_block = ""
    if clarification:
        log.section("CLARIFICATION — Model Soruları", style="bold bright_cyan")
        log.step(
            "Model, final raporu yazmadan önce eksik noktaları belirliyor…"
        )

        clar_prompt = build_clarification_prompt(
            n_batches   = stats.batches_done,
            n_sources   = stats.total_fetched,
            all_outputs = synthesis_input[:6000],   # özet kısım yeter
            language    = language,
        )
        raw_clar = ask_llm(clar_prompt, cfg, stats)

        # JSON parse
        cleaned_clar = raw_clar.strip()
        if cleaned_clar.startswith("```"):
            cleaned_clar = re.sub(r'^```[a-zA-Z]*\n?', '', cleaned_clar)
            cleaned_clar = re.sub(r'\n?```$', '', cleaned_clar.strip())

        questions: list[dict] = []
        try:
            parsed_clar = json.loads(cleaned_clar)
            questions   = parsed_clar.get("questions", [])
        except json.JSONDecodeError:
            log.warning(
                "[bright_yellow]Clarification JSON parse hatası — "
                "soru aşaması atlanıyor.[/bright_yellow]"
            )

        if questions:
            log.success(
                f"Model [bright_white]{len(questions)}[/bright_white] soru üretti."
            )
            user_qa_block = collect_user_answers(questions, language)
            if user_qa_block:
                log.success("Kullanıcı cevapları final prompt'a eklenecek.")
            else:
                log.info("Tüm sorular atlandı — clarification bilgisi olmadan devam ediliyor.")
        else:
            log.info(
                "Model ek bilgiye ihtiyaç duymadı — "
                "doğrudan final rapora geçiliyor."
            )

    # ── Final LLM Çağrısı ─────────────────────────────────────────────────────
    if rag_store is not None:
        # RAG modu: retrieval chunk'larından direkt rapor
        final_prompt = build_rag_final_prompt(
            n_sources       = stats.total_fetched,
            rag_context     = synthesis_input,
            language        = language,
            user_answers    = user_qa_block,
            source_registry = source_registry,
            intent          = intent,
        )
    else:
        # Normal mod: batch analizlerinden rapor
        final_prompt = build_final_prompt(
            n_batches       = stats.batches_done,
            n_sources       = stats.total_fetched,
            n_chars         = f"{stats.total_chars:,}",
            all_outputs     = synthesis_input,
            language        = language,
            rag_context     = "",
            user_answers    = user_qa_block,
            source_registry = source_registry,
            intent          = intent,
        )

    MAX_FINAL_RETRIES = 3
    final_text = None

    for attempt in range(1, MAX_FINAL_RETRIES + 1):
        raw = ask_llm(final_prompt, cfg, stats)

        # JSON parse: markdown code fence varsa temizle
        cleaned = raw.strip()
        if cleaned.startswith("```"):
            cleaned = re.sub(r'^```[a-zA-Z]*\n?', '', cleaned)
            cleaned = re.sub(r'\n?```$', '', cleaned.strip())

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError:
            log.warning(
                f"[bright_yellow]Final rapor JSON parse hatası "
                f"(deneme {attempt}/{MAX_FINAL_RETRIES})[/bright_yellow] — "
                f"Doğrudan metin olarak kabul ediliyor."
            )
            # JSON değil ama içerik var → doğrudan kullan (geçmiş davranışla uyumlu)
            final_text = raw
            break

        if parsed.get("is_final_report") is True:
            report = parsed.get("report", "").strip()
            if report:
                log.success("Final rapor JSON'dan başarıyla çıkarıldı.")
                final_text = report
                break
            else:
                log.warning(
                    f"[bright_yellow]is_final_report=true ama 'report' alanı boş "
                    f"(deneme {attempt}/{MAX_FINAL_RETRIES})[/bright_yellow]"
                )
        else:
            # LLM raporu tamamlayamadı — kullanıcıya bildir ve girdi iste
            message      = parsed.get("message", "")
            needed_input = parsed.get("needed_input", "")

            log.warning("[bright_yellow]LLM final raporu oluşturmadı.[/bright_yellow]")
            console.print()
            console.print(Panel(
                f"[bold bright_yellow]⚠  Model final raporu oluşturmadı[/bold bright_yellow]\n\n"
                f"[white]{message}[/white]\n\n"
                f"[bold bright_cyan]Gerekli bilgi:[/bold bright_cyan] "
                f"[white]{needed_input}[/white]",
                title="[bold]Kullanıcı Girdisi Gerekiyor[/bold]",
                border_style="bright_yellow",
                padding=(1, 2),
            ))
            console.print()

            if attempt < MAX_FINAL_RETRIES:
                try:
                    user_input = input("✏  Cevabınızı girin (boş bırakırsanız atlanır): ").strip()
                except EOFError:
                    user_input = ""

                if user_input:
                    log.info(f"Kullanıcı girdisi alındı, final prompt'a ekleniyor…")
                    # Mevcut clarification cevaplarına retry girdisini de ekle
                    combined_qa = "\n\n".join(filter(None, [user_qa_block,
                                                            f"RETRY EK BİLGİSİ:\n{user_input}"]))
                    if rag_store is not None:
                        final_prompt = build_rag_final_prompt(
                            n_sources       = stats.total_fetched,
                            rag_context     = synthesis_input,
                            language        = language,
                            user_answers    = combined_qa,
                            source_registry = source_registry,
                            intent          = intent,
                        )
                    else:
                        final_prompt = build_final_prompt(
                            n_batches       = stats.batches_done,
                            n_sources       = stats.total_fetched,
                            n_chars         = f"{stats.total_chars:,}",
                            all_outputs     = "\n\n".join(history),
                            language        = language,
                            rag_context     = "",
                            user_answers    = combined_qa,
                            source_registry = source_registry,
                            intent          = intent,
                        )
                else:
                    log.warning("Kullanıcı girdi vermedi — bir sonraki denemeye geçiliyor.")

    if final_text is None:
        log.error(
            f"Final rapor {MAX_FINAL_RETRIES} denemede oluşturulamadı — çıkılıyor."
        )
        sys.exit(1)

    # ── KAYIT ──────────────────────────────────────────────────────────────────
    log.rule("Kayıt", style="bright_green")
    fmt = output_format.lower()

    if fmt == "pdf":
        log.step("Markdown → PDF dönüşümü başlatılıyor…", i=1)
        save_pdf(final_text, output_path)
    elif fmt == "docx":
        save_docx(final_text, output_path)
    elif fmt == "json":
        save_json({
            "meta": {
                "backend": cfg["backend"], "model": cfg["model"],
                "batches": stats.batches_done,
                "total_urls_processed": stats.total_fetched,
                "generated_at": datetime.now().isoformat(),
                "elapsed_sec": round(time.time() - stats.start_time, 1),
            },
            "batches": all_batch_data,
            "final_report": final_text,
        }, output_path)
    else:
        # md veya txt — düz metin olarak kaydet
        save_txt(final_text, output_path)

    log.save(
        f"[bold bright_green]Rapor kaydedildi:[/bold bright_green] "
        f"[underline]{output_path}[/underline]  [dim]({fmt})[/dim]"
    )

    if not log.quiet:
        stats.print_batch_table()
        stats.print_summary()
        console.print()
        console.print(Align.center(
            f"[bold bright_green]✅ Tamamlandı[/bold bright_green]  "
            f"[dim]{stats.elapsed()}[/dim]"
        ))
        console.print()


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def build_parser():
    p = argparse.ArgumentParser(
        prog="analizkasar",
        description="Analizkasar – tüm URL'leri işler, model bağlantı takip edebilir",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Örnekler:
  # Varsayılan çıktı: PDF
  python main.py --urls urls.txt

  # DOCX çıktısı:
  python main.py --urls urls.txt --format docx -o rapor.docx

  # Markdown çıktısı:
  python main.py --urls urls.txt --format md -o rapor.md

  # JSON çıktısı:
  python main.py --urls urls.txt --format json -o rapor.json

  # OpenAI + PDF:
  python main.py --backend openai --model gpt-4o \\
      --urls urls.txt --format pdf -o rapor.pdf

  # Verbose modda:
  python main.py --urls urls.txt --verbose
        """,
    )

    src = p.add_argument_group("📂 Kaynak")
    src.add_argument("--urls", "-u", metavar="FILE",
                     help="Her satırda bir URL içeren dosya")
    src.add_argument("--url", action="append", dest="extra_urls", metavar="URL",
                     help="Tek URL ekle (birden fazla kullanılabilir)")

    llm = p.add_argument_group("🤖 LLM Backend")
    llm.add_argument("--backend", "-b", choices=BACKENDS, default="ollama")
    llm.add_argument("--model",   "-m", metavar="MODEL",
                     help="Model adı (varsayılan backend'e göre otomatik)")
    llm.add_argument("--list-models", action="store_true")

    be = p.add_argument_group("🔑 Backend Kimlik Bilgileri")
    be.add_argument("--ollama-host",       default="http://localhost:11434", metavar="URL")
    be.add_argument("--openai-api-key",    metavar="KEY", help="(env: OPENAI_API_KEY)")
    be.add_argument("--openai-base-url",   metavar="URL")
    be.add_argument("--anthropic-api-key", metavar="KEY", help="(env: ANTHROPIC_API_KEY)")
    be.add_argument("--groq-api-key",      metavar="KEY", help="(env: GROQ_API_KEY)")
    be.add_argument("--lmstudio-url",      default="http://localhost:1234", metavar="URL")

    ag = p.add_argument_group("⚙️  Agent Ayarları")
    ag.add_argument(
        "--batch-size", "-s", type=int, default=15, metavar="N",
        help="Tek LLM çağrısında işlenecek URL sayısı (varsayılan: 15)",
    )
    ag.add_argument(
        "--max-extra-links", type=int, default=50, metavar="N",
        help="Model tarafından LINK_REQUEST ile talep edilebilecek maksimum bağlantı sayısı "
             "(varsayılan: 50). 0 = sınırsız.",
    )
    ag.add_argument("--delay",          type=float, default=0.5, metavar="SEC",
                    help="Batch'ler arası bekleme süresi (varsayılan: 0.5)")
    ag.add_argument("--scrape-timeout", type=int,   default=15,  metavar="SEC")
    ag.add_argument("--max-chars",      type=int,   default=20_000, metavar="N",
                    help="Kaynak başına maksimum karakter (varsayılan: 20000)")
    ag.add_argument(
        "--no-thematic-synthesis", dest="no_thematic_synthesis",
        action="store_true", default=False,
        help=(
            "Tematik gruplandırma + derinleştirilmiş sentez aşamasını devre dışı bırakır. "
            "Varsayılan: etkin (batch sayısı ≥ 2 olduğunda çalışır)."
        ),
    )

    rag = p.add_argument_group("🔍 RAG (Retrieval-Augmented Generation)")
    rag.add_argument(
        "--rag", action="store_true", default=False,
        help=(
            "RAG'ı etkinleştir: tüm fetch edilen içerik chunk'lanır ve "
            "vektör deposuna eklenir; her LLM çağrısında ilgili chunk'lar "
            "prompt'a enjekte edilir. (varsayılan: kapalı)"
        ),
    )
    rag.add_argument(
        "--rag-chunk-size", type=int, default=1000, metavar="N",
        help="Her chunk'ın maksimum karakter sayısı (varsayılan: 1000)",
    )
    rag.add_argument(
        "--rag-chunk-overlap", type=int, default=200, metavar="N",
        help="Ardışık chunk'lar arasındaki örtüşme (varsayılan: 200)",
    )
    rag.add_argument(
        "--rag-top-k", type=int, default=5, metavar="N",
        help="Her retrieval sorgusunda döndürülecek chunk sayısı (varsayılan: 5)",
    )
    rag.add_argument(
        "--rag-embedding-model", default="all-MiniLM-L6-v2", metavar="MODEL",
        help=(
            "sentence-transformers model adı (varsayılan: all-MiniLM-L6-v2). "
            "sentence-transformers yüklü değilse TF-IDF geri dönüşü kullanılır."
        ),
    )

    clar = p.add_argument_group("💬 Clarification (Final Rapor Öncesi Soru–Cevap)")
    clar.add_argument(
        "--no-clarification", dest="no_clarification",
        action="store_true", default=False,
        help=(
            "Final rapor yazmadan önce modelin kullanıcıya soru sormasını devre dışı bırakır. "
            "CI/pipe ortamları veya tam otomatik çalıştırma için kullanın. "
            "Varsayılan: clarification açık."
        ),
    )

    pi = p.add_argument_group("🎯 Başlangıç Promptu")
    pi.add_argument(
        "--prompt", metavar="TOPIC",
        help=(
            "Araştırma konusunu doğrudan belirt; interaktif giriş ekranını atlar. "
            "Örnek: --prompt \"Transformer modelleri ile protein yapı tahmini\""
        ),
    )
    pi.add_argument(
        "--no-prompt", dest="no_prompt",
        action="store_true", default=False,
        help=(
            "Kullanıcı giriş ekranını tamamen atla. "
            "CI/pipe/otomatik çalıştırma için kullanın. "
            "Varsayılan: giriş ekranı açık."
        ),
    )

    out = p.add_argument_group("💾 Çıktı")
    out.add_argument("--output", "-o", default="rapor.pdf", metavar="FILE",
                     help="Çıktı dosyası (varsayılan: rapor.pdf)")
    out.add_argument(
        "--format", "-f",
        choices=OUTPUT_FORMATS,
        metavar="|".join(OUTPUT_FORMATS),
        help=(
            "Çıktı formatı:\n"
            "  pdf   – Markdown → ReportLab PDF  [varsayılan]\n"
            "  docx  – Microsoft Word\n"
            "  md    – Ham Markdown\n"
            "  txt   – Düz metin\n"
            "  json  – Tüm batch verileri + final rapor\n"
        ),
    )
    out.add_argument("--save-intermediate", action="store_true",
                     help="Her batch sonunda ara çıktıyı .txt olarak kaydet")

    lang = p.add_argument_group("🌍 Dil")
    lang.add_argument(
        "--language", "-l", metavar="LANG", default="Turkish",
        help="Rapor dili (varsayılan: Turkish). Örnek: English, German, Arabic",
    )

    verb = p.add_argument_group("🔊 Log Seviyesi")
    grp  = verb.add_mutually_exclusive_group()
    grp.add_argument("--quiet",   "-q", action="store_true")
    grp.add_argument("--verbose", "-v", action="store_true")

    return p


def resolve_format(output: str, fmt_arg: str | None) -> str:
    """
    Format önceliği:
    1. --format argümanı açıkça verilmişse → onu kullan
    2. Dosya uzantısı bilinen bir format ise → uzantıyı kullan
    3. Varsayılan → pdf
    """
    if fmt_arg:
        return fmt_arg
    ext = Path(output).suffix.lower().lstrip(".")
    return ext if ext in OUTPUT_FORMATS else "pdf"


def load_urls(args):
    urls = []
    if args.urls:
        path = Path(args.urls)
        if not path.exists():
            raise SystemExit(f"❌ URL dosyası bulunamadı: {args.urls}")
        urls += [
            line.strip()
            for line in path.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        ]
    if args.extra_urls:
        urls += args.extra_urls
    if not urls:
        raise SystemExit("❌ Hiç URL belirtilmedi. --urls veya --url kullanın.")
    return urls


def main():
    global log
    parser = build_parser()
    args   = parser.parse_args()
    log    = Logger(quiet=args.quiet, verbose=args.verbose)

    if args.list_models:
        t = Table(title="Varsayılan Modeller", box=box.ROUNDED,
                  border_style="bright_black", header_style="bold cyan")
        t.add_column("Backend", style="bright_cyan", min_width=12)
        t.add_column("Model",   style="bright_yellow")
        for k, v in DEFAULT_MODELS.items():
            bc = BACKEND_COLORS.get(k, "white")
            t.add_row(f"[{bc}]{k}[/{bc}]", v)
        console.print(t)
        sys.exit(0)

    backend = args.backend
    model   = args.model or DEFAULT_MODELS[backend]
    fmt     = resolve_format(args.output, args.format)

    cfg = {
        "backend":           backend,
        "model":             model,
        "ollama_host":       args.ollama_host,
        "openai_api_key":    args.openai_api_key,
        "openai_base_url":   args.openai_base_url,
        "anthropic_api_key": args.anthropic_api_key,
        "groq_api_key":      args.groq_api_key,
        "lmstudio_url":      args.lmstudio_url,
    }

    language = args.language

    urls = load_urls(args)

    # ── Kullanıcı niyeti toplama ───────────────────────────────────────────────
    intent: UserIntent | None = None
    if not args.no_prompt:
        intent = collect_user_intent(preset_topic=args.prompt or "")
    elif args.prompt:
        # --no-prompt + --prompt: sadece konuyu kaydet, ekran gösterme
        intent = UserIntent(
            topic       = args.prompt,
            output_type = "Akademik Makale",
            audience    = "",
            focus       = "",
            constraints = "",
        )

    run_agent(
        initial_urls=urls,
        cfg=cfg,
        batch_size=args.batch_size,
        delay=args.delay,
        output_path=args.output,
        output_format=fmt,
        scrape_timeout=args.scrape_timeout,
        max_chars=args.max_chars,
        save_intermediate=args.save_intermediate,
        max_extra_links=args.max_extra_links,
        language=language,
        thematic_synthesis=not args.no_thematic_synthesis,
        rag=args.rag,
        rag_chunk_size=args.rag_chunk_size,
        rag_chunk_overlap=args.rag_chunk_overlap,
        rag_top_k=args.rag_top_k,
        rag_embedding_model=args.rag_embedding_model,
        clarification=not args.no_clarification,
        intent=intent,
    )


if __name__ == "__main__":
    main()