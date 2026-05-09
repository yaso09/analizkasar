# 🔬 Analizkasar

> **Iteratif web araştırması ve LLM sentezi için otonom komut satırı aracı.**
> URL listesini alır, sayfaları tarar, model aracılığıyla analiz eder, bağlantıları takip eder ve akademik rapor üretir.

**Yazar:** Yasir Eymen KAYABAŞI · **Versiyon:** 0.2

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
- Anthropic düşünen modellerinde (`claude-3-7-sonnet` ve üzeri) extended thinking akışını ayrı bir panelde gösterir
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
git clone https://github.com/kullanici/analizkasar.git
cd analizkasar
```

veya sadece `main.py` dosyasını indirin.

### Adım 2 — Bağımlılıkları Kurun

```bash
pip install requests beautifulsoup4 python-docx rich reportlab
```

Kullanmak istediğiniz backend'e göre ek paket:

| Backend    | Ek paket                    |
|------------|-----------------------------|
| Ollama     | `pip install ollama`        |
| OpenAI     | `pip install openai`        |
| Anthropic  | `pip install anthropic`     |
| Groq       | `pip install groq`          |
| LM Studio  | *(ek paket gerekmez)*       |

### Adım 3 — API Anahtarlarını Ayarlayın (cloud backend'ler için)

```bash
export OPENAI_API_KEY="sk-..."
export ANTHROPIC_API_KEY="sk-ant-..."
export GROQ_API_KEY="gsk_..."
```

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

`--openai-api-key` yerine `OPENAI_API_KEY` ortam değişkeni de kullanılabilir.
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

`--anthropic-api-key` yerine `ANTHROPIC_API_KEY` ortam değişkeni de kullanılabilir.

`claude-3-7-sonnet` ve üzeri modellerde **extended thinking** otomatik olarak etkinleştirilir; düşünce akışı terminalde ayrı bir panelde gösterilir. Eski modeller düz streaming'e otomatik olarak düşer.

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

`--groq-api-key` yerine `GROQ_API_KEY` ortam değişkeni de kullanılabilir.

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

v0.2 ile birlikte tüm backend'ler tam streaming moduna geçmiştir. Her LLM çağrısında token'lar terminale anında basılır; tüm yanıt belleğe alınıp toplu gösterilmez.

### Genel Akış Görünümü

```
── akış başlıyor ──────────────────────────────────────────
Bu batch'teki kaynaklar transformer mimarisinin temel bileşenlerini...
...analiz etmektedir. Multi-head attention mekanizması açısından...
── akış bitti ─────────────────────────────────────────────
```

### Anthropic Extended Thinking

`claude-3-7-sonnet` ve üzeri modellerde model yanıt üretmeden önce bir "düşünce" adımı çalıştırır. Bu adım terminalde soluk renkli bir panel içinde canlı olarak izlenebilir:

```
╭─────────────────── 🧠 Düşünce akışı ──────────────────────╮
│ Kaynaklarda geçen attention mekanizması açıklamalarını    │
│ karşılaştırmam gerekiyor. İlk kaynak scaled dot-product   │
│ formülünü detaylı veriyor, ikinci kaynak ise...           │
╰───────────────────────────────────────────────────────────╯
  🧠 Düşünce: 3,241 karakter
```

Düşünce paneli kapandıktan sonra asıl yanıt metninin akışı başlar. Düşünce içeriği nihai rapora veya çıktı dosyasına dahil edilmez; yalnızca terminalde gösterilir.

Eski modeller (`claude-opus-4-5` gibi) extended thinking desteklemez; bu durumda hata yakalanır ve düz streaming ile devam edilir.

---

## Çıktı Formatları

| Format | Uzantı   | Açıklama |
|--------|----------|----------|
| `pdf`  | `.pdf`   | **Varsayılan.** Markdown → ReportLab ile biçimlendirilmiş PDF. Başlıklar, paragraflar, listeler, kod blokları, alıntılar render edilir. |
| `docx` | `.docx`  | Microsoft Word belgesi. Paragraf bazlı, düz yapı. |
| `md`   | `.md`    | Ham Markdown. LLM'nin ürettiği metin, işlenmeden kaydedilir. |
| `txt`  | `.txt`   | Düz metin. |
| `json` | `.json`  | Tüm batch verileri + final rapor. Programatik işleme için idealdir. |

### Format Seçim Önceliği

1. `--format` argümanı açıkça verilmişse → kullanılır
2. `--output` dosyasının uzantısı tanınan bir format ise → uzantı kullanılır
3. Hiçbiri yoksa → `pdf` varsayılan

```bash
# Uzantıdan otomatik algılama
python main.py --urls urls.txt -o rapor.docx   # → docx
python main.py --urls urls.txt -o rapor.json   # → json

