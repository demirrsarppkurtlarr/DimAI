# DimAI

Kendi eğitilen, dış AI API’si kullanmayan küçük bir kod dil modeli.

- NumPy GRU (karakter seviyesinde)
- Yerel Python corpus + Hugging Face’ten veri eklenebilir
- Geçerli Python üretince self-train döngüsü
- Flask web arayüzü

## Kurulum

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python3 data/build_corpus.py
python3 server.py
```

Aç: http://127.0.0.1:5055

## Not

Bu bir prototip. ChatGPT kalitesinde kod üretmez; öğrenme döngüsünü ve kendi modelini göstermek içindir.
