"""DimAI Brain — rule + knowledge based chat engine focused on code.

No external AI APIs. Understands Turkish and English requests, returns
explanations + code. Falls back to the neural char-RNN (experimental).
"""
from __future__ import annotations

import difflib
import random
import re
import unicodedata
from typing import Optional


def _norm(text: str) -> str:
    text = text.lower()
    table = str.maketrans("çğıöşü", "cgiosu")
    text = text.translate(table)
    text = unicodedata.normalize("NFKD", text)
    text = re.sub(r"[^a-z0-9+\-*/=<>.,!?'\"\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


# ---------------------------------------------------------------------------
# Knowledge base: each entry = keywords, answer, code, language
# ---------------------------------------------------------------------------

KB: list[dict] = [
    # --- Python temelleri ---
    {"k": ["print", "yazdir", "ekrana yaz", "output", "konsola yaz"],
     "a": "Python'da ekrana yazdırmak için `print()` kullanılır:",
     "c": '''print("Merhaba Dünya!")

isim = "Demir"
yas = 16
print("İsim:", isim, "- Yaş:", yas)
print(f"{isim} {yas} yaşında")  # f-string en modern yol''', "l": "python"},

    {"k": ["degisken", "variable", "atama", "tanimla"],
     "a": "Python'da değişken tanımlamak çok basit — tip belirtmene gerek yok:",
     "c": '''isim = "Ali"        # str
yas = 25            # int
boy = 1.78          # float
ogrenci = True      # bool
notlar = [90, 85]   # list

print(type(isim), type(yas))''', "l": "python"},

    {"k": ["input", "kullanicidan", "veri al", "klavyeden"],
     "a": "Kullanıcıdan veri almak için `input()` kullanılır. Sayı için dönüştürmeyi unutma:",
     "c": '''isim = input("Adın ne? ")
yas = int(input("Kaç yaşındasın? "))
print(f"Merhaba {isim}, {yas} yaşındasın!")''', "l": "python"},

    {"k": ["if", "else", "elif", "kosul", "sart", "karsilastirma"],
     "a": "Koşullu ifadeler `if / elif / else` ile yazılır:",
     "c": '''puan = 75

if puan >= 90:
    print("AA")
elif puan >= 70:
    print("BB")
elif puan >= 50:
    print("CC")
else:
    print("Kaldın :(")''', "l": "python"},

    {"k": ["for", "dongu", "loop", "tekrar", "iterate"],
     "a": "`for` döngüsü ile bir aralıkta veya liste üzerinde dönebilirsin:",
     "c": '''for i in range(5):        # 0 1 2 3 4
    print(i)

meyveler = ["elma", "armut", "muz"]
for meyve in meyveler:
    print(meyve)

for i, m in enumerate(meyveler):  # index ile
    print(i, m)''', "l": "python"},

    {"k": ["while", "sonsuz dongu", "kosullu dongu"],
     "a": "`while` döngüsü koşul doğru olduğu sürece çalışır:",
     "c": '''sayi = 1
while sayi <= 5:
    print(sayi)
    sayi += 1

# break ile çıkış
while True:
    cevap = input("çıkmak için q: ")
    if cevap == "q":
        break''', "l": "python"},

    {"k": ["liste", "list", "dizi", "array", "append"],
     "a": "Listeler Python'un en çok kullanılan veri yapısıdır:",
     "c": '''sayilar = [3, 1, 4, 1, 5]

sayilar.append(9)      # sona ekle
sayilar.insert(0, 2)   # başa ekle
sayilar.remove(1)      # ilk 1'i sil
son = sayilar.pop()    # son elemanı al

print(len(sayilar))    # uzunluk
print(sayilar[0])      # ilk eleman
print(sayilar[-1])     # son eleman
print(sorted(sayilar)) # sıralı kopya''', "l": "python"},

    {"k": ["list comprehension", "tek satirda liste", "comprehension"],
     "a": "List comprehension ile tek satırda liste üretebilirsin:",
     "c": '''kareler = [x**2 for x in range(10)]
ciftler = [x for x in range(20) if x % 2 == 0]
kelimeler = [s.upper() for s in ["ali", "veli"]]

print(kareler)
print(ciftler)
print(kelimeler)''', "l": "python"},

    {"k": ["sozluk", "dict", "dictionary", "key value", "anahtar"],
     "a": "Sözlük (dict) anahtar-değer çiftleri tutar:",
     "c": '''kisi = {"isim": "Ayşe", "yas": 22, "sehir": "İzmir"}

print(kisi["isim"])           # Ayşe
print(kisi.get("meslek", "yok"))  # güvenli erişim

kisi["meslek"] = "mühendis"   # ekle/güncelle

for anahtar, deger in kisi.items():
    print(anahtar, "->", deger)''', "l": "python"},

    {"k": ["tuple", "demet"],
     "a": "Tuple değiştirilemez (immutable) bir dizidir:",
     "c": '''nokta = (3, 5)
x, y = nokta          # unpacking
print(x, y)

# tek elemanlı tuple'da virgül şart
tek = (42,)''', "l": "python"},

    {"k": ["set", "kume", "benzersiz", "unique", "tekrarsiz"],
     "a": "Set (küme) tekrarsız eleman tutar:",
     "c": '''a = {1, 2, 3, 3, 2}
print(a)              # {1, 2, 3}

b = {3, 4, 5}
print(a | b)          # birleşim
print(a & b)          # kesişim
print(a - b)          # fark

# listeden tekrarları silmek
liste = [1, 2, 2, 3, 3, 3]
print(list(set(liste)))''', "l": "python"},

    {"k": ["string", "metin", "karakter dizisi", "upper", "lower", "split", "strip"],
     "a": "String metotlarının en kullanışlıları:",
     "c": '''s = "  Merhaba Dünya  "

print(s.strip())        # boşlukları kırp
print(s.lower())        # küçük harf
print(s.upper())        # büyük harf
print(s.replace("Dünya", "Python"))
print("a,b,c".split(","))   # ['a','b','c']
print("-".join(["x", "y", "z"]))  # x-y-z
print("Merhaba".startswith("Mer"))  # True
print(len(s.strip()))''', "l": "python"},

    {"k": ["f-string", "fstring", "format", "string format", "bicimlendir"],
     "a": "f-string ile değişkenleri metne gömebilirsin:",
     "c": '''isim = "Zeynep"
puan = 92.5678

print(f"{isim} aldı: {puan}")
print(f"Yuvarlak: {puan:.2f}")     # 92.57
print(f"Hizala: {isim:>10}")       # sağa yasla
print(f"Hesap: {3*7=}")            # 3*7=21''', "l": "python"},

    {"k": ["fonksiyon", "function", "def", "tanimla fonksiyon", "metod yaz"],
     "a": "Fonksiyon `def` ile tanımlanır:",
     "c": '''def topla(a, b):
    return a + b

def selamla(isim, mesaj="Merhaba"):   # varsayılan değer
    return f"{mesaj}, {isim}!"

print(topla(3, 5))          # 8
print(selamla("Can"))       # Merhaba, Can!
print(selamla("Can", "Selam"))''', "l": "python"},

    {"k": ["lambda", "anonim fonksiyon", "tek satir fonksiyon"],
     "a": "Lambda tek satırlık isimsiz fonksiyondur:",
     "c": '''kare = lambda x: x**2
print(kare(6))    # 36

sayilar = [(1, 'b'), (3, 'a'), (2, 'c')]
sayilar.sort(key=lambda t: t[1])   # harfe göre sırala
print(sayilar)''', "l": "python"},

    {"k": ["map", "filter", "reduce"],
     "a": "`map` dönüştürür, `filter` süzer:",
     "c": '''sayilar = [1, 2, 3, 4, 5, 6]

kareler = list(map(lambda x: x**2, sayilar))
ciftler = list(filter(lambda x: x % 2 == 0, sayilar))

print(kareler)   # [1, 4, 9, 16, 25, 36]
print(ciftler)   # [2, 4, 6]

from functools import reduce
toplam = reduce(lambda a, b: a + b, sayilar)
print(toplam)    # 21''', "l": "python"},

    {"k": ["sirala", "sort", "sorted", "siralama", "buyukten kucuge"],
     "a": "Sıralama için `sorted()` (kopya) veya `.sort()` (yerinde):",
     "c": '''sayilar = [5, 2, 9, 1]

print(sorted(sayilar))              # [1, 2, 5, 9]
print(sorted(sayilar, reverse=True))# [9, 5, 2, 1]

kisiler = [{"ad": "Ali", "yas": 30}, {"ad": "Veli", "yas": 25}]
kisiler.sort(key=lambda k: k["yas"])
print(kisiler)''', "l": "python"},

    {"k": ["dosya oku", "read file", "dosya okuma", "open", "txt oku",
           "dosya nasil okunur", "okunur", "dosyayi oku", "dosyadan oku"],
     "a": "Dosya okumak için `with open` kullan — otomatik kapanır:",
     "c": '''with open("veri.txt", "r", encoding="utf-8") as f:
    icerik = f.read()          # tümü
    print(icerik)

with open("veri.txt", encoding="utf-8") as f:
    for satir in f:            # satır satır
        print(satir.strip())''', "l": "python"},

    {"k": ["dosya yaz", "write file", "dosyaya kaydet", "txt yaz", "dosya olustur",
           "dosyaya yaz", "dosyaya nasil yazarim", "yazarim", "dosyaya yazma",
           "yazma", "yazilir", "nasil yazilir", "kaydet"],
     "a": "Dosyaya yazmak için `w` (üzerine) veya `a` (sona ekle) modu:",
     "c": '''with open("cikti.txt", "w", encoding="utf-8") as f:
    f.write("İlk satır\\n")
    f.write("İkinci satır\\n")

with open("cikti.txt", "a", encoding="utf-8") as f:
    f.write("Sona eklendi\\n")''', "l": "python"},

    {"k": ["json", "json oku", "json yaz", "json parse"],
     "a": "JSON okumak/yazmak için `json` modülü:",
     "c": '''import json

veri = {"isim": "Deniz", "hobiler": ["kod", "müzik"]}

# yaz
with open("veri.json", "w", encoding="utf-8") as f:
    json.dump(veri, f, ensure_ascii=False, indent=2)

# oku
with open("veri.json", encoding="utf-8") as f:
    okunan = json.load(f)
print(okunan["hobiler"])

# string <-> dict
s = json.dumps(veri)
d = json.loads(s)''', "l": "python"},

    {"k": ["csv", "csv oku", "excel", "tablo oku"],
     "a": "CSV dosyaları için `csv` modülü:",
     "c": '''import csv

# yaz
with open("kisiler.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f)
    w.writerow(["isim", "yas"])
    w.writerow(["Ali", 30])

# oku
with open("kisiler.csv", encoding="utf-8") as f:
    for satir in csv.reader(f):
        print(satir)''', "l": "python"},

    {"k": ["hata", "try", "except", "exception", "hata yakalama", "error"],
     "a": "Hataları `try/except` ile yakalarsın:",
     "c": '''try:
    sayi = int(input("Sayı gir: "))
    sonuc = 10 / sayi
    print(sonuc)
except ValueError:
    print("Bu bir sayı değil!")
except ZeroDivisionError:
    print("Sıfıra bölünmez!")
except Exception as e:
    print("Beklenmeyen hata:", e)
finally:
    print("Her durumda çalışır")''', "l": "python"},

    {"k": ["class", "sinif", "oop", "nesne", "object"],
     "a": "Sınıf (class) ile kendi veri tiplerini oluşturursun:",
     "c": '''class Araba:
    def __init__(self, marka, hiz=0):
        self.marka = marka
        self.hiz = hiz

    def hizlan(self, artis):
        self.hiz += artis
        return self.hiz

    def __str__(self):
        return f"{self.marka} ({self.hiz} km/s)"

a = Araba("Togg")
a.hizlan(50)
print(a)   # Togg (50 km/s)''', "l": "python"},

    {"k": ["kalitim", "inheritance", "miras", "super"],
     "a": "Kalıtım ile bir sınıf başka sınıftan özellik alır:",
     "c": '''class Hayvan:
    def __init__(self, isim):
        self.isim = isim
    def ses(self):
        return "..."

class Kedi(Hayvan):
    def ses(self):
        return "Miyav!"

class Kopek(Hayvan):
    def ses(self):
        return "Hav!"

for h in [Kedi("Tekir"), Kopek("Karabaş")]:
    print(h.isim, h.ses())''', "l": "python"},

    {"k": ["decorator", "dekorator", "sarici"],
     "a": "Decorator bir fonksiyonu sarıp davranış ekler:",
     "c": '''import time

def sure_olc(fn):
    def sarici(*args, **kwargs):
        t = time.time()
        sonuc = fn(*args, **kwargs)
        print(f"{fn.__name__}: {time.time()-t:.4f} sn")
        return sonuc
    return sarici

@sure_olc
def yavas_islem():
    time.sleep(0.3)
    return "bitti"

print(yavas_islem())''', "l": "python"},

    {"k": ["generator", "yield", "uretec"],
     "a": "Generator, değerleri tek tek üretir — bellek dostu:",
     "c": '''def sayac(n):
    i = 0
    while i < n:
        yield i
        i += 1

for x in sayac(5):
    print(x)

# generator expression
kareler = (x**2 for x in range(1000000))  # bellekte yer kaplamaz
print(next(kareler), next(kareler))''', "l": "python"},

    {"k": ["import", "modul", "kutuphane", "pip", "yukle"],
     "a": "Modül içe aktarma ve pip ile kurulum:",
     "c": '''import math
from datetime import datetime
import numpy as np           # takma ad

print(math.sqrt(16))
print(datetime.now())

# Terminalde paket kurmak:
# pip install requests
# pip install -r requirements.txt''', "l": "python"},

    {"k": ["random", "rastgele", "rasgele", "sans", "kura"],
     "a": "Rastgelelik için `random` modülü:",
     "c": '''import random

print(random.randint(1, 6))        # zar
print(random.random())             # 0-1 arası float
print(random.choice(["a", "b"]))   # listeden seç
print(random.sample(range(50), 6)) # loto: 6 benzersiz

liste = [1, 2, 3, 4, 5]
random.shuffle(liste)              # karıştır
print(liste)''', "l": "python"},

    {"k": ["tarih", "saat", "datetime", "date", "zaman damgasi", "timestamp"],
     "a": "Tarih/saat işlemleri için `datetime`:",
     "c": '''from datetime import datetime, timedelta

simdi = datetime.now()
print(simdi.strftime("%d.%m.%Y %H:%M"))

yarin = simdi + timedelta(days=1)
print(yarin.date())

dogum = datetime(2008, 5, 12)
yas = (simdi - dogum).days // 365
print(f"Yaş: {yas}")''', "l": "python"},

    {"k": ["regex", "regular expression", "duzenli ifade", "re modulu", "pattern"],
     "a": "Regex ile metin deseni arama:",
     "c": '''import re

metin = "Mail: ali@test.com, veli@ornek.org"

mailler = re.findall(r"[\\w.]+@[\\w.]+", metin)
print(mailler)

telefon = "0532 111 22 33"
if re.match(r"^0\\d{3} \\d{3} \\d{2} \\d{2}$", telefon):
    print("Geçerli numara")

temiz = re.sub(r"\\d", "*", "abc123")  # abc***
print(temiz)''', "l": "python"},

    {"k": ["requests", "http", "api istek", "get istegi", "url", "web istek", "api cek"],
     "a": "HTTP istekleri için `requests` kütüphanesi (pip install requests):",
     "c": '''import requests

r = requests.get("https://api.github.com/users/torvalds")
print(r.status_code)          # 200
veri = r.json()
print(veri["name"])

# POST isteği
cevap = requests.post(
    "https://httpbin.org/post",
    json={"kullanici": "demir"},
    timeout=10,
)
print(cevap.json()["json"])''', "l": "python"},

    {"k": ["flask", "web sitesi", "web uygulamasi", "web server", "sunucu"],
     "a": "Flask ile mini web uygulaması:",
     "c": '''from flask import Flask, jsonify, request

app = Flask(__name__)

@app.route("/")
def anasayfa():
    return "<h1>Merhaba Flask!</h1>"

@app.route("/api/topla")
def topla():
    a = int(request.args.get("a", 0))
    b = int(request.args.get("b", 0))
    return jsonify({"sonuc": a + b})

if __name__ == "__main__":
    app.run(debug=True, port=5000)''', "l": "python"},

    {"k": ["sqlite", "veritabani", "database", "sql", "db"],
     "a": "SQLite — kurulum gerektirmeyen veritabanı:",
     "c": '''import sqlite3

con = sqlite3.connect("okul.db")
cur = con.cursor()

cur.execute("""CREATE TABLE IF NOT EXISTS ogrenci (
    id INTEGER PRIMARY KEY,
    isim TEXT, puan REAL)""")

cur.execute("INSERT INTO ogrenci (isim, puan) VALUES (?, ?)",
            ("Ali", 87.5))
con.commit()

for satir in cur.execute("SELECT * FROM ogrenci ORDER BY puan DESC"):
    print(satir)

con.close()''', "l": "python"},

    {"k": ["thread", "threading", "paralel", "ayni anda"],
     "a": "Threading ile işleri paralel çalıştırma:",
     "c": '''import threading
import time

def gorev(isim, sn):
    time.sleep(sn)
    print(f"{isim} bitti")

t1 = threading.Thread(target=gorev, args=("A", 1))
t2 = threading.Thread(target=gorev, args=("B", 2))

t1.start(); t2.start()
t1.join(); t2.join()
print("Hepsi tamam")''', "l": "python"},

    {"k": ["async", "asyncio", "await", "asenkron"],
     "a": "Asenkron programlama `asyncio` ile:",
     "c": '''import asyncio

async def gorev(isim, sn):
    await asyncio.sleep(sn)
    return f"{isim} bitti"

async def main():
    sonuclar = await asyncio.gather(
        gorev("A", 1),
        gorev("B", 1),
    )
    print(sonuclar)   # ikisi de ~1 sn'de biter

asyncio.run(main())''', "l": "python"},

    {"k": ["os", "dosya sistemi", "klasor", "dizin", "path", "listdir"],
     "a": "Dosya sistemi işlemleri için `os` ve `pathlib`:",
     "c": '''from pathlib import Path
import os

p = Path("belgeler")
p.mkdir(exist_ok=True)          # klasör oluştur

for dosya in Path(".").glob("*.py"):
    print(dosya.name, dosya.stat().st_size, "bayt")

print(os.getcwd())              # bulunduğun dizin
print(Path("a/b.txt").suffix)   # .txt''', "l": "python"},

    {"k": ["args", "kwargs", "coklu parametre"],
     "a": "`*args` ve `**kwargs` ile esnek parametreler:",
     "c": '''def topla(*args):
    return sum(args)

def bilgi(**kwargs):
    for k, v in kwargs.items():
        print(f"{k} = {v}")

print(topla(1, 2, 3, 4))        # 10
bilgi(isim="Ali", yas=30)''', "l": "python"},

    {"k": ["recursion", "ozyineleme", "recursive", "kendini cagiran"],
     "a": "Recursion — fonksiyonun kendini çağırması:",
     "c": '''def faktoriyel(n):
    if n <= 1:
        return 1
    return n * faktoriyel(n - 1)

def toplam(n):
    if n == 0:
        return 0
    return n + toplam(n - 1)

print(faktoriyel(5))   # 120
print(toplam(10))      # 55''', "l": "python"},

    {"k": ["type hint", "tip", "typing", "annotation"],
     "a": "Tip ipuçları kodu okunur ve güvenli yapar:",
     "c": '''def ortalama(sayilar: list[float]) -> float:
    return sum(sayilar) / len(sayilar)

def selamla(isim: str, kez: int = 1) -> str:
    return ("Merhaba " + isim + "! ") * kez

x: int = 5
puanlar: dict[str, float] = {"ali": 90.5}''', "l": "python"},

    # --- Klasik algoritma soruları ---
    {"k": ["fibonacci", "fibonacchi", "fibo"],
     "a": "Fibonacci dizisi — hem döngülü hem recursive:",
     "c": '''def fibonacci(n):
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a

# İlk 10 terim
print([fibonacci(i) for i in range(10)])
# [0, 1, 1, 2, 3, 5, 8, 13, 21, 34]''', "l": "python"},

    {"k": ["faktoriyel", "factorial"],
     "a": "Faktöriyel hesaplama:",
     "c": '''def faktoriyel(n):
    sonuc = 1
    for i in range(2, n + 1):
        sonuc *= i
    return sonuc

print(faktoriyel(5))   # 120

import math
print(math.factorial(5))  # hazır fonksiyon''', "l": "python"},

    {"k": ["asal", "prime", "asal sayi"],
     "a": "Asal sayı kontrolü ve listeleme:",
     "c": '''def asal_mi(n):
    if n < 2:
        return False
    for i in range(2, int(n**0.5) + 1):
        if n % i == 0:
            return False
    return True

print(asal_mi(17))    # True
print([x for x in range(50) if asal_mi(x)])''', "l": "python"},

    {"k": ["palindrom", "palindrome", "tersten ayni"],
     "a": "Palindrom kontrolü (tersten okunuşu aynı):",
     "c": '''def palindrom_mu(s):
    s = s.lower().replace(" ", "")
    return s == s[::-1]

print(palindrom_mu("kayak"))       # True
print(palindrom_mu("ey edip adanada pide ye"))  # True
print(palindrom_mu("python"))      # False''', "l": "python"},

    {"k": ["fizzbuzz", "fizz buzz"],
     "a": "Klasik FizzBuzz:",
     "c": '''for i in range(1, 31):
    if i % 15 == 0:
        print("FizzBuzz")
    elif i % 3 == 0:
        print("Fizz")
    elif i % 5 == 0:
        print("Buzz")
    else:
        print(i)''', "l": "python"},

    {"k": ["bubble sort", "kabarcik", "siralama algoritmasi"],
     "a": "Bubble sort — en basit sıralama algoritması:",
     "c": '''def bubble_sort(liste):
    arr = liste[:]
    n = len(arr)
    for i in range(n):
        for j in range(n - i - 1):
            if arr[j] > arr[j + 1]:
                arr[j], arr[j + 1] = arr[j + 1], arr[j]
    return arr

print(bubble_sort([5, 2, 9, 1, 7]))''', "l": "python"},

    {"k": ["binary search", "ikili arama"],
     "a": "Binary search — sıralı listede hızlı arama (O(log n)):",
     "c": '''def binary_search(arr, hedef):
    dusuk, yuksek = 0, len(arr) - 1
    while dusuk <= yuksek:
        orta = (dusuk + yuksek) // 2
        if arr[orta] == hedef:
            return orta
        if arr[orta] < hedef:
            dusuk = orta + 1
        else:
            yuksek = orta - 1
    return -1

print(binary_search([1, 3, 5, 7, 9, 11], 7))  # 3''', "l": "python"},

    {"k": ["ters cevir", "reverse", "tersine", "tersten yazdir"],
     "a": "String veya listeyi ters çevirme:",
     "c": '''s = "Merhaba"
print(s[::-1])            # abahreM

liste = [1, 2, 3, 4]
print(liste[::-1])        # [4, 3, 2, 1]
liste.reverse()           # yerinde çevir
print(list(reversed(liste)))''', "l": "python"},

    {"k": ["sesli harf", "vowel", "unlu harf", "harf say"],
     "a": "Sesli harf sayma:",
     "c": '''def sesli_say(metin):
    sesliler = "aeıioöuüAEIİOÖUÜ"
    return sum(1 for h in metin if h in sesliler)

print(sesli_say("merhaba dünya"))   # 5''', "l": "python"},

    {"k": ["ebob", "gcd", "ekok", "lcm"],
     "a": "EBOB ve EKOK hesaplama:",
     "c": '''import math

print(math.gcd(24, 36))   # 12 (EBOB)
print(math.lcm(4, 6))     # 12 (EKOK)

# elle:
def ebob(a, b):
    while b:
        a, b = b, a % b
    return a''', "l": "python"},

    {"k": ["en buyuk", "max", "min", "en kucuk", "buyugu bul"],
     "a": "En büyük / en küçük bulma:",
     "c": '''sayilar = [12, 45, 7, 89, 23]

print(max(sayilar))    # 89
print(min(sayilar))    # 7
print(max("elma", "armut", key=len))  # en uzun kelime

# elle:
en_buyuk = sayilar[0]
for s in sayilar:
    if s > en_buyuk:
        en_buyuk = s
print(en_buyuk)''', "l": "python"},

    {"k": ["toplam", "sum", "ortalama", "average", "mean"],
     "a": "Toplam ve ortalama hesaplama:",
     "c": '''notlar = [70, 85, 90, 65]

toplam = sum(notlar)
ortalama = toplam / len(notlar)

print(f"Toplam: {toplam}")
print(f"Ortalama: {ortalama:.1f}")''', "l": "python"},

    {"k": ["tekrar eden", "duplicate", "cift kayit", "ayni eleman"],
     "a": "Tekrar eden elemanları bulma / silme:",
     "c": '''liste = [1, 2, 2, 3, 4, 4, 4]

# tekrarları sil (sıra korunur)
benzersiz = list(dict.fromkeys(liste))
print(benzersiz)   # [1, 2, 3, 4]

# tekrar edenleri bul
from collections import Counter
sayim = Counter(liste)
tekrarlar = [x for x, n in sayim.items() if n > 1]
print(tekrarlar)   # [2, 4]''', "l": "python"},

    {"k": ["sayi tahmin", "tahmin oyunu", "guessing"],
     "a": "Sayı tahmin oyunu:",
     "c": '''import random

hedef = random.randint(1, 100)
hak = 7

print("1-100 arası bir sayı tuttum!")
while hak > 0:
    tahmin = int(input(f"Tahminin ({hak} hak): "))
    if tahmin == hedef:
        print("Bildin! 🎉")
        break
    print("Daha büyük" if tahmin < hedef else "Daha küçük")
    hak -= 1
else:
    print(f"Bitti! Sayı: {hedef}")''', "l": "python"},

    {"k": ["tas kagit makas", "rock paper", "oyun yap"],
     "a": "Taş-Kağıt-Makas oyunu:",
     "c": '''import random

secenekler = ["taş", "kağıt", "makas"]
kazanan = {"taş": "makas", "kağıt": "taş", "makas": "kağıt"}

while True:
    sen = input("taş/kağıt/makas (q=çık): ").lower()
    if sen == "q":
        break
    if sen not in secenekler:
        continue
    pc = random.choice(secenekler)
    print("Bilgisayar:", pc)
    if sen == pc:
        print("Berabere!")
    elif kazanan[sen] == pc:
        print("Kazandın! 🎉")
    else:
        print("Kaybettin!")''', "l": "python"},

    {"k": ["hesap makinesi", "calculator", "dort islem"],
     "a": "Basit hesap makinesi:",
     "c": '''def hesapla(a, islem, b):
    if islem == "+": return a + b
    if islem == "-": return a - b
    if islem == "*": return a * b
    if islem == "/":
        return a / b if b != 0 else "Sıfıra bölünmez!"
    return "Geçersiz işlem"

a = float(input("1. sayı: "))
islem = input("İşlem (+ - * /): ")
b = float(input("2. sayı: "))
print("Sonuç:", hesapla(a, islem, b))''', "l": "python"},

    {"k": ["sifre uret", "password generator", "parola olustur", "rastgele sifre"],
     "a": "Güçlü şifre üretici:",
     "c": '''import secrets
import string

def sifre_uret(uzunluk=16):
    havuz = string.ascii_letters + string.digits + "!@#$%^&*"
    return "".join(secrets.choice(havuz) for _ in range(uzunluk))

print(sifre_uret())
print(sifre_uret(24))''', "l": "python"},

    {"k": ["yapilacaklar", "todo", "gorev listesi", "not uygulamasi"],
     "a": "Mini yapılacaklar (todo) uygulaması:",
     "c": '''gorevler = []

while True:
    print("\\n1: Ekle  2: Listele  3: Sil  4: Çık")
    secim = input("> ")
    if secim == "1":
        gorevler.append(input("Görev: "))
    elif secim == "2":
        for i, g in enumerate(gorevler, 1):
            print(f"{i}. {g}")
    elif secim == "3":
        no = int(input("Silinecek no: ")) - 1
        if 0 <= no < len(gorevler):
            print("Silindi:", gorevler.pop(no))
    elif secim == "4":
        break''', "l": "python"},

    {"k": ["sicaklik", "celsius", "fahrenheit", "derece cevir"],
     "a": "Sıcaklık dönüştürme:",
     "c": '''def c_to_f(c):
    return c * 9 / 5 + 32

def f_to_c(f):
    return (f - 32) * 5 / 9

print(c_to_f(25))   # 77.0
print(f_to_c(98.6)) # 37.0''', "l": "python"},

    {"k": ["artik yil", "leap year", "subat 29"],
     "a": "Artık yıl kontrolü:",
     "c": '''def artik_yil(yil):
    return yil % 4 == 0 and (yil % 100 != 0 or yil % 400 == 0)

for y in [2020, 2023, 2024, 2100, 2000]:
    print(y, "->", artik_yil(y))''', "l": "python"},

    {"k": ["degisken takas", "swap", "yer degistir"],
     "a": "İki değişkenin değerini takas etme:",
     "c": '''a, b = 5, 10
a, b = b, a          # Python'da tek satır!
print(a, b)          # 10 5''', "l": "python"},

    {"k": ["kelime say", "word count", "cumledeki kelime"],
     "a": "Kelime ve karakter sayma:",
     "c": '''metin = "python ile kod yazmak çok keyifli python harika"

kelimeler = metin.split()
print("Kelime sayısı:", len(kelimeler))
print("Karakter sayısı:", len(metin))

from collections import Counter
print(Counter(kelimeler).most_common(2))''', "l": "python"},

    {"k": ["zip", "iki liste", "listeleri birlestir"],
     "a": "`zip` ile listeleri eşleştirme:",
     "c": '''isimler = ["Ali", "Ayşe", "Can"]
puanlar = [85, 92, 78]

for isim, puan in zip(isimler, puanlar):
    print(f"{isim}: {puan}")

sozluk = dict(zip(isimler, puanlar))
print(sozluk)''', "l": "python"},

    {"k": ["slicing", "dilimleme", "listeyi kes", "alt liste"],
     "a": "Slicing (dilimleme) ile parça alma:",
     "c": '''liste = [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]

print(liste[2:5])     # [2, 3, 4]
print(liste[:3])      # [0, 1, 2]
print(liste[7:])      # [7, 8, 9]
print(liste[::2])     # [0, 2, 4, 6, 8]
print(liste[::-1])    # ters

s = "Merhaba"
print(s[0:3])          # Mer''', "l": "python"},

    {"k": ["matris", "matrix", "2d liste", "ic ice liste"],
     "a": "2D liste (matris) işlemleri:",
     "c": '''matris = [
    [1, 2, 3],
    [4, 5, 6],
    [7, 8, 9],
]

print(matris[1][2])    # 6

for satir in matris:
    print(satir)

# transpoze
transpoz = [list(s) for s in zip(*matris)]
print(transpoz)''', "l": "python"},

    {"k": ["sayi mi", "isdigit", "kontrol et sayi", "gecerli sayi"],
     "a": "Girdinin sayı olup olmadığını kontrol etme:",
     "c": '''girdi = input("Bir şey yaz: ")

if girdi.lstrip("-").isdigit():
    print("Tam sayı:", int(girdi))
else:
    try:
        f = float(girdi)
        print("Ondalıklı:", f)
    except ValueError:
        print("Sayı değil")''', "l": "python"},

    {"k": ["kac basamak", "basamak", "rakam topla", "digits"],
     "a": "Basamak sayısı ve rakamların toplamı:",
     "c": '''sayi = 48291

print(len(str(sayi)))                 # 5 basamak
print(sum(int(b) for b in str(sayi))) # 4+8+2+9+1 = 24''', "l": "python"},

    {"k": ["saat bekle", "sleep", "gecikme", "bekleme"],
     "a": "Programı bekletmek için `time.sleep`:",
     "c": '''import time

print("3 saniye sayıyorum...")
for i in range(3, 0, -1):
    print(i)
    time.sleep(1)
print("Bitti!")''', "l": "python"},

    {"k": ["virtual env", "venv", "sanal ortam"],
     "a": "Sanal ortam oluşturma ve kullanma:",
     "c": '''# Terminal komutları:
python3 -m venv .venv

# Aktifleştir (Linux/Mac):
source .venv/bin/activate
# Windows:
.venv\\Scripts\\activate

pip install requests flask
pip freeze > requirements.txt''', "l": "bash"},

    {"k": ["pandas", "dataframe", "veri analizi"],
     "a": "Pandas ile veri analizi temelleri (pip install pandas):",
     "c": '''import pandas as pd

df = pd.DataFrame({
    "isim": ["Ali", "Ayşe", "Can"],
    "puan": [85, 92, 78],
})

print(df.head())
print(df["puan"].mean())          # ortalama
print(df[df["puan"] > 80])        # filtre
df["gecti"] = df["puan"] >= 80    # yeni kolon
df.to_csv("sonuc.csv", index=False)''', "l": "python"},

    {"k": ["numpy", "matematik dizi", "vektor"],
     "a": "NumPy ile hızlı sayısal işlemler (pip install numpy):",
     "c": '''import numpy as np

a = np.array([1, 2, 3, 4])
b = np.array([10, 20, 30, 40])

print(a + b)          # [11 22 33 44]
print(a * 2)          # [2 4 6 8]
print(a.mean(), a.max(), a.sum())

m = np.zeros((3, 3))  # 3x3 sıfır matrisi
r = np.random.rand(2, 2)''', "l": "python"},

    {"k": ["grafik ciz", "matplotlib", "plot", "cizim", "gorsellestir"],
     "a": "Matplotlib ile grafik çizme (pip install matplotlib):",
     "c": '''import matplotlib.pyplot as plt

x = [1, 2, 3, 4, 5]
y = [2, 4, 9, 16, 25]

plt.plot(x, y, marker="o", label="kareler")
plt.title("Basit Grafik")
plt.xlabel("x"); plt.ylabel("y")
plt.legend()
plt.grid(True)
plt.savefig("grafik.png")   # veya plt.show()''', "l": "python"},

    {"k": ["web scraping", "kaziyici", "beautifulsoup", "site verisi cek"],
     "a": "BeautifulSoup ile web kazıma (pip install beautifulsoup4 requests):",
     "c": '''import requests
from bs4 import BeautifulSoup

r = requests.get("https://example.com", timeout=10)
soup = BeautifulSoup(r.text, "html.parser")

print(soup.title.text)          # sayfa başlığı

for link in soup.find_all("a"):
    print(link.get("href"))''', "l": "python"},

    {"k": ["tkinter", "masaustu", "gui", "pencere", "arayuz yap"],
     "a": "Tkinter ile masaüstü arayüz (Python ile gelir):",
     "c": '''import tkinter as tk

pencere = tk.Tk()
pencere.title("İlk Uygulamam")
pencere.geometry("300x150")

def tikla():
    etiket.config(text="Merhaba " + giris.get())

etiket = tk.Label(pencere, text="Adını yaz:")
etiket.pack(pady=5)
giris = tk.Entry(pencere)
giris.pack()
tk.Button(pencere, text="Selamla", command=tikla).pack(pady=10)

pencere.mainloop()''', "l": "python"},

    {"k": ["mail gonder", "email", "smtp"],
     "a": "Python ile e-posta gönderme:",
     "c": '''import smtplib
from email.mime.text import MIMEText

msg = MIMEText("Merhaba, bu otomatik bir mail!")
msg["Subject"] = "Test"
msg["From"] = "sen@gmail.com"
msg["To"] = "alici@ornek.com"

with smtplib.SMTP_SSL("smtp.gmail.com", 465) as s:
    s.login("sen@gmail.com", "uygulama-sifresi")
    s.send_message(msg)
print("Gönderildi")''', "l": "python"},

    {"k": ["qr kod", "qrcode", "karekod"],
     "a": "QR kod üretme (pip install qrcode):",
     "c": '''import qrcode

img = qrcode.make("https://github.com/demirrsarppkurtlarr")
img.save("qr.png")
print("qr.png kaydedildi")''', "l": "python"},

    {"k": ["counter", "en cok gecen", "frekans", "sayim"],
     "a": "`Counter` ile frekans sayımı:",
     "c": '''from collections import Counter

metin = "aabbbccdde"
sayim = Counter(metin)

print(sayim)                 # {'b': 3, 'a': 2, ...}
print(sayim.most_common(2))  # en çok 2 tanesi
print(sayim["b"])            # 3''', "l": "python"},

    {"k": ["enumerate", "indexle", "sira numarasi"],
     "a": "`enumerate` ile index + değer birlikte:",
     "c": '''renkler = ["kırmızı", "yeşil", "mavi"]

for i, renk in enumerate(renkler):
    print(i, renk)

for i, renk in enumerate(renkler, start=1):  # 1'den başla
    print(f"{i}. {renk}")''', "l": "python"},

    {"k": ["ternary", "tek satir if", "kisa if"],
     "a": "Tek satırlık if (ternary):",
     "c": '''yas = 20
durum = "reşit" if yas >= 18 else "reşit değil"
print(durum)

# listede bile kullanılır
etiketler = ["çift" if x % 2 == 0 else "tek" for x in range(5)]
print(etiketler)''', "l": "python"},

    # --- Diğer diller ---
    {"k": ["javascript", "js kodu", "console.log", "javascript fonksiyon",
           "js fonksiyon", "javascript function", "js kod", "arrow function"],
     "a": "JavaScript temel sözdizimi:",
     "c": '''// değişkenler
const isim = "Demir";
let yas = 16;

// fonksiyon
function selamla(kisi) {
  return `Merhaba ${kisi}!`;
}

// arrow function
const topla = (a, b) => a + b;

console.log(selamla(isim));
console.log(topla(3, 5));

// dizi işlemleri
const sayilar = [1, 2, 3, 4];
console.log(sayilar.map(x => x * 2));
console.log(sayilar.filter(x => x % 2 === 0));''', "l": "javascript"},

    {"k": ["html", "web sayfasi", "html iskelet", "boilerplate"],
     "a": "HTML5 başlangıç şablonu:",
     "c": '''<!DOCTYPE html>
<html lang="tr">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Sayfam</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <h1>Merhaba Dünya!</h1>
  <p>İlk web sayfam.</p>
  <script src="app.js"></script>
</body>
</html>''', "l": "html"},

    {"k": ["css", "ortala", "center div", "stil"],
     "a": "CSS ile öğe ortalama (en modern yol):",
     "c": '''/* Flexbox ile ortala */
.kapsayici {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
}

/* Grid ile tek satırda */
.kapsayici2 {
  display: grid;
  place-items: center;
  min-height: 100vh;
}''', "l": "css"},

    {"k": ["sql select", "sorgu yaz", "sql sorgusu"],
     "a": "Temel SQL sorguları:",
     "c": '''-- seçme
SELECT isim, puan FROM ogrenciler
WHERE puan > 80
ORDER BY puan DESC
LIMIT 10;

-- ekleme
INSERT INTO ogrenciler (isim, puan) VALUES ('Ali', 85);

-- güncelleme
UPDATE ogrenciler SET puan = 90 WHERE isim = 'Ali';

-- silme
DELETE FROM ogrenciler WHERE puan < 50;

-- gruplama
SELECT sinif, AVG(puan) FROM ogrenciler GROUP BY sinif;''', "l": "sql"},

    {"k": ["git", "commit", "push", "github komut"],
     "a": "En çok kullanılan Git komutları:",
     "c": '''git init                     # repo başlat
git add .                    # tüm değişiklikleri ekle
git commit -m "mesaj"        # kaydet
git push origin main         # gönder
git pull origin main         # çek
git status                   # durum
git log --oneline            # geçmiş
git checkout -b yeni-dal     # dal oluştur + geç
git merge yeni-dal           # birleştir''', "l": "bash"},
]


# ---------------------------------------------------------------------------
# Chit-chat responses
# ---------------------------------------------------------------------------

CHITCHAT: list[tuple[list[str], list[str]]] = [
    (["merhaba", "selam", "hello", "hi", "hey", "slm", "sa"],
     ["Merhaba! 👋 Ben DimAI. Kod yazmama yardım et dersen buradayım — ör. \"python'da liste nasıl sıralanır?\"",
      "Selam! Hangi kodu yazalım? Python, JS, SQL... sor yeter."]),
    (["nasilsin", "naber", "ne haber", "iyi misin", "how are you"],
     ["İyiyim, corpus'umda geziniyordum 😄 Sen hangi kodu yazmak istiyorsun?",
      "Harikayım — az önce kendimi biraz daha eğittim. Ne kodlayalım?"]),
    (["adin ne", "kimsin", "sen nesin", "who are you", "ismin"],
     ["Ben DimAI — dış API kullanmayan, kendi kendini eğiten bir kod asistanıyım. Bilgi tabanım + küçük nöral modelim var."]),
    (["seni kim yapti", "kim gelistirdi", "yaraticin"],
     ["Beni Demir geliştirdi. Bilgi tabanım ve nöral modelim tamamen yerel çalışıyor — ChatGPT falan karışmıyor 😎"]),
    (["tesekkur", "sagol", "sag ol", "thanks", "eyvallah", "tskler"],
     ["Rica ederim! Başka kod lazım olursa buradayım 🚀", "Ne demek! Takıldığın yerde tekrar sor."]),
    (["gorusuruz", "bay bay", "hosca kal", "bye", "gule gule"],
     ["Görüşürüz! İyi kodlamalar 👨‍💻"]),
    (["ne yapabilirsin", "neler yapabilirsin", "ozelliklerin", "yetenekler", "help", "yardim"],
     ["Şunları yapabilirim:\n• Python kodu yazarım (döngü, liste, dosya, class, API...)\n• Algoritma örnekleri veririm (fibonacci, asal, sıralama...)\n• JS / HTML / CSS / SQL / Git temelleri\n• Matematik işlemleri hesaplarım (ör. \"25*4 kaç eder\")\n• Nöral modelim arka planda kendini eğitmeye devam eder\n\nÖrnek: \"sayı tahmin oyunu yaz\" veya \"dosya nasıl okunur?\""]),
    (["saka", "espri", "komik", "joke", "guldur"],
     ["Neden programcılar karanlıktan korkmaz? Çünkü ışığı `print`'lerler 😅",
      "İki byte bir barda karşılaşmış. Biri sormuş: \"Bit'ler nasıl?\" 😄"]),
    (["seni seviyorum", "cok iyisin", "harikasin", "mukemmelsin"],
     ["Teşekkürler! 🥹 O zaman hadi güzel bir şeyler kodlayalım."]),
]


SUGGESTIONS = [
    "print komutu nasıl kullanılır?",
    "sayı tahmin oyunu yaz",
    "fibonacci kodu yaz",
    "dosya nasıl okunur?",
    "listeyi nasıl sıralarım?",
    "class örneği göster",
    "flask web uygulaması yaz",
    "şifre üretici yaz",
]


class Brain:
    def __init__(self) -> None:
        try:
            from model.brain_extra import EXTRA_KB
        except ImportError:
            from brain_extra import EXTRA_KB  # type: ignore
        self._kb = []
        for entry in KB + EXTRA_KB:
            keys = [_norm(k) for k in entry["k"]]
            self._kb.append({**entry, "nk": keys})

    # -------------------- matching --------------------

    GENERIC_WORDS = {
        "nedir", "ne", "nasil", "yaz", "ornek", "ornegi", "kod", "goster",
        "kullanilir", "icin", "yap", "olustur", "how", "write", "code",
    }

    def _score_entry(self, text: str, words: set[str], entry: dict) -> float:
        score = 0.0
        for key in entry["nk"]:
            # substring match only for long/multiword keys; short keys must be whole words
            strong = key in words or (key in text and (len(key) >= 6 or " " in key))
            if strong:
                # longer, more specific keys outrank short generic ones
                score += 3.0 + key.count(" ") * 2.0 + len(key) * 0.05
                continue
            key_words = key.split()
            specific = [kw for kw in key_words if kw not in self.GENERIC_WORDS]
            hits = sum(1 for kw in key_words if kw in words)
            specific_hits = sum(1 for kw in specific if kw in words)
            if hits == len(key_words) and hits:
                score += 2.0 * hits
            elif specific_hits:
                # only topic words count toward partial credit
                score += 0.6 * specific_hits
            elif specific:
                for kw in specific:
                    close = difflib.get_close_matches(kw, words, n=1, cutoff=0.85)
                    if close:
                        score += 0.8
        return score

    def _match_kb(self, text: str, exclude: Optional[dict] = None) -> Optional[dict]:
        ranked = self._rank_kb(text)
        for entry, score in ranked:
            if exclude is not None and entry is exclude:
                continue
            if score >= 2.0:
                return entry
            break
        return None

    def _rank_kb(self, text: str) -> list:
        words = set(text.split())
        scored = []
        for entry in self._kb:
            s = self._score_entry(text, words, entry)
            if s > 0:
                scored.append((entry, s))
        scored.sort(key=lambda t: -t[1])
        return scored

    def _match_chitchat(self, text: str) -> Optional[str]:
        words = set(text.split())
        for keys, answers in CHITCHAT:
            for key in keys:
                nk = _norm(key)
                if nk in words or (len(nk) >= 6 and nk in text):
                    return random.choice(answers)
        return None

    def _try_math(self, raw: str) -> Optional[str]:
        cleaned = raw.lower()
        for w in ["kac eder", "kaç eder", "kac", "kaç", "hesapla", "sonucu ne", "=", "?"]:
            cleaned = cleaned.replace(w, " ")
        cleaned = cleaned.replace("x", "*").replace("çarpı", "*").replace("carpi", "*")
        cleaned = cleaned.replace("artı", "+").replace("arti", "+")
        cleaned = cleaned.replace("eksi", "-").replace("bölü", "/").replace("bolu", "/")
        cleaned = cleaned.strip()
        if not re.fullmatch(r"[\d\s+\-*/().%]+", cleaned or ""):
            return None
        if not re.search(r"\d", cleaned) or not re.search(r"[+\-*/%]", cleaned):
            return None
        try:
            result = eval(cleaned, {"__builtins__": {}}, {})  # noqa: S307 sanitized above
        except Exception:
            return None
        if isinstance(result, float) and result.is_integer():
            result = int(result)
        return f"Sonuç: **{result}**\n\n`{cleaned.strip()} = {result}`"

    @staticmethod
    def _kb_result(entry: dict) -> dict:
        result = {"reply": entry["a"], "source": "kb"}
        if entry.get("c"):
            result["code"] = entry["c"]
            result["lang"] = entry.get("l", "python")
        return result

    # -------------------- conversation memory --------------------

    FOLLOWUP_HINTS = {
        "peki", "onu", "bunu", "sunu", "o", "bu", "devam", "baska", "daha",
        "tekrar", "detay", "detayli", "acikla", "anlatsana", "ornek",
        "ornegi", "birdaha", "yine", "ayrica", "hani", "onun", "bunun",
        "ona", "buna", "ondan", "bundan", "orada", "orasi", "oyle", "soyle",
    }

    QUESTION_WORDS = {
        "nedir", "ne", "nasil", "kim", "kimdir", "neden", "niye", "nerede",
        "neresi", "nereden", "kac", "kactir", "hangi", "hangisi", "zaman",
        "midir", "mi", "mu", "mudur", "acaba", "yani", "iste", "cok", "en",
        "kadar", "ki", "ya", "ve", "de", "da", "ile", "icin", "olur", "oluyor",
        "olabilir", "var", "yok", "gibi", "bana", "bize", "biraz",
    }
    MORE_PATTERNS = ("baska ornek", "bir ornek daha", "devam et", "daha fazla",
                     "birtane daha", "bir tane daha", "baska bir", "yenisini")

    def _last_user_messages(self, history: list) -> list[str]:
        return [
            str(h.get("content", ""))
            for h in history
            if h.get("role") == "user" and str(h.get("content", "")).strip()
        ]

    def _last_topic_entry(self, history: list) -> Optional[dict]:
        """Find the most recent KB topic the user asked about."""
        for msg in reversed(self._last_user_messages(history)):
            entry = self._match_kb(_norm(msg))
            if entry:
                return entry
        return None

    def _topic_keywords(self, history: list, limit: int = 6) -> list[str]:
        """Extract the conversation topic from recent user messages.

        Works for ANY topic (KB, web-researched or unknown): pulls content
        words from the most recent user message that has any, walking
        backwards through history.
        """
        stop = self.GENERIC_WORDS | self.FOLLOWUP_HINTS | self.QUESTION_WORDS
        out: list[str] = []
        for msg in reversed(self._last_user_messages(history)[-4:]):
            for w in _norm(msg).split():
                if len(w) >= 3 and w not in stop and w not in out:
                    out.append(w)
            if out:
                break  # en yakın "içerikli" mesaj konuyu belirler
        return out[:limit]

    def _remember_name(self, history: list, current: str) -> Optional[str]:
        pattern = r"(?:benim )?(?:adim|ismim)\s+([a-zçğıöşü]+)"
        for msg in [current] + list(reversed(self._last_user_messages(history))):
            m = re.search(pattern, _norm(msg))
            if m and m.group(1) not in ("ne", "neydi", "nedir"):
                return m.group(1).capitalize()
        return None

    # -------------------- public API --------------------

    def reply(self, message: str, history: Optional[list] = None) -> dict:
        history = history or []
        raw = (message or "").strip()
        text = _norm(raw)

        if not text:
            return {"reply": "Bir şeyler yaz da konuşalım 🙂", "source": "chat"}

        math_answer = self._try_math(raw)
        if math_answer:
            return {"reply": math_answer, "source": "math"}

        # name memory
        intro = re.search(r"(?:benim )?(?:adim|ismim)\s+([a-zçğıöşü]+)", text)
        if intro and intro.group(1) not in ("ne", "neydi", "nedir"):
            return {
                "reply": f"Memnun oldum **{intro.group(1).capitalize()}**! 🤝 Aklımda. Ne kodlayalım?",
                "source": "chat",
            }
        if re.search(r"(adim|ismim|adimi)\s*(ne|neydi|nedir|hatirliyor)", text):
            name = self._remember_name(history, raw)
            if name:
                return {"reply": f"Tabii, adın **{name}** 😊", "source": "chat"}
            return {"reply": "Daha söylemedin! \"Benim adım ...\" dersen aklımda tutarım.", "source": "chat"}

        kb = self._match_kb(text)
        chit = self._match_chitchat(text)

        words = set(text.split())
        is_short = len(words) <= 6
        has_followup_hint = bool(words & self.FOLLOWUP_HINTS)

        # "başka örnek / devam et" → aynı konudan farklı bir kayıt getir
        if is_short and (any(p in text for p in self.MORE_PATTERNS) or
                         (has_followup_hint and not kb)):
            prev = self._last_topic_entry(history)
            if prev:
                # önceki konunun en belirgin kelimesi (ör. "dosya", "fibonacci")
                word_counts: dict = {}
                for key in prev["nk"]:
                    for w in key.split():
                        if w not in self.GENERIC_WORDS and len(w) > 2:
                            word_counts[w] = word_counts.get(w, 0) + 1
                seed = max(word_counts, key=word_counts.get) if word_counts else ""

                if any(p in text for p in self.MORE_PATTERNS):
                    # ilgili ama farklı bir kayıt: konu + cevap metni üzerinden ara
                    related_text = _norm(prev["a"])[:200] + " " + seed
                    for entry, _score in self._rank_kb(related_text):
                        if entry is not prev:
                            result = self._kb_result(entry)
                            result["reply"] = "İlgili başka bir örnek:\n\n" + result["reply"]
                            return result
                    return self._kb_result(prev)

                # takip sorusu: yeni mesaj + konu kelimesini birleştirip tekrar dene
                combined = self._match_kb(text + " " + seed)
                if combined:
                    return self._kb_result(combined)
                return self._kb_result(prev)

        # ---- takip sorusu: önceki konuya bağlı kal ----
        stop = self.GENERIC_WORDS | self.FOLLOWUP_HINTS | self.QUESTION_WORDS
        content_words = {w for w in words if len(w) >= 3 and w not in stop}
        topic = self._topic_keywords(history)
        is_followup = bool(history) and (has_followup_hint or not content_words)

        if is_followup and topic and not any(p in text for p in self.MORE_PATTERNS):
            # sadece selamlaşma/teşekkür ise normal sohbet cevabı ver
            if chit and not content_words:
                return {"reply": chit, "source": "chat"}
            topic_str = " ".join(topic)
            comb = self._rank_kb(text + " " + topic_str)
            bare = self._rank_kb(text)
            comb_s = comb[0][1] if comb else 0.0
            bare_s = bare[0][1] if bare else 0.0
            # konu + soru birlikte güçlü bir KB kaydına oturuyorsa onu ver
            if comb and comb_s >= 3.0 and comb_s >= bare_s:
                return self._kb_result(comb[0][0])
            # konudan bağımsız ama ÇOK güçlü bir eşleşme varsa kabul et
            if bare and bare_s >= 5.0:
                return self._kb_result(bare[0][0])
            # aksi halde konuyu koruyarak web/öğrenilmiş bilgiye git —
            # zayıf KB eşleşmelerinin konuyu kaçırmasına izin verme
            return {
                "reply": (
                    "Bunu tam anlayamadım 🤔 Şunları deneyebilirsin:\n"
                    + "\n".join(f"• {s}" for s in random.sample(SUGGESTIONS, 4))
                ),
                "source": "fallback",
                "research_query": topic_str + " " + raw,
            }

        # If the message clearly asks for code, prefer KB over chitchat
        code_signals = ["kod", "yaz", "nasil", "ornek", "goster", "code", "how", "write"]
        wants_code = any(s in text for s in code_signals)

        if kb and (wants_code or not chit):
            return self._kb_result(kb)
        if chit:
            return {"reply": chit, "source": "chat"}
        if kb:
            return self._kb_result(kb)

        # Hiç eşleşme yok → web/öğrenilmiş bilgi araştırması.
        # Kısa/az içerikli mesajlarda sunucu önce soruyu, bulamazsa
        # konu + soruyu dener (iki aşamalı bağlam).
        result = {
            "reply": (
                "Bunu tam anlayamadım 🤔 Şunları deneyebilirsin:\n"
                + "\n".join(f"• {s}" for s in random.sample(SUGGESTIONS, 4))
            ),
            "source": "fallback",
            "research_query": raw,
        }
        if topic and len(content_words) <= 2:
            result["context_query"] = " ".join(topic) + " " + raw
        return result


brain = Brain()