# Açık format belirtme
python main.py --urls urls.txt -o sonuc.txt --format md   # → md (format öncelikli)
```

### PDF Yapısı

PDF çıktısı LLM'nin ürettiği Markdown'ı ayrıştırarak şunları render eder:

| Markdown | PDF karşılığı |
|----------|--------------|
| `# Başlık` | H1 — büyük, koyu, lacivert |
| `## Başlık` | H2 — orta, koyu |
| `### Başlık` | H3 — küçük, koyu, mavi |
| `**metin**` | Kalın |
| `*metin*` | İtalik |
| `` `kod` `` | Courier yazı tipi |
| ` ``` blok ``` ` | Gri arka planlı kod kutusu |
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
|---------|----------|-----------|----------|
| `--backend` | `-b` | `ollama` | LLM sağlayıcısı: `ollama` `openai` `anthropic` `groq` `lmstudio` |
| `--model` | `-m` | *(backend'e göre)* | Model adı. Belirtilmezse her backend için otomatik varsayılan seçilir. |
| `--list-models` | — | — | Tüm backend'ler için varsayılan modelleri tabloda gösterir ve çıkar. |

---

### 🔑 Backend Kimlik Bilgileri

| Argüman | Ortam değişkeni | Varsayılan |
|---------|----------------|-----------|
| `--ollama-host` | — | `http://localhost:11434` |
| `--openai-api-key` | `OPENAI_API_KEY` | — |
| `--openai-base-url` | — | *(OpenAI resmi endpoint)* |
| `--anthropic-api-key` | `ANTHROPIC_API_KEY` | — |
| `--groq-api-key` | `GROQ_API_KEY` | — |
| `--lmstudio-url` | — | `http://localhost:1234` |

---

### ⚙️ Agent Ayarları

| Argüman | Kısaltma | Varsayılan | Açıklama |
|---------|----------|-----------|----------|
| `--batch-size` | `-s` | `15` | Tek LLM çağrısına gönderilecek maksimum URL sayısı. Tüm URL'ler bitene kadar döngü tekrarlanır. |
| `--max-extra-links` | — | `50` | Model `LINK_REQUEST:` ile talep edebileceği maksimum bağlantı sayısı. `0` = sınırsız. |
| `--delay` | — | `0.5` | Batch'ler arasında bekleme süresi (saniye). Hedef sunucuyu aşırı yüklemekten kaçınır. |
| `--scrape-timeout` | — | `15` | HTTP istek zaman aşımı (saniye). |
| `--max-chars` | — | `20000` | Kaynak başına maksimum karakter. Uzun sayfalar bu değerde kesilir. |

---

### 💾 Çıktı

| Argüman | Kısaltma | Varsayılan | Açıklama |
|---------|----------|-----------|----------|
| `--output` | `-o` | `rapor.pdf` | Çıktı dosyası yolu. Uzantı format belirleme için kullanılır. |
| `--format` | `-f` | *(uzantıdan)* | Çıktı formatı: `pdf` `docx` `md` `txt` `json` |
| `--save-intermediate` | — | kapalı | Her batch sonunda analizi `<çıktı>.batchN.txt` dosyasına kaydeder. |

---

### 🌍 Dil

| Argüman | Kısaltma | Varsayılan | Açıklama |
|---------|----------|-----------|----------|
| `--language` | `-l` | `Turkish` | Rapor ve analiz dili. Hem batch analizlerine hem de final rapora uygulanır. |

Herhangi bir doğal dil adı girilebilir. Örnekler:

```bash
python main.py --urls urls.txt --language English
python main.py --urls urls.txt --language German
python main.py --urls urls.txt --language Arabic
python main.py --urls urls.txt -l French
```

---

### 🔊 Log Seviyesi

| Argüman | Kısaltma | Açıklama |
|---------|----------|----------|
| `--quiet` | `-q` | Yalnızca hata mesajlarını gösterir. |
| `--verbose` | `-v` | DEBUG dahil tüm mesajları gösterir. |

`--quiet` ve `--verbose` birlikte kullanılamaz.

---

## Örnek Kullanımlar

### Temel kullanım

```bash
# Ollama + PDF (varsayılanlar)
python main.py --urls urls.txt
```

### Backend ve model seçimi

```bash
# Anthropic Claude
python main.py \
  --backend anthropic \
  --model claude-opus-4-5 \
  --urls urls.txt \
  -o rapor.pdf

# OpenAI GPT-4o + Markdown
python main.py \
  --backend openai \
  --model gpt-4o \
  --urls urls.txt \
  --format md \
  -o rapor.md

# Groq — hızlı ve ücretsiz tier
python main.py \
  --backend groq \
  --model llama-3.3-70b-versatile \
  --urls urls.txt
```

### Anthropic thinking modeli ile kullanım

```bash
# Extended thinking terminalde canlı gösterilir
python main.py \
  --backend anthropic \
  --model claude-3-7-sonnet-20250219 \
  --urls urls.txt \
  -o rapor.pdf
```

### Farklı dilde rapor

```bash
# İngilizce rapor
python main.py --urls urls.txt --language English -o report.pdf

# Almanca rapor
python main.py --urls urls.txt -l German -o bericht.pdf
```

### Tek URL ile çalışma

```bash
python main.py \
  --url https://arxiv.org/abs/1706.03762 \
  --url https://arxiv.org/abs/2005.14165 \
  --backend anthropic \
  -o transformer_raporu.pdf
```

### Büyük URL listeleri — batch boyutu optimizasyonu

```bash
# Küçük batch → daha sık LLM çağrısı, daha odaklı analiz
python main.py --urls urls.txt --batch-size 5

# Büyük batch → daha az LLM çağrısı, daha az maliyet
python main.py --urls urls.txt --batch-size 25
```

### Ara çıktıları kaydet

```bash
# Her batch sonunda rapor.pdf.batchN.txt dosyası oluşur
python main.py \
  --urls urls.txt \
  --save-intermediate \
  -o rapor.pdf
```

### JSON çıktısı — programatik işleme

```bash
python main.py \
  --urls urls.txt \
  --format json \
  -o sonuclar.json

# Python ile işleme
python3 -c "
import json
data = json.load(open('sonuclar.json'))
print(f\"İşlenen URL: {data['meta']['total_urls_processed']}\")
print(f\"Batch sayısı: {data['meta']['batches']}\")
for b in data['batches']:
    print(f\"Batch {b['batch']}: {b['fetched']} başarılı, {b['chars']:,} karakter\")
"
```

### Sessiz mod — otomasyon / cron

```bash
python main.py --urls urls.txt --quiet -o rapor.pdf
echo "Çıkış kodu: $?"
```

### Verbose mod — hata ayıklama

```bash
python main.py --urls urls.txt --verbose -o rapor.pdf 2>&1 | tee debug.log
```

### Uzak Ollama sunucusu

```bash
python main.py \
  --backend ollama \
  --ollama-host http://192.168.1.100:11434 \
  --model llama3:70b \
  --urls urls.txt
```

### Azure OpenAI

```bash
python main.py \
  --backend openai \
  --openai-base-url https://MY_RESOURCE.openai.azure.com/ \
  --openai-api-key MY_KEY \
  --model gpt-4o \
  --urls urls.txt
```

---

## Agent Döngüsü Detayı

### LINK_REQUEST Mekanizması

Model, analiz sırasında bir sayfanın bağlantılarından kritik olanları tespit ederse çıktısına şu satırları ekler:

```
LINK_REQUEST: https://github.com/example/repo
LINK_REQUEST: https://arxiv.org/abs/2103.00020
```

Bu URL'ler:
- Henüz fetch edilmemişse kuyruğun **başına** eklenir (öncelikli işlenir)
- Zaten fetch edilmişse veya kuyrukta varsa atlanır
- Her batch için model en fazla **10 adet** `LINK_REQUEST` kullanabilir

### NEW_SOURCE Mekanizması

Model, bilgi eksikliğini gidermek için yeni kaynaklar önerebilir:

```
NEW_SOURCE: https://papers.with-code.com/paper/attention-is-all-you-need
NEW_SOURCE: https://lilianweng.github.io/posts/2023-01-27-the-transformer-family-v2/
```

Bu URL'ler kuyruğun **sonuna** eklenir (normal öncelik).

### URL Tekrar Fetch Önlemi

Her URL yalnızca bir kez işlenir. `processed` kümesi aracılığıyla hem `LINK_REQUEST` hem `NEW_SOURCE` hem de orijinal listeden gelen URL'lerin tekrarlanması engellenir.

### Final Rapor — JSON Doğrulama ve Retry

v0.2'den itibaren final rapor LLM'den JSON olarak istenir. Model şu iki şemadan birini döndürmek zorundadır:

```json
// Rapor başarıyla oluşturulduysa
{ "is_final_report": true, "report": "# Araştırma Raporu\n..." }

// Model raporu tamamlayamadıysa
{ "is_final_report": false, "message": "...", "needed_input": "..." }
```

`is_final_report` değeri `false` gelirse terminal ekranında bir uyarı paneli gösterilir ve kullanıcıdan ek bilgi istenir. Girilen bilgi prompt'a eklenerek LLM yeniden çağrılır. İşlem en fazla **3 kez** tekrarlanır; başarısız olursa program hata koduyla çıkar.

Model geçersiz JSON döndürürse (bazı eski modellerde görülebilir) ham metin doğrudan rapor olarak kullanılır; önceki sürümlerle uyumluluk korunur.

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
| `ollama` | Ollama backend (streaming) | `pip install ollama` |
| `openai` | OpenAI / LM Studio backend (streaming) | `pip install openai` |
| `anthropic` | Anthropic backend (streaming + thinking) | `pip install anthropic` |
| `groq` | Groq backend (streaming) | `pip install groq` |

Tek komutla tam kurulum:

```bash
pip install requests beautifulsoup4 python-docx rich reportlab ollama openai anthropic groq
```

---

## Sık Sorulan Sorular

### Model bazen alakasız URL'ler öneriyor, nasıl engellerim?

`LINK_REQUEST` başına `10` ile sınırlıdır (prompt'ta belirtilmiş). İsterseniz prompt'taki bu sayıyı düşürebilirsiniz. `NEW_SOURCE` için ek filtreleme eklemek isterseniz `run_agent()` içindeki ilgili bloku güncelleyin.

### Çok sayıda URL için batch boyutunu nasıl optimize ederim?

| URL sayısı | Önerilen `--batch-size` |
|-----------|------------------------|
| < 20      | 5–10                   |
| 20–100    | 10–20                  |
| 100+      | 20–30                  |

Büyük batch → daha az LLM çağrısı → daha düşük maliyet, ama her prompt daha büyük.

### Bir URL fetch edilemiyor, tüm batch durur mu?

Hayır. Başarısız fetch'ler atlanır, log'a yazılır ve batch geri kalan URL'lerle devam eder.

### `--save-intermediate` ne işe yarar?

Her batch'in ham LLM çıktısını ayrı bir `.txt` dosyasına kaydeder. Uzun çalışmalarda agent ortasında kesilirse kısmi analiz kaybolmaz.

### Thinking akışı çıktı dosyasına dahil ediliyor mu?

Hayır. Thinking içeriği yalnızca terminalde gösterilir; nihai rapor, DOCX, PDF veya JSON dosyasına yazılmaz.

### Model JSON döndürmüyor, final rapor oluşturulmuyor.

v0.2 final prompt'u JSON yanıt gerektirir. Geçersiz JSON durumunda ham metin otomatik olarak kullanılır (geçmiş uyumluluğu). Model `is_final_report: false` döndürüyorsa terminalde ek bilgi girmeniz istenir; bu bilgi prompt'a eklenerek en fazla 3 kez yeniden denenir.

### PDF Türkçe karakter sorunu yaşıyorum.

ReportLab varsayılan fontları (Helvetica/Times/Courier) tam Latin-Extended desteği sunar. Sorun yaşarsanız TTFont ile sisteminizden bir font ekleyebilirsiniz:

```python
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
pdfmetrics.registerFont(TTFont("DejaVu", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
```

---

## Lisans

Bu proje **GNU General Public License v3.0 (GPLv3)** ile lisanslanmıştır.

Bu lisans kapsamında:

- ✅ Kaynak kodu serbestçe kullanabilir, inceleyebilir ve değiştirebilirsiniz
- ✅ Dağıtabilirsiniz — ancak aynı GPLv3 lisansı ile
- ✅ Ticari kullanıma izin verilir
- ❌ Kapalı kaynak türev çalışma dağıtamazsınız
- ❌ Lisans ve telif hakkı bildirimlerini kaldıramazsınız

Lisansın tam metni için: <https://www.gnu.org/licenses/gpl-3.0.html>

---

*Analizkasar v0.2 — Yasir Eymen KAYABAŞI*