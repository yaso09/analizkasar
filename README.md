# 🔬 Analizkasar

# Analizkasar

URL listesini alır, her sayfayı scrape eder ve LLM aracılığıyla akademik bir araştırma raporu üretir. Model, sayfalardan bulduğu bağlantıları takip edebilir; RAG modu etkinleştirildiğinde tüm içerik vektör deposuna yüklenir ve retrieval üzerinden rapor yazılır.

## Gereksinimler

- Python 3.10 veya üzeri
- Ollama kurulu ve çalışır durumda (yerel model kullanıyorsanız)
- Bulut API kullanıyorsanız ilgili servis için API anahtarı (bkz. [Ortam Değişkenleri](#ortam-değişkenleri))

## Kurulum

```bash
pip install requests beautifulsoup4 python-docx rich reportlab
```

RAG modu için ek bağımlılıklar:

```bash
pip install numpy sentence-transformers
```

> `sentence-transformers` yüklü değilse RAG otomatik olarak TF-IDF tabanlı geri dönüşe geçer; program yine de çalışır.

## Çalıştırma

URL'leri bir metin dosyasına koyun (her satıra bir URL, `#` ile başlayan satırlar yoksayılır):

```
https://example.com/makale-1
https://example.com/makale-2
# bu satır yoksayılır
```

Ardından çalıştırın:

```bash
python main.py --urls urls.txt
```

Varsayılan backend Ollama (`gemma3:12b`), varsayılan çıktı `rapor.pdf`.

Tek URL ile hızlı test:

```bash
python main.py --url https://example.com/makale
```

## Ortam Değişkenleri

API anahtarları argüman olarak verilebileceği gibi ortam değişkeni olarak da tanımlanabilir:

| Değişken | Açıklama |
|---|---|
| `OPENAI_API_KEY` | OpenAI API anahtarı |
| `ANTHROPIC_API_KEY` | Anthropic API anahtarı |
| `GROQ_API_KEY` | Groq API anahtarı |

```bash
export ANTHROPIC_API_KEY=sk-ant-...
python main.py --urls urls.txt --backend anthropic
```

## Komutlar

### Backend seçimi

```bash
# Ollama (varsayılan)
python main.py --urls urls.txt --backend ollama --model qwen3:30b-a3b

# OpenAI
python main.py --urls urls.txt --backend openai --model gpt-4o

# Anthropic
python main.py --urls urls.txt --backend anthropic

# Groq
python main.py --urls urls.txt --backend groq

# LM Studio
python main.py --urls urls.txt --backend lmstudio
```

Desteklenen tüm backend'leri ve varsayılan modellerini listelemek için:

```bash
python main.py --list-models
```

### Çıktı formatı

```bash
python main.py --urls urls.txt -o rapor.pdf     # PDF (varsayılan)
python main.py --urls urls.txt -o rapor.docx    # Word
python main.py --urls urls.txt -o rapor.md      # Markdown
python main.py --urls urls.txt -o rapor.txt     # Düz metin
python main.py --urls urls.txt -o rapor.json    # JSON (batch verileri + rapor)
```

Uzantı formatı otomatik olarak belirler; `--format` ile geçersiz kılınabilir.

### RAG modu

Çok sayıda kaynak için uygundur. Bu modda batch LLM analizi yapılmaz; tüm kaynaklar indekslendikten sonra retrieval üzerinden tek seferde rapor yazılır.

```bash
python main.py --urls urls.txt --rag
python main.py --urls urls.txt --rag --rag-top-k 10 --rag-chunk-size 1500
```

### Otomatik / CI pipeline

```bash
python main.py --urls urls.txt --no-clarification --quiet -o rapor.pdf
```

## Tüm Seçenekler

### Kaynak

| Argüman | Açıklama |
|---|---|
| `--urls`, `-u` FILE | Her satırda bir URL içeren dosya |
| `--url` URL | Tek URL ekle (birden fazla kullanılabilir) |

### LLM Backend

| Argüman | Varsayılan | Açıklama |
|---|---|---|
| `--backend`, `-b` | `ollama` | `ollama`, `openai`, `anthropic`, `groq`, `lmstudio` |
| `--model`, `-m` | backend'e göre | Model adı |
| `--ollama-host` | `http://localhost:11434` | Ollama sunucu adresi |
| `--lmstudio-url` | `http://localhost:1234` | LM Studio sunucu adresi |

### Agent Ayarları

| Argüman | Varsayılan | Açıklama |
|---|---|---|
| `--batch-size`, `-s` | `15` | Tek LLM çağrısında işlenecek URL sayısı |
| `--max-extra-links` | `50` | `LINK_REQUEST` ile talep edilebilecek maks. bağlantı (`0` = sınırsız) |
| `--delay` | `0.5` | Batch'ler arası bekleme süresi (saniye) |
| `--scrape-timeout` | `15` | Fetch zaman aşımı (saniye) |
| `--max-chars` | `20000` | Kaynak başına maksimum karakter |
| `--no-thematic-synthesis` | — | Tematik gruplama + sentez aşamasını devre dışı bırakır |

### RAG

| Argüman | Varsayılan | Açıklama |
|---|---|---|
| `--rag` | kapalı | RAG modunu etkinleştirir |
| `--rag-chunk-size` | `1000` | Chunk başına maksimum karakter |
| `--rag-chunk-overlap` | `200` | Ardışık chunk'lar arasındaki örtüşme |
| `--rag-top-k` | `5` | Retrieval sorgusu başına döndürülecek chunk sayısı |
| `--rag-embedding-model` | `all-MiniLM-L6-v2` | sentence-transformers model adı |

### Clarification

| Argüman | Açıklama |
|---|---|
| `--no-clarification` | Final rapor öncesi kullanıcı soru-cevap aşamasını devre dışı bırakır |

### Çıktı

| Argüman | Varsayılan | Açıklama |
|---|---|---|
| `--output`, `-o` | `rapor.pdf` | Çıktı dosya yolu |
| `--format`, `-f` | uzantıdan | `pdf`, `docx`, `md`, `txt`, `json` |
| `--save-intermediate` | — | Her batch sonunda ara çıktıyı `.txt` olarak kaydet |
| `--language`, `-l` | `Turkish` | Rapor dili (`English`, `German`, `Arabic` …) |

### Log Seviyesi

| Argüman | Açıklama |
|---|---|
| `--quiet`, `-q` | Yalnızca hata mesajlarını göster |
| `--verbose`, `-v` | Debug çıktısını etkinleştir |

## Katkıda Bulunma

1. Repo'yu fork'layın ve yeni bir branch açın: `git checkout -b ozellik/aciklama`
2. Değişikliklerinizi yapın ve commit'leyin.
3. Pull request açın; açıklamaya ne değiştiğini ve neden yazın.

Büyük değişiklikler için önce bir issue açıp tartışmaya başlamanız önerilir.

## Lisans

GPLv3