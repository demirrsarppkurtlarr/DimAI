"""Extra knowledge for DimAI brain — more topics, algorithms, tools, concepts."""

EXTRA_KB: list[dict] = [
    # --- Python ileri seviye ---
    {"k": ["dict comprehension", "sozluk comprehension", "tek satirda sozluk"],
     "a": "Dict comprehension ile tek satırda sözlük:",
     "c": '''kareler = {x: x**2 for x in range(6)}
print(kareler)   # {0: 0, 1: 1, 2: 4, ...}

fiyatlar = {"elma": 10, "armut": 15, "muz": 8}
zamli = {k: v * 1.2 for k, v in fiyatlar.items()}
ucuzlar = {k: v for k, v in fiyatlar.items() if v < 12}''', "l": "python"},

    {"k": ["match case", "switch case", "match statement"],
     "a": "Python 3.10+ `match-case` (switch benzeri):",
     "c": '''def islem(komut):
    match komut.split():
        case ["git", yon]:
            return f"{yon} yönüne gidiliyor"
        case ["al", *esyalar]:
            return f"Alındı: {esyalar}"
        case ["dur"] | ["bekle"]:
            return "Duruldu"
        case _:
            return "Bilinmeyen komut"

print(islem("git kuzey"))
print(islem("al kilic kalkan"))''', "l": "python"},

    {"k": ["walrus", "walrus operator", ":="],
     "a": "Walrus operatörü `:=` — atama + kullanım tek adımda:",
     "c": '''# klasik
veri = input("yaz: ")
while veri != "q":
    print(veri)
    veri = input("yaz: ")

# walrus ile
while (veri := input("yaz: ")) != "q":
    print(veri)

if (n := len([1,2,3,4])) > 3:
    print(f"{n} eleman var")''', "l": "python"},

    {"k": ["itertools", "kombinasyon", "permutasyon", "combination", "permutation"],
     "a": "`itertools` ile kombinasyon ve permütasyon:",
     "c": '''from itertools import combinations, permutations, product, cycle

print(list(combinations([1,2,3], 2)))   # [(1,2),(1,3),(2,3)]
print(list(permutations("ab")))          # [('a','b'),('b','a')]
print(list(product([0,1], repeat=2)))    # [(0,0),(0,1),(1,0),(1,1)]

from itertools import count, islice
tek_sayilar = (x for x in count(1, 2))
print(list(islice(tek_sayilar, 5)))      # [1,3,5,7,9]''', "l": "python"},

    {"k": ["defaultdict", "deque", "collections"],
     "a": "`collections` modülünün güçlü yapıları:",
     "c": '''from collections import defaultdict, deque, namedtuple

# defaultdict: olmayan anahtar hata vermez
gruplar = defaultdict(list)
gruplar["a"].append(1)
gruplar["a"].append(2)
print(gruplar)

# deque: iki uçlu hızlı kuyruk
d = deque([1, 2, 3])
d.appendleft(0)
d.append(4)
print(d.popleft(), d.pop())   # 0 4

# namedtuple
Nokta = namedtuple("Nokta", "x y")
p = Nokta(3, 5)
print(p.x, p.y)''', "l": "python"},

    {"k": ["lru_cache", "memoization", "onbellek", "cache"],
     "a": "`lru_cache` ile fonksiyon sonuçlarını önbellekleme:",
     "c": '''from functools import lru_cache

@lru_cache(maxsize=None)
def fib(n):
    if n < 2:
        return n
    return fib(n-1) + fib(n-2)

print(fib(100))   # anında! cache olmasa yıllar sürerdi''', "l": "python"},

    {"k": ["dataclass", "data class", "veri sinifi"],
     "a": "`dataclass` ile az kodla sınıf:",
     "c": '''from dataclasses import dataclass, field

@dataclass
class Urun:
    isim: str
    fiyat: float
    stok: int = 0
    etiketler: list = field(default_factory=list)

u = Urun("Klavye", 450.0, 12)
print(u)                    # otomatik __repr__
print(u.fiyat * u.stok)''', "l": "python"},

    {"k": ["enum", "sabit", "enumeration"],
     "a": "`Enum` ile sabit değerler:",
     "c": '''from enum import Enum, auto

class Durum(Enum):
    BEKLIYOR = auto()
    CALISIYOR = auto()
    BITTI = auto()

d = Durum.CALISIYOR
print(d.name, d.value)

if d == Durum.CALISIYOR:
    print("İşlem sürüyor...")''', "l": "python"},

    {"k": ["context manager", "with statement", "kaynak yonetimi"],
     "a": "Kendi context manager'ını yazmak:",
     "c": '''from contextlib import contextmanager
import time

@contextmanager
def zamanla(isim):
    t = time.time()
    yield
    print(f"{isim}: {time.time()-t:.3f} sn")

with zamanla("döngü"):
    toplam = sum(range(1000000))
print(toplam)''', "l": "python"},

    {"k": ["property", "getter", "setter"],
     "a": "`@property` ile kontrollü erişim:",
     "c": '''class Hesap:
    def __init__(self):
        self._bakiye = 0

    @property
    def bakiye(self):
        return self._bakiye

    @bakiye.setter
    def bakiye(self, deger):
        if deger < 0:
            raise ValueError("Bakiye negatif olamaz!")
        self._bakiye = deger

h = Hesap()
h.bakiye = 100
print(h.bakiye)''', "l": "python"},

    {"k": ["staticmethod", "classmethod", "sinif metodu"],
     "a": "`@staticmethod` ve `@classmethod` farkı:",
     "c": '''class Matematik:
    pi = 3.14159

    @staticmethod
    def topla(a, b):          # self yok, bağımsız
        return a + b

    @classmethod
    def daire_alani(cls, r):  # cls = sınıfın kendisi
        return cls.pi * r * r

print(Matematik.topla(3, 4))
print(Matematik.daire_alani(5))''', "l": "python"},

    {"k": ["subprocess", "komut calistir", "terminal komutu", "shell komutu"],
     "a": "Python'dan terminal komutu çalıştırma:",
     "c": '''import subprocess

sonuc = subprocess.run(
    ["ls", "-la"],
    capture_output=True, text=True,
)
print(sonuc.stdout)
print("Hata kodu:", sonuc.returncode)''', "l": "python"},

    {"k": ["logging", "log", "kayit tutma"],
     "a": "Profesyonel log tutma:",
     "c": '''import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    filename="uygulama.log",
)

logging.info("Uygulama başladı")
logging.warning("Dikkat, stok azalıyor")
logging.error("Bağlantı hatası!")''', "l": "python"},

    {"k": ["unittest", "pytest", "test yaz", "birim test"],
     "a": "Test yazma (pytest en pratik olanı):",
     "c": '''# test_hesap.py  →  çalıştır: pytest
def topla(a, b):
    return a + b

def test_topla():
    assert topla(2, 3) == 5
    assert topla(-1, 1) == 0

def test_topla_float():
    assert abs(topla(0.1, 0.2) - 0.3) < 1e-9''', "l": "python"},

    {"k": ["argparse", "komut satiri", "cli", "argument"],
     "a": "Komut satırı argümanları için `argparse`:",
     "c": '''import argparse

parser = argparse.ArgumentParser(description="Selamlayıcı")
parser.add_argument("isim", help="Selamlanacak kişi")
parser.add_argument("--kez", type=int, default=1)
args = parser.parse_args()

for _ in range(args.kez):
    print(f"Merhaba {args.isim}!")

# kullanım: python app.py Ali --kez 3''', "l": "python"},

    {"k": ["hashlib", "hash", "sha256", "md5", "sifrele"],
     "a": "Hash (özet) alma — şifre saklamada temel:",
     "c": '''import hashlib

metin = "gizli şifre"
ozet = hashlib.sha256(metin.encode()).hexdigest()
print(ozet)

# dosya hash'i
def dosya_hash(yol):
    h = hashlib.sha256()
    with open(yol, "rb") as f:
        for blok in iter(lambda: f.read(8192), b""):
            h.update(blok)
    return h.hexdigest()''', "l": "python"},

    {"k": ["base64", "encode", "decode", "kodlama"],
     "a": "Base64 kodlama/çözme:",
     "c": '''import base64

veri = "Merhaba Dünya".encode()
kodlu = base64.b64encode(veri).decode()
print(kodlu)

cozulmus = base64.b64decode(kodlu).decode()
print(cozulmus)''', "l": "python"},

    {"k": ["uuid", "benzersiz id", "unique id"],
     "a": "Benzersiz ID üretme:",
     "c": '''import uuid

print(uuid.uuid4())          # rastgele benzersiz
print(str(uuid.uuid4())[:8]) # kısa versiyon

import secrets
print(secrets.token_hex(8))  # güvenli rastgele hex''', "l": "python"},

    {"k": ["sys argv", "sys", "cikis", "exit"],
     "a": "`sys` modülü temel kullanımı:",
     "c": '''import sys

print(sys.argv)          # komut satırı argümanları
print(sys.version)       # python sürümü
print(sys.platform)      # işletim sistemi

if len(sys.argv) < 2:
    print("Kullanım: python app.py <dosya>")
    sys.exit(1)''', "l": "python"},

    {"k": ["environment variable", "ortam degiskeni", "env", "getenv"],
     "a": "Ortam değişkenleri (API anahtarları için şart):",
     "c": '''import os

# oku
api_key = os.environ.get("API_KEY", "varsayilan")
print(api_key)

# .env dosyası ile (pip install python-dotenv)
from dotenv import load_dotenv
load_dotenv()
sifre = os.getenv("DB_PASSWORD")''', "l": "python"},

    {"k": ["fastapi", "modern api", "rest api yaz"],
     "a": "FastAPI ile modern REST API (pip install fastapi uvicorn):",
     "c": '''from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

class Urun(BaseModel):
    isim: str
    fiyat: float

urunler = []

@app.get("/urunler")
def listele():
    return urunler

@app.post("/urunler")
def ekle(urun: Urun):
    urunler.append(urun)
    return {"ok": True}

# çalıştır: uvicorn main:app --reload''', "l": "python"},

    {"k": ["selenium", "tarayici otomasyon", "browser bot"],
     "a": "Selenium ile tarayıcı otomasyonu (pip install selenium):",
     "c": '''from selenium import webdriver
from selenium.webdriver.common.by import By

driver = webdriver.Chrome()
driver.get("https://example.com")

baslik = driver.find_element(By.TAG_NAME, "h1")
print(baslik.text)

buton = driver.find_element(By.ID, "giris")
buton.click()

driver.quit()''', "l": "python"},

    {"k": ["excel", "openpyxl", "xlsx"],
     "a": "Excel dosyaları için `openpyxl` (pip install openpyxl):",
     "c": '''from openpyxl import Workbook, load_workbook

# yaz
wb = Workbook()
ws = wb.active
ws.append(["isim", "puan"])
ws.append(["Ali", 85])
wb.save("veriler.xlsx")

# oku
wb = load_workbook("veriler.xlsx")
for satir in wb.active.iter_rows(values_only=True):
    print(satir)''', "l": "python"},

    {"k": ["resim", "pillow", "pil", "image", "fotograf isle"],
     "a": "Pillow ile resim işleme (pip install pillow):",
     "c": '''from PIL import Image, ImageFilter

img = Image.open("foto.jpg")
print(img.size)

kucuk = img.resize((300, 200))
gri = img.convert("L")
bulanik = img.filter(ImageFilter.BLUR)
dondu = img.rotate(90)

kucuk.save("kucuk.jpg")''', "l": "python"},

    {"k": ["discord bot", "discord"],
     "a": "Discord botu (pip install discord.py):",
     "c": '''import discord
from discord.ext import commands

bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

@bot.event
async def on_ready():
    print(f"{bot.user} hazır!")

@bot.command()
async def selam(ctx):
    await ctx.send(f"Merhaba {ctx.author.mention}!")

bot.run("BOT_TOKEN")''', "l": "python"},

    {"k": ["telegram bot", "telegram"],
     "a": "Telegram botu (pip install python-telegram-bot):",
     "c": '''from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Merhaba! Ben bir botum 🤖")

app = ApplicationBuilder().token("BOT_TOKEN").build()
app.add_handler(CommandHandler("start", start))
app.run_polling()''', "l": "python"},

    # --- Algoritmalar ---
    {"k": ["quick sort", "quicksort", "hizli siralama"],
     "a": "Quick sort — ortalama O(n log n):",
     "c": '''def quick_sort(arr):
    if len(arr) <= 1:
        return arr
    pivot = arr[len(arr) // 2]
    sol = [x for x in arr if x < pivot]
    orta = [x for x in arr if x == pivot]
    sag = [x for x in arr if x > pivot]
    return quick_sort(sol) + orta + quick_sort(sag)

print(quick_sort([5, 2, 9, 1, 7, 3]))''', "l": "python"},

    {"k": ["merge sort", "birlestirme siralama"],
     "a": "Merge sort — garantili O(n log n):",
     "c": '''def merge_sort(arr):
    if len(arr) <= 1:
        return arr
    orta = len(arr) // 2
    sol = merge_sort(arr[:orta])
    sag = merge_sort(arr[orta:])
    sonuc = []
    i = j = 0
    while i < len(sol) and j < len(sag):
        if sol[i] <= sag[j]:
            sonuc.append(sol[i]); i += 1
        else:
            sonuc.append(sag[j]); j += 1
    return sonuc + sol[i:] + sag[j:]

print(merge_sort([5, 2, 9, 1, 7]))''', "l": "python"},

    {"k": ["insertion sort", "eklemeli siralama", "selection sort", "secmeli siralama"],
     "a": "Insertion ve selection sort:",
     "c": '''def insertion_sort(arr):
    a = arr[:]
    for i in range(1, len(a)):
        key = a[i]
        j = i - 1
        while j >= 0 and a[j] > key:
            a[j + 1] = a[j]
            j -= 1
        a[j + 1] = key
    return a

def selection_sort(arr):
    a = arr[:]
    for i in range(len(a)):
        m = min(range(i, len(a)), key=a.__getitem__)
        a[i], a[m] = a[m], a[i]
    return a

print(insertion_sort([4, 1, 3]))
print(selection_sort([4, 1, 3]))''', "l": "python"},

    {"k": ["stack", "yigin", "queue", "kuyruk veri yapisi"],
     "a": "Stack (yığın) ve Queue (kuyruk):",
     "c": '''# Stack: son giren ilk çıkar (LIFO)
stack = []
stack.append(1); stack.append(2)
print(stack.pop())    # 2

# Queue: ilk giren ilk çıkar (FIFO)
from collections import deque
q = deque()
q.append("a"); q.append("b")
print(q.popleft())    # a''', "l": "python"},

    {"k": ["linked list", "bagli liste"],
     "a": "Bağlı liste (linked list) implementasyonu:",
     "c": '''class Dugum:
    def __init__(self, veri):
        self.veri = veri
        self.sonraki = None

class BagliListe:
    def __init__(self):
        self.bas = None

    def ekle(self, veri):
        yeni = Dugum(veri)
        if not self.bas:
            self.bas = yeni
            return
        d = self.bas
        while d.sonraki:
            d = d.sonraki
        d.sonraki = yeni

    def yazdir(self):
        d = self.bas
        while d:
            print(d.veri, end=" -> ")
            d = d.sonraki
        print("None")

l = BagliListe()
l.ekle(1); l.ekle(2); l.ekle(3)
l.yazdir()''', "l": "python"},

    {"k": ["anagram"],
     "a": "Anagram kontrolü (aynı harflerden mi oluşuyor):",
     "c": '''def anagram_mi(a, b):
    return sorted(a.lower()) == sorted(b.lower())

print(anagram_mi("listen", "silent"))   # True
print(anagram_mi("kedi", "deki"))       # True''', "l": "python"},

    {"k": ["sezar", "caesar", "sifreleme"],
     "a": "Sezar şifrelemesi:",
     "c": '''def sezar(metin, kaydir):
    sonuc = ""
    for h in metin:
        if h.isalpha():
            taban = ord("A") if h.isupper() else ord("a")
            sonuc += chr((ord(h) - taban + kaydir) % 26 + taban)
        else:
            sonuc += h
    return sonuc

sifreli = sezar("Merhaba", 3)
print(sifreli)              # Phukded
print(sezar(sifreli, -3))   # Merhaba''', "l": "python"},

    {"k": ["binary", "ikilik", "onluk", "decimal", "taban cevir", "hex"],
     "a": "Sayı tabanı dönüşümleri:",
     "c": '''sayi = 42

print(bin(sayi))       # 0b101010
print(hex(sayi))       # 0x2a
print(oct(sayi))       # 0o52

print(int("101010", 2))   # 42 (ikilikten)
print(int("2a", 16))      # 42 (hexten)
print(format(sayi, "08b"))# 00101010''', "l": "python"},

    {"k": ["armstrong", "narsist sayi"],
     "a": "Armstrong (narsist) sayı kontrolü:",
     "c": '''def armstrong_mu(n):
    basamaklar = str(n)
    k = len(basamaklar)
    return n == sum(int(b) ** k for b in basamaklar)

print(armstrong_mu(153))   # True (1³+5³+3³=153)
print([x for x in range(1000) if armstrong_mu(x)])''', "l": "python"},

    {"k": ["mukemmel sayi", "perfect number"],
     "a": "Mükemmel sayı (bölenlerinin toplamı kendisine eşit):",
     "c": '''def mukemmel_mi(n):
    return n > 1 and sum(i for i in range(1, n) if n % i == 0) == n

print(mukemmel_mi(28))   # True (1+2+4+7+14=28)
print([x for x in range(1, 500) if mukemmel_mi(x)])''', "l": "python"},

    {"k": ["collatz", "3n+1"],
     "a": "Collatz dizisi (3n+1 problemi):",
     "c": '''def collatz(n):
    adimlar = [n]
    while n != 1:
        n = n // 2 if n % 2 == 0 else 3 * n + 1
        adimlar.append(n)
    return adimlar

print(collatz(27))
print("Adım sayısı:", len(collatz(27)))''', "l": "python"},

    {"k": ["hanoi", "tower of hanoi", "hanoi kulesi"],
     "a": "Hanoi Kulesi çözümü:",
     "c": '''def hanoi(n, kaynak, hedef, yardimci):
    if n == 1:
        print(f"{kaynak} -> {hedef}")
        return
    hanoi(n - 1, kaynak, yardimci, hedef)
    print(f"{kaynak} -> {hedef}")
    hanoi(n - 1, yardimci, hedef, kaynak)

hanoi(3, "A", "C", "B")''', "l": "python"},

    {"k": ["asal carpan", "prime factor", "carpanlara ayir"],
     "a": "Asal çarpanlara ayırma:",
     "c": '''def asal_carpanlar(n):
    carpanlar = []
    b = 2
    while b * b <= n:
        while n % b == 0:
            carpanlar.append(b)
            n //= b
        b += 1
    if n > 1:
        carpanlar.append(n)
    return carpanlar

print(asal_carpanlar(360))   # [2, 2, 2, 3, 3, 5]''', "l": "python"},

    {"k": ["roman", "roma rakami"],
     "a": "Roma rakamına çevirme:",
     "c": '''def romaya(n):
    degerler = [(1000,"M"),(900,"CM"),(500,"D"),(400,"CD"),
                (100,"C"),(90,"XC"),(50,"L"),(40,"XL"),
                (10,"X"),(9,"IX"),(5,"V"),(4,"IV"),(1,"I")]
    sonuc = ""
    for deger, sembol in degerler:
        while n >= deger:
            sonuc += sembol
            n -= deger
    return sonuc

print(romaya(2024))   # MMXXIV''', "l": "python"},

    # --- Kavramlar (kod gerektirmeyen) ---
    {"k": ["yapay zeka nedir", "ai nedir", "machine learning nedir", "makine ogrenmesi nedir"],
     "a": "**Yapay zeka (AI)**, bilgisayarların insan benzeri görevleri yapabilmesidir: öğrenme, karar verme, dil anlama.\n\n**Makine öğrenmesi (ML)** ise AI'ın bir alt dalı — kurallar tek tek yazılmaz, sistem verilerden örüntü öğrenir.\n\n• **Denetimli öğrenme**: etiketli veriyle (spam/değil)\n• **Denetimsiz**: etiketsiz veride örüntü bulma (kümeleme)\n• **Pekiştirmeli**: deneme-yanılma + ödül (oyun AI'ları)\n\nBen de basit bir örneğim: bilgi tabanı + kendi kendini eğiten küçük bir sinir ağı kullanıyorum."},

    {"k": ["python nedir", "python ne ise yarar", "neden python"],
     "a": "**Python**, 1991'de Guido van Rossum'un yarattığı, okunabilirliğiyle ünlü programlama dilidir.\n\n**Neden popüler?**\n• Sözdizimi neredeyse İngilizce gibi\n• Devasa kütüphane ekosistemi (pip)\n• Yapay zeka, veri bilimi, web, otomasyon — her yerde\n\n**Kullanım alanları:** AI/ML (PyTorch, TensorFlow), web (Django, Flask), veri analizi (pandas), otomasyon, oyun, siber güvenlik.\n\nBaşlamak için: `print(\"Merhaba!\")` yaz, gerisi gelir 🚀"},

    {"k": ["algoritma nedir", "algorithm nedir"],
     "a": "**Algoritma**, bir problemi çözmek için izlenen adım adım yol tarifidir. Yemek tarifi gibi: sırayla uygula, sonuç çıksın.\n\n**İyi algoritmanın ölçüsü karmaşıklıktır (Big-O):**\n• O(1) — sabit: dizinin ilk elemanı\n• O(log n) — çok hızlı: binary search\n• O(n) — doğrusal: listede arama\n• O(n log n) — iyi sıralamalar: merge sort\n• O(n²) — yavaş: bubble sort\n• O(2ⁿ) — kaçın: naif fibonacci\n\nÖrnek istersen: \"binary search yaz\" de."},

    {"k": ["api nedir", "rest nedir", "endpoint nedir"],
     "a": "**API** (Application Programming Interface), iki yazılımın konuşma yoludur. Garson gibi: sen sipariş verirsin (istek), mutfağa iletir, yemeği getirir (cevap).\n\n**REST API** en yaygın türü:\n• `GET /kullanicilar` → listele\n• `POST /kullanicilar` → ekle\n• `PUT /kullanicilar/5` → güncelle\n• `DELETE /kullanicilar/5` → sil\n\nCevaplar genelde **JSON** formatındadır. Python'da `requests` ile kullanılır — \"requests örneği\" diye sor, kod vereyim."},

    {"k": ["git nedir", "github nedir", "version control"],
     "a": "**Git**, kod değişikliklerini kaydeden versiyon kontrol sistemidir — kodun zaman makinesi. Her `commit` bir kayıt noktasıdır; istediğin ana dönebilirsin.\n\n**GitHub** ise Git depolarını internette barındıran platform: yedekleme + ekip çalışması + açık kaynak paylaşımı.\n\nTemel akış:\n1. `git add .` — değişiklikleri seç\n2. `git commit -m \"mesaj\"` — kaydet\n3. `git push` — GitHub'a gönder\n\n\"git komutları\" diye sorarsan komut listesi veririm."},

    {"k": ["degiskenler arasindaki fark", "list tuple fark", "mutable immutable"],
     "a": "**Mutable (değişebilir)** vs **Immutable (değişemez)**:\n\n• `list`, `dict`, `set` → mutable: yerinde değişir\n• `str`, `tuple`, `int` → immutable: her değişiklik yeni nesne yaratır\n\n```python\na = [1, 2]; a.append(3)   # aynı liste değişti\ns = \"ab\"; s += \"c\"        # yeni string oluştu\n```\n\nBu yüzden fonksiyona liste geçirirsen içini değiştirebilir ama string'i değiştiremez."},

    {"k": ["hata cozumu", "hata aliyorum", "calismiyor", "bug", "debug"],
     "a": "Hata çözmenin sistematik yolu:\n\n1. **Hata mesajını sonuna kadar oku** — son satır asıl sebep\n2. **Satır numarasına bak** — traceback sana yeri söyler\n3. **print ile ara değerleri yazdır** veya `breakpoint()` koy\n4. Hata mesajını Google'a aynen yapıştır\n\nSık hatalar:\n• `NameError` → tanımsız değişken (yazım hatası?)\n• `TypeError` → yanlış tip (str + int gibi)\n• `IndexError` → listede olmayan index\n• `KeyError` → dict'te olmayan anahtar\n• `IndentationError` → girinti bozuk\n\nHatanı buraya yapıştır, birlikte bakalım."},

    {"k": ["hangi dil", "hangi programlama dili", "dil onerisi", "nereden baslamali"],
     "a": "**Yeni başlıyorsan: Python.** Nokta.\n\nSonrası hedefe göre:\n• **Web sitesi** → JavaScript (+ HTML/CSS)\n• **Mobil** → Kotlin (Android), Swift (iOS) veya Flutter/React Native\n• **Oyun** → C# (Unity) veya C++ (Unreal)\n• **Yapay zeka / veri** → Python\n• **Sistem / performans** → Rust, C++\n• **Şirket backend'i** → Java, Go, C#\n\nÖnemli olan ilk dili iyi öğrenmek — ikincisi çok daha kolay gelir."},

    {"k": ["recursion nedir", "ozyineleme nedir"],
     "a": "**Recursion (özyineleme)**, fonksiyonun kendini çağırmasıdır. İki şart:\n\n1. **Temel durum (base case)** — durma noktası\n2. **Küçültme** — her çağrı problemi küçültmeli\n\n```python\ndef geri_say(n):\n    if n == 0:          # temel durum\n        print(\"Bitti!\")\n        return\n    print(n)\n    geri_say(n - 1)     # küçült\n```\n\nAyna karşısında ayna gibi — ama sonu olan. \"faktöriyel yaz\" veya \"fibonacci\" diye sor, örnek vereyim."},

    {"k": ["json nedir"],
     "a": "**JSON** (JavaScript Object Notation), veri taşımanın evrensel formatı. API'lerin %99'u JSON konuşur.\n\n```json\n{\n  \"isim\": \"Demir\",\n  \"yas\": 16,\n  \"diller\": [\"Python\", \"JS\"],\n  \"aktif\": true\n}\n```\n\nPython karşılıkları: nesne→dict, dizi→list, true→True, null→None.\n\n\"json oku yaz\" diye sorarsan Python kodunu veririm."},

    {"k": ["sql nedir", "veritabani nedir", "database nedir"],
     "a": "**Veritabanı**, verileri düzenli ve kalıcı saklayan sistemdir. **SQL** ise onunla konuşma dilidir.\n\n**İlişkisel (SQL):** PostgreSQL, MySQL, SQLite — tablolar halinde, ilişkili veri\n**NoSQL:** MongoDB (belge), Redis (anahtar-değer) — esnek yapı\n\nBaşlangıç için **SQLite** ideal: kurulum yok, tek dosya, Python'da hazır geliyor. \"sqlite örneği\" diye sor, kod vereyim."},

    {"k": ["frontend backend", "front end back end", "fullstack"],
     "a": "**Frontend** = kullanıcının gördüğü kısım (tarayıcıda çalışır)\n→ HTML, CSS, JavaScript, React, Vue\n\n**Backend** = sunucuda dönen kısım (veri, hesap, güvenlik)\n→ Python, Node.js, Java, Go + veritabanı\n\n**Full-stack** = ikisini de yapan geliştirici\n\nÖrnek: Instagram'da gördüğün arayüz frontend; fotoğrafın yüklenmesi, beğenilerin sayılması backend."},
]
