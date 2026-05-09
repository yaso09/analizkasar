# 🔬 Analizkasar

> **Iteratif web araştırması ve LLM sentezi için otonom komut satırı aracı.**
> URL listesini alır, sayfaları tarar, model aracılığıyla analiz eder, bağlantıları takip eder ve akademik rapor üretir.

**Yazar:** Yasir Eymen KAYABAŞI · **Versiyon:** 0.1

---

## İçindekiler

1. [Genel Bakış](#genel-bakış)
2. [Nasıl Çalışır](#nasıl-çalışır)
3. [Kurulum](#kurulum)
4. [Hızlı Başlangıç](#hızlı-başlangıç)
5. [Desteklenen LLM Backend'leri](#desteklenen-llm-backendleri)
6. [Canlı Streaming ve Düşünce Akışı](#canlı-streaming-ve-düşünce-akışı)
7. [Çıktı Formatları](#çıktı-formatları)
8. [Tüm Argümanlar](#tüm-argümanlar)
9. [Örnek Kullanımlar](#örnek-kullanımlar)
10. [Agent Döngüsü Detayı](#agent-döngüsü-detayı)
11. [İstatistik ve Loglama](#istatistik-ve-loglama)
12. [Bağımlılıklar](#bağımlılıklar)
13. [Sık Sorulan Sorular](#sık-sorulan-sorular)

---

## Genel Bakış

Analizkasar, bir URL listesini girdi olarak alır ve şu işlemleri otonom olarak gerçekleştirir:

- Sayfaları batch'ler hâlinde indirir ve ham metnini çıkarır
- Seçtiğiniz LLM backend'i üzerinden her batch için derin teknik analiz yapar; token'lar terminale canlı akar
- Anthropic düşünen modellerinde extended thinking akışını ayrı bir panelde gösterir
- Modelin `LINK_REQUEST:` direktifiyle talep ettiği yeni bağlantıları öncelikli olarak kuyruğa ekler
- Modelin `NEW_SOURCE:` direktifiyle önerdiği ek kaynakları normal sırayla kuyruğa ekler
- Tüm batch analizlerini birleştirerek tek bir bütünlüklü akademik rapor üretir
- Final raporu JSON doğrulamasıyla alır; model raporu tamamlayamazsa kullanıcıdan ek girdi ister ve yeniden dener
- Raporu seçilen dilde PDF, DOCX, Markdown, düz metin veya JSON formatında dışa aktarır

---

## Nasıl Çalışır

```
┌─────────────────────────────────────────────────────────┐
│                    URL Kuyruğu                          │
│  [url1, url2, url3, ..., urlN]                          │
└──────────────────────┬──────────────────────────────────┘
                       │  batch_size kadar URL al
                       ▼
┌─────────────────────────────────────────────────────────┐
│                  Web Scraper                            │
│  • HTTP GET → BeautifulSoup metin çıkarma               │
│  • Sayfa içi bağlantıları topla (PAGE_LINKS)            │
│  • Maksimum max_chars karakter al                       │
└──────────────────────┬──────────────────────────────────┘
                       │  ham içerik + PAGE_LINKS
                       ▼
┌─────────────────────────────────────────────────────────┐
│          LLM Analiz  (canlı streaming)                  │
│  • [Anthropic thinking modelleri] düşünce paneli        │
│  • Token token terminal çıktısı                         │
│  • Teknik anlama & çapraz kaynak sentezi                │
│  • LINK_REQUEST: → kuyruğun BAŞINA ekle (öncelikli)     │
│  • NEW_SOURCE:   → kuyruğun SONUNA ekle (normal)        │
└──────────────────────┬──────────────────────────────────┘
                       │
          ┌────────────┴────────────┐
          │  Kuyrukta URL var mı?   │
          │  Evet → döngü devam     │
          │  Hayır → Final Rapor    │
          └─────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│          Final LLM Çağrısı (JSON doğrulamalı)           │
│  • Model { "is_final_report": true, "report": "..." }   │
│    döndürürse rapor çıkarılır                           │
│  • false döndürürse kullanıcıdan girdi istenir,         │
│    maks. 3 deneme yapılır                               │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
            PDF / DOCX / MD / TXT / JSON
```

### Batch Döngüsü

Her batch şunları içerir:

1. Kuyruktan `--batch-size` kadar URL alınır (tekrar fetch edilmeyenler)
2. Her URL paralel değil, sıralı olarak indirilir (rate limit dostu)
3. Toplanan içerik tek bir LLM prompt'una gönderilir; yanıt terminale canlı akar
4. Model çıktısından `LINK_REQUEST:` ve `NEW_SOURCE:` satırları ayrıştırılır
5. Yeni URL'ler kuyruğa eklenir; döngü devam eder

---

## Kurulum

### Gereksinimler

- Python 3.10+
- pip

### Adım 1 — Depoyu Klonlayın veya Script'i İndirin

```bash
git clone https://github.com/yaso09/analizkasar.git
cd analizkasar
```

### Adım 2 — Bağımlılıkları Kurun

```bash
pip install requests beautifulsoup4 python-docx rich reportlab
```

Kullanmak istediğiniz backend'e göre ek paket:

| Backend   | Ek paket                |
|-----------|-------------------------|
| Ollama    | `pip install ollama`    |
| OpenAI    | `pip install openai`    |
| Anthropic | `pip install anthropic` |
| Groq      | `pip install groq`      |
| LM Studio | *(ek paket gerekmez)*   |

RAG modu için:

```bash
pip install numpy sentence-transformers
```

> `sentence-transformers` yüklü değilse RAG otomatik olarak TF-IDF tabanlı geri dönüşe geçer; program yine de çalışır.

### Adım 3 — Ortam Değişkenlerini Ayarlayın

Bulut backend'leri için API anahtarları ortam değişkeni olarak tanımlanabilir:

| Değişken            | Açıklama             |
|---------------------|----------------------|
| `OPENAI_API_KEY`    | OpenAI API anahtarı  |
| `ANTHROPIC_API_KEY` | Anthropic API anahtarı |
| `GROQ_API_KEY`      | Groq API anahtarı    |

```bash
export ANTHROPIC_API_KEY="sk-ant-..."
export OPENAI_API_KEY="sk-..."
export GROQ_API_KEY="gsk_..."
```

Anahtarlar `--openai-api-key`, `--anthropic-api-key`, `--groq-api-key` argümanlarıyla da verilebilir.

---

## Hızlı Başlangıç

### 1. URL Dosyası Hazırlayın

`urls.txt` dosyası — her satırda bir URL, `#` ile başlayan satırlar yorum:

```
# Araştırma konusu: Transformer mimarileri
https://arxiv.org/abs/1706.03762
https://arxiv.org/abs/2005.14165
https://huggingface.co/docs/transformers/index
# Ek kaynaklar
https://jalammar.github.io/illustrated-transformer/
```

### 2. Çalıştırın

```bash
# Varsayılan: Ollama backend, PDF çıktısı, Türkçe rapor
python main.py --urls urls.txt

# Anthropic + PDF + İngilizce rapor
python main.py --backend anthropic --urls urls.txt -o rapor.pdf --language English

# OpenAI + JSON
python main.py --backend openai --urls urls.txt --format json -o rapor.json
```

---

## Desteklenen LLM Backend'leri

### Ollama (varsayılan)

Yerel olarak çalışır, API anahtarı gerekmez. Streaming desteklenir.

```bash
python main.py \
  --backend ollama \
  --model gemma3:12b \
  --ollama-host http://localhost:11434 \
  --urls urls.txt
```

Varsayılan model: `gemma3:12b`

---

### OpenAI

Streaming desteklenir.

```bash
python main.py \
  --backend openai \
  --model gpt-4o \
  --openai-api-key sk-... \
  --urls urls.txt
```

`--openai-base-url` ile uyumlu üçüncü taraf endpoint'ler desteklenir (örn. Azure OpenAI).

Varsayılan model: `gpt-4o`

---

### Anthropic

Streaming ve extended thinking desteklenir.

```bash
python main.py \
  --backend anthropic \
  --model claude-opus-4-5 \
  --anthropic-api-key sk-ant-... \
  --urls urls.txt
```

Thinking destekleyen modellerde **extended thinking** otomatik olarak etkinleştirilir; düşünce akışı terminalde ayrı bir panelde gösterilir. Eski modeller düz streaming'e otomatik olarak düşer.

Varsayılan model: `claude-opus-4-5`

---

### Groq

Streaming desteklenir.

```bash
python main.py \
  --backend groq \
  --model llama-3.3-70b-versatile \
  --groq-api-key gsk_... \
  --urls urls.txt
```

Varsayılan model: `llama-3.3-70b-versatile`

---

### LM Studio

SSE (Server-Sent Events) üzerinden streaming desteklenir.

```bash
python main.py \
  --backend lmstudio \
  --model local-model \
  --lmstudio-url http://localhost:1234 \
  --urls urls.txt
```

LM Studio'nun OpenAI uyumlu `/v1/chat/completions` endpoint'i kullanılır.

Varsayılan model: `local-model`

---

### Tüm Varsayılan Modelleri Görüntüle

```bash
python main.py --list-models
```

---

## Canlı Streaming ve Düşünce Akışı

Tüm backend'ler tam streaming modunda çalışır. Her LLM çağrısında token'lar terminale anında basılır; tüm yanıt belleğe alınıp toplu gösterilmez.

### Genel Akış Görünümü

```
── akış başlıyor ──────────────────────────────────────────
Bu batch'teki kaynaklar transformer mimarisinin temel bileşenlerini...
...analiz etmektedir. Multi-head attention mekanizması açısından...
── akış bitti ─────────────────────────────────────────────
```

### Anthropic Extended Thinking

Thinking destekleyen modellerde model yanıt üretmeden önce bir "düşünce" adımı çalıştırır. Bu adım terminalde soluk renkli bir panel içinde canlı olarak izlenebilir:

```
╭─────────────────── 🧠 Düşünce akışı ──────────────────────╮
│ Kaynaklarda geçen attention mekanizması açıklamalarını    │
│ karşılaştırmam gerekiyor. İlk kaynak scaled dot-product   │
│ formülünü detaylı veriyor, ikinci kaynak ise...           │
╰───────────────────────────────────────────────────────────╯
  🧠 Düşünce: 3,241 karakter
```

Düşünce paneli kapandıktan sonra asıl yanıt metninin akışı başlar. Düşünce içeriği nihai rapora veya çıktı dosyasına dahil edilmez; yalnızca terminalde gösterilir.

---

## Çıktı Formatları

| Format | Uzantı | Açıklama |
|--------|--------|----------|
| `pdf`  | `.pdf`  | **Varsayılan.** Markdown → ReportLab ile biçimlendirilmiş PDF. Başlıklar, paragraflar, listeler, kod blokları, alıntılar render edilir. |
| `docx` | `.docx` | Microsoft Word belgesi. |
| `md`   | `.md`   | Ham Markdown. LLM'nin ürettiği metin, işlenmeden kaydedilir. |
| `txt`  | `.txt`  | Düz metin. |
| `json` | `.json` | Tüm batch verileri + final rapor. Programatik işleme için idealdir. |

### Format Seçim Önceliği

1. `--format` argümanı açıkça verilmişse → kullanılır
2. `--output` dosyasının uzantısı tanınan bir format ise → uzantı kullanılır
3. Hiçbiri yoksa → `pdf` varsayılan

```bash
python main.py --urls urls.txt -o rapor.docx          # → docx
python main.py --urls urls.txt -o sonuc.txt --format md  # → md (format öncelikli)
```

### PDF Yapısı

| Markdown | PDF karşılığı |
|----------|---------------|
| `# Başlık` | H1 — büyük, koyu, lacivert |
| `## Başlık` | H2 — orta, koyu |
| `### Başlık` | H3 — küçük, koyu, mavi |
| `**metin**` | Kalın |
| `*metin*` | İtalik |
| `` `kod` `` | Courier yazı tipi |
| ```` ```blok``` ```` | Gri arka planlı kod kutusu |
| `> alıntı` | Soldan girintili italik |
| `- madde` | Madde listesi |
| `1. madde` | Numaralı liste |
| `---` | Yatay çizgi |

### JSON Yapısı

```json
{
  "meta": {
    "backend": "anthropic",
    "model": "claude-opus-4-5",
    "batches": 4,
    "total_urls_processed": 52,
    "generated_at": "2025-01-15T14:32:00",
    "elapsed_sec": 187.3
  },
  "batches": [
    {
      "batch": 1,
      "urls": ["https://..."],
      "fetched": 15,
      "failed": 0,
      "chars": 284920,
      "link_reqs": 3,
      "new_urls": 2,
      "llm_secs": 12.4,
      "secs": 18.7,
      "analysis": "..."
    }
  ],
  "final_report": "# Araştırma Raporu\n\n## 1. Abstract\n..."
}
```

---

## Tüm Argümanlar

### 📂 Kaynak

| Argüman | Kısaltma | Tür | Açıklama |
|---------|----------|-----|----------|
| `--urls` | `-u` | dosya yolu | Her satırda bir URL içeren metin dosyası. `#` ile başlayan satırlar yorum olarak atlanır. |
| `--url` | — | URL | Tek bir URL ekler. Birden fazla kez kullanılabilir: `--url https://a.com --url https://b.com` |

En az biri zorunludur. İkisi birlikte kullanılabilir; URL'ler birleştirilir.

---

### 🤖 LLM Backend

| Argüman | Kısaltma | Varsayılan | Açıklama |
|---------|----------|------------|----------|
| `--backend` | `-b` | `ollama` | LLM sağlayıcısı: `ollama` `openai` `anthropic` `groq` `lmstudio` |
| `--model` | `-m` | *(backend'e göre)* | Model adı. Belirtilmezse her backend için otomatik varsayılan seçilir. |
| `--list-models` | — | — | Tüm backend'ler için varsayılan modelleri tabloda gösterir ve çıkar. |

---

### 🔑 Backend Kimlik Bilgileri

| Argüman | Ortam değişkeni | Varsayılan |
|---------|----------------|------------|
| `--ollama-host` | — | `http://localhost:11434` |
| `--openai-api-key` | `OPENAI_API_KEY` | — |
| `--openai-base-url` | — | *(OpenAI resmi endpoint)* |
| `--anthropic-api-key` | `ANTHROPIC_API_KEY` | — |
| `--groq-api-key` | `GROQ_API_KEY` | — |
| `--lmstudio-url` | — | `http://localhost:1234` |

---

### ⚙️ Agent Ayarları

| Argüman | Kısaltma | Varsayılan | Açıklama |
|---------|----------|------------|----------|
| `--batch-size` | `-s` | `15` | Tek LLM çağrısına gönderilecek maksimum URL sayısı. |
| `--max-extra-links` | — | `50` | Model `LINK_REQUEST:` ile talep edebileceği maksimum bağlantı sayısı. `0` = sınırsız. |
| `--delay` | — | `0.5` | Batch'ler arasında bekleme süresi (saniye). |
| `--scrape-timeout` | — | `15` | HTTP istek zaman aşımı (saniye). |
| `--max-chars` | — | `20000` | Kaynak başına maksimum karakter. Uzun sayfalar bu değerde kesilir. |
| `--no-thematic-synthesis` | — | kapalı | Tematik gruplama + sentez aşamasını devre dışı bırakır. |

---

### 🔍 RAG

| Argüman | Varsayılan | Açıklama |
|---------|------------|----------|
| `--rag` | kapalı | RAG modunu etkinleştirir. Batch LLM analizi yapılmaz; tüm kaynaklar indekslendikten sonra retrieval üzerinden tek seferde rapor yazılır. |
| `--rag-chunk-size` | `1000` | Chunk başına maksimum karakter. |
| `--rag-chunk-overlap` | `200` | Ardışık chunk'lar arasındaki örtüşme. |
| `--rag-top-k` | `5` | Retrieval sorgusu başına döndürülecek chunk sayısı. |
| `--rag-embedding-model` | `all-MiniLM-L6-v2` | sentence-transformers model adı. |

---

### 💬 Clarification

| Argüman | Açıklama |
|---------|----------|
| `--no-clarification` | Final rapor öncesi kullanıcı soru-cevap aşamasını devre dışı bırakır. CI/otomasyon ortamları için. |

---

### 💾 Çıktı

| Argüman | Kısaltma | Varsayılan | Açıklama |
|---------|----------|------------|----------|
| `--output` | `-o` | `rapor.pdf` | Çıktı dosyası yolu. Uzantı format belirleme için kullanılır. |
| `--format` | `-f` | *(uzantıdan)* | Çıktı formatı: `pdf` `docx` `md` `txt` `json` |
| `--save-intermediate` | — | kapalı | Her batch sonunda analizi `<çıktı>.batchN.txt` dosyasına kaydeder. |
| `--language` | `-l` | `Turkish` | Rapor dili. Hem batch analizlerine hem de final rapora uygulanır. |

---

### 🔊 Log Seviyesi

| Argüman | Kısaltma | Açıklama |
|---------|----------|----------|
| `--quiet` | `-q` | Yalnızca hata mesajlarını gösterir. |
| `--verbose` | `-v` | DEBUG dahil tüm mesajları gösterir. |

`--quiet` ve `--verbose` birlikte kullanılamaz.

---

## Örnek Kullanımlar

```bash
# Temel kullanım
python main.py --urls urls.txt

# Anthropic + PDF
python main.py --backend anthropic --model claude-opus-4-5 --urls urls.txt -o rapor.pdf

# OpenAI + Markdown
python main.py --backend openai --model gpt-4o --urls urls.txt --format md -o rapor.md

# Groq
python main.py --backend groq --model llama-3.3-70b-versatile --urls urls.txt

# RAG modu — çok sayıda kaynak
python main.py --urls urls.txt --rag --rag-top-k 10 -o rapor.docx

# İngilizce rapor
python main.py --urls urls.txt --language English -o report.pdf

# Tek URL ile hızlı test
python main.py --url https://arxiv.org/abs/1706.03762 --url https://arxiv.org/abs/2005.14165 -o rapor.pdf

# Ara çıktıları kaydet
python main.py --urls urls.txt --save-intermediate -o rapor.pdf

# Otomatik pipeline — clarification yok, sessiz mod
python main.py --urls urls.txt --no-clarification --quiet -o rapor.pdf

# JSON çıktısı — programatik işleme
python main.py --urls urls.txt --format json -o sonuclar.json

# Uzak Ollama sunucusu
python main.py --backend ollama --ollama-host http://192.168.1.100:11434 --model llama3:70b --urls urls.txt

# Azure OpenAI
python main.py --backend openai --openai-base-url https://MY_RESOURCE.openai.azure.com/ --openai-api-key MY_KEY --model gpt-4o --urls urls.txt
```

---

## Agent Döngüsü Detayı

### LINK_REQUEST Mekanizması

Model, analiz sırasında sayfanın bağlantılarından kritik olanları tespit ederse çıktısına şu satırları ekler:

```
LINK_REQUEST: https://github.com/example/repo
LINK_REQUEST: https://arxiv.org/abs/2103.00020
```

Bu URL'ler henüz fetch edilmemişse kuyruğun **başına** eklenir (öncelikli işlenir). Her batch için model en fazla **10 adet** `LINK_REQUEST` kullanabilir.

### NEW_SOURCE Mekanizması

Model, bilgi eksikliğini gidermek için yeni kaynaklar önerebilir:

```
NEW_SOURCE: https://papers.with-code.com/paper/attention-is-all-you-need
```

Bu URL'ler kuyruğun **sonuna** eklenir (normal öncelik).

### URL Tekrar Fetch Önlemi

Her URL yalnızca bir kez işlenir. `processed` kümesi aracılığıyla hem `LINK_REQUEST` hem `NEW_SOURCE` hem de orijinal listeden gelen URL'lerin tekrarlanması engellenir.

### Final Rapor — JSON Doğrulama ve Retry

Final rapor LLM'den JSON olarak istenir. Model şu iki şemadan birini döndürmek zorundadır:

```json
{ "is_final_report": true, "report": "# Araştırma Raporu\n..." }
{ "is_final_report": false, "message": "...", "needed_input": "..." }
```

`is_final_report` değeri `false` gelirse terminalde uyarı paneli gösterilir ve kullanıcıdan ek bilgi istenir. Girilen bilgi prompt'a eklenerek LLM yeniden çağrılır. İşlem en fazla **3 kez** tekrarlanır. Model geçersiz JSON döndürürse ham metin doğrudan rapor olarak kullanılır.

---

## İstatistik ve Loglama

Her çalışma sonunda terminal çıktısında iki tablo görünür:

### Batch Detay Tablosu

```
┃ Batch ┃ Fetch ✓ ┃ Fetch ✗ ┃  Karakter  ┃ Link req. ┃ Yeni URL ┃ LLM süresi ┃   Süre   ┃
┃   1   ┃    15   ┃    0    ┃   312,450  ┃     3     ┃    2     ┃    14.2s   ┃  22.1s   ┃
┃   2   ┃    13   ┃    2    ┃   278,100  ┃     1     ┃    0     ┃    11.8s   ┃  19.3s   ┃
```

### Çalışma Özeti

```
┃ Metrik                                  ┃   Değer   ┃
┃ Toplam süre                             ┃  0:04:12  ┃
┃ Tamamlanan batch                        ┃     4     ┃
┃ Başarılı fetch                          ┃    52     ┃
┃ Başarısız fetch                         ┃     3     ┃
┃ İşlenen toplam karakter                 ┃ 1,243,800 ┃
┃ Model tarafından keşfedilen URL         ┃     8     ┃
┃ Model tarafından talep edilen bağlantı  ┃     5     ┃
┃ LLM çağrı sayısı                        ┃     5     ┃
┃ Ort. LLM yanıt süresi                  ┃   13.4s   ┃
┃ Ort. fetch süresi                       ┃   0.82s   ┃
```

---

## Bağımlılıklar

| Paket | Amaç | Kurulum |
|-------|------|---------|
| `requests` | HTTP fetch ve LM Studio SSE streaming | `pip install requests` |
| `beautifulsoup4` | HTML ayrıştırma | `pip install beautifulsoup4` |
| `python-docx` | DOCX üretimi | `pip install python-docx` |
| `rich` | Terminal UI (renkler, tablo, Live streaming paneli) | `pip install rich` |
| `reportlab` | PDF üretimi | `pip install reportlab` |
| `ollama` | Ollama backend | `pip install ollama` |
| `openai` | OpenAI / LM Studio backend | `pip install openai` |
| `anthropic` | Anthropic backend (streaming + thinking) | `pip install anthropic` |
| `groq` | Groq backend | `pip install groq` |
| `numpy` | RAG — TF-IDF geri dönüşü | `pip install numpy` |
| `sentence-transformers` | RAG — semantik embedding | `pip install sentence-transformers` |

Tek komutla tam kurulum:

```bash
pip install requests beautifulsoup4 python-docx rich reportlab ollama openai anthropic groq
```

---

## Sık Sorulan Sorular

**Model bazen alakasız URL'ler öneriyor, nasıl engellerim?**
`LINK_REQUEST` başına 10 ile sınırlıdır. İsterseniz prompt'taki bu sayıyı düşürebilirsiniz.

**Bir URL fetch edilemiyor, tüm batch durur mu?**
Hayır. Başarısız fetch'ler atlanır, log'a yazılır ve batch geri kalan URL'lerle devam eder.

**`--save-intermediate` ne işe yarar?**
Her batch'in ham LLM çıktısını ayrı bir `.txt` dosyasına kaydeder. Uzun çalışmalarda agent ortasında kesilirse kısmi analiz kaybolmaz.

**Thinking akışı çıktı dosyasına dahil ediliyor mu?**
Hayır. Thinking içeriği yalnızca terminalde gösterilir; rapor dosyasına yazılmaz.

**Model JSON döndürmüyor, final rapor oluşturulmuyor.**
Geçersiz JSON durumunda ham metin otomatik olarak kullanılır. Model `is_final_report: false` döndürüyorsa terminalde ek bilgi girmeniz istenir; en fazla 3 kez yeniden denenir.

**PDF'de Türkçe karakter sorunu yaşıyorum.**
ReportLab varsayılan fontları tam Latin-Extended desteği sunar. Sorun yaşarsanız sisteminizden bir TTFont ekleyebilirsiniz:

```python
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
pdfmetrics.registerFont(TTFont("DejaVu", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
```

---

## Katkıda Bulunma

1. Repo'yu fork'layın ve yeni bir branch açın: `git checkout -b ozellik/aciklama`
2. Değişikliklerinizi yapın ve commit'leyin.
3. Pull request açın; açıklamaya ne değiştiğini ve neden yazın.

Büyük değişiklikler için önce bir issue açıp tartışmaya başlamanız önerilir.

---

## Lisans

GPLv3

---

*Analizkasar v0.1 — Yasir Eymen KAYABAŞI*