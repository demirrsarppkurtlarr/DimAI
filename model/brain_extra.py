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

    # --- Yoğun kod paketi (eğitim + sohbet kalitesi) ---
    {"k": ["kod yaz", "python kodu yaz", "write code", "bir kod yaz", "ornek kod"],
     "a": "İşte temiz, çalışır bir Python başlangıç paketi — fonksiyon + sınıf + ana blok:",
     "c": '''from __future__ import annotations

def merhaba(isim: str = "Dünya") -> str:
    mesaj = f"Merhaba, {isim}!"
    print(mesaj)
    return mesaj

def kareler(n: int) -> list[int]:
    return [i * i for i in range(1, n + 1)]

class Sayac:
    def __init__(self) -> None:
        self.n = 0
    def artir(self) -> int:
        self.n += 1
        return self.n

if __name__ == "__main__":
    merhaba("DimAI")
    print(kareler(5))
    s = Sayac()
    print(s.artir(), s.artir())''', "l": "python"},

    {"k": ["todo app", "yapilacaklar listesi", "todo listesi", "gorev listesi yaz"],
     "a": "Basit terminal TODO uygulaması:",
     "c": '''tasks: list[str] = []

while True:
    print("\\n1) Ekle  2) Listele  3) Sil  4) Çık")
    secim = input("> ").strip()
    if secim == "1":
        tasks.append(input("Görev: ").strip())
    elif secim == "2":
        for i, t in enumerate(tasks, 1):
            print(f"{i}. {t}")
    elif secim == "3":
        i = int(input("No: ")) - 1
        if 0 <= i < len(tasks):
            tasks.pop(i)
    elif secim == "4":
        break''', "l": "python"},

    {"k": ["hesap makinesi yaz", "calculator", "hesap makinesi kodu"],
     "a": "Basit hesap makinesi:",
     "c": '''def hesapla(a: float, op: str, b: float) -> float:
    if op == "+": return a + b
    if op == "-": return a - b
    if op == "*": return a * b
    if op == "/":
        if b == 0: raise ZeroDivisionError("sıfıra bölme")
        return a / b
    raise ValueError(f"bilinmeyen işlem: {op}")

if __name__ == "__main__":
    x = float(input("a: "))
    op = input("işlem (+ - * /): ").strip()
    y = float(input("b: "))
    print("sonuç:", hesapla(x, op, y))''', "l": "python"},

    {"k": ["http istek", "requests get", "api cagir", "json api"],
     "a": "`requests` ile JSON API çağrısı:",
     "c": '''import requests

def get_json(url: str) -> dict:
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.json()

data = get_json("https://httpbin.org/get")
print(data.get("url"))''', "l": "python"},

    {"k": ["decorator yaz", "dekorator", "decorator ornegi"],
     "a": "Decorator ile fonksiyonu sarmalama:",
     "c": '''import time
from functools import wraps

def sure_olc(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        t0 = time.time()
        sonuc = fn(*args, **kwargs)
        print(f"{fn.__name__}: {time.time() - t0:.4f}s")
        return sonuc
    return wrapper

@sure_olc
def yavas():
    time.sleep(0.2)
    return "ok"

print(yavas())''', "l": "python"},

    {"k": ["generator yaz", "yield", "generator ornegi"],
     "a": "Generator (`yield`) ile bellek dostu akış:",
     "c": '''def sayac(n: int):
    i = 0
    while i < n:
        yield i
        i += 1

def dosya_satirlari(path: str):
    with open(path, encoding="utf-8") as f:
        for line in f:
            yield line.rstrip("\\n")

for x in sayac(5):
    print(x)''', "l": "python"},

    {"k": ["regex yaz", "duzenli ifade", "re search", "regex ornegi"],
     "a": "Regex ile e-posta / sayı yakalama:",
     "c": '''import re

text = "Mail: demir@ornek.com, yaş 16, tel +90 555"
print(re.findall(r"[\\w.-]+@[\\w.-]+", text))
print(re.findall(r"\\d+", text))
m = re.search(r"yaş (\\d+)", text)
print(m.group(1) if m else None)''', "l": "python"},

    {"k": ["threading yaz", "coklu is parcacigi", "thread ornegi"],
     "a": "Basit threading örneği:",
     "c": '''import threading
import time

def isci(ad: str, n: int) -> None:
    for i in range(n):
        print(ad, i)
        time.sleep(0.1)

t1 = threading.Thread(target=isci, args=("A", 3))
t2 = threading.Thread(target=isci, args=("B", 3))
t1.start(); t2.start()
t1.join(); t2.join()
print("bitti")''', "l": "python"},

    {"k": ["oop yaz", "nesne yonelimli", "class ornegi gelismis"],
     "a": "OOP: kalıtım + encapsulation:",
     "c": '''class Canli:
    def __init__(self, isim: str):
        self.isim = isim
    def konus(self) -> str:
        return "..."

class Kopek(Canli):
    def konus(self) -> str:
        return f"{self.isim}: hav!"

class Kedi(Canli):
    def konus(self) -> str:
        return f"{self.isim}: miyav!"

for c in (Kopek("Karabaş"), Kedi("Pamuk")):
    print(c.konus())''', "l": "python"},

    {"k": ["sqlite yaz", "sqlite ornegi", "sqlite örneği", "sqlite", "veritabani kodu", "sql ornegi"],
     "a": "SQLite ile tablo oluştur / ekle / oku:",
     "c": '''import sqlite3

conn = sqlite3.connect("app.db")
cur = conn.cursor()
cur.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, name TEXT)")
cur.execute("INSERT INTO users (name) VALUES (?)", ("Demir",))
conn.commit()
for row in cur.execute("SELECT id, name FROM users"):
    print(row)
conn.close()''', "l": "python"},

    {"k": ["async await", "asyncio yaz", "asenkron python"],
     "a": "asyncio ile eşzamanlı işler:",
     "c": '''import asyncio

async def is_yap(ad: str, sn: float) -> str:
    await asyncio.sleep(sn)
    return f"{ad} bitti"

async def main():
    sonuclar = await asyncio.gather(
        is_yap("A", 0.3),
        is_yap("B", 0.2),
        is_yap("C", 0.1),
    )
    print(sonuclar)

asyncio.run(main())''', "l": "python"},

    {"k": ["react component yaz", "react yaz", "react ornegi", "jsx yaz", "component yaz"],
     "a": "Basit React fonksiyon bileşeni:",
     "c": '''import { useState } from "react";

export default function Counter() {
  const [n, setN] = useState(0);
  return (
    <div>
      <h1>Sayaç: {n}</h1>
      <button onClick={() => setN(n + 1)}>+1</button>
      <button onClick={() => setN(0)}>Sıfırla</button>
    </div>
  );
}''', "l": "javascript"},

    {"k": ["hello world yaz", "hello world", "merhaba dunya yaz", "write a hello world"],
     "a": "Klasik Hello World:",
     "c": '''print("Hello, World!")

# veya fonksiyonla:
def main() -> None:
    print("Hello, World!")

if __name__ == "__main__":
    main()''', "l": "python"},

    {"k": ["python kim buldu", "python kim yaratti", "guido", "python mucidi"],
     "a": "**Python**'u **Guido van Rossum** 1989–1991 yıllarında geliştirdi; ilk resmi sürüm 1991'de çıktı. İsmini Monty Python'dan alır. Guido uzun süre “Benevolent Dictator For Life” (BDFL) unvanıyla dilin yönünü belirledi."},

    {"k": ["docker compose yaz", "docker-compose", "dockerfile yaz", "docker yaz"],
     "a": "Basit Dockerfile + Compose:",
     "c": '''# Dockerfile
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
CMD ["python", "server.py"]

# docker-compose.yml
services:
  web:
    build: .
    ports:
      - "5055:5055"
    environment:
      - PORT=5055''', "l": "yaml"},

    {"k": ["typescript interface yaz", "typescript yaz", "ts interface", "interface yaz"],
     "a": "TypeScript interface örneği:",
     "c": '''interface User {
  id: number;
  name: string;
  email?: string;
  active: boolean;
}

function greet(user: User): string {
  return `Merhaba, ${user.name}`;
}

const u: User = { id: 1, name: "Demir", active: true };
console.log(greet(u));''', "l": "typescript"},

    {"k": ["api key sakla", "secret sakla", "env dosya", ".env yaz", "api anahtari"],
     "a": "API anahtarını koda gömme — ortam değişkeni kullan:",
     "c": '''# .env  (git'e EKLEME)
API_KEY=sk-ornek-anahtar

# Python
import os
from dotenv import load_dotenv  # pip install python-dotenv

load_dotenv()
api_key = os.environ["API_KEY"]

# asla: api_key = "sk-..."  ❌''', "l": "python"},

    {"k": ["http nedir", "http ne demek", "https nedir"],
     "a": "**HTTP**, tarayıcı ile sunucunun konuştuğu protokoldür.\n\n• **İstek (request):** GET (oku), POST (gönder), PUT/PATCH (güncelle), DELETE\n• **Yanıt (response):** durum kodu — 200 OK, 404 Not Found, 500 Server Error\n• **HTTPS** = HTTP + şifreleme (TLS)\n\nÖrnek: tarayıcı `GET /api/status` der, sunucu JSON döner. Kod örneği için \"requests get\" yaz."},

    {"k": ["python vs javascript", "python mi js mi", "python mi javascript mi", "python vs java", "hangisi daha iyi python"],
     "a": "**Kısa cevap:** yeni başlayan / AI / veri → **Python**. Web arayüzü / tarayıcı → **JavaScript**.\n\n| | Python | JavaScript |\n|---|---|---|\n| Nerede | Sunucu, script, AI | Tarayıcı + Node.js |\n| Sözdizimi | Sade | Esnek, her yerde |\n| Tipik iş | ML, otomasyon, API | Frontend, realtime |\n\nİkisini de öğrenmek yaygın; önce hedefine yakın olanı seç."},

    {"k": ["rest api yaz", "flask api yaz", "mini api"],
     "a": "Flask ile mini REST API:",
     "c": '''from flask import Flask, jsonify, request

app = Flask(__name__)
items = []

@app.get("/items")
def list_items():
    return jsonify(items)

@app.post("/items")
def add_item():
    data = request.get_json(force=True) or {}
    items.append(data)
    return jsonify(data), 201

if __name__ == "__main__":
    app.run(port=5000)''', "l": "python"},

    {"k": ["unit test yaz", "pytest yaz", "test kodu yaz"],
     "a": "pytest ile birim test:",
     "c": '''def topla(a, b):
    return a + b

def test_topla():
    assert topla(2, 3) == 5
    assert topla(-1, 1) == 0

# çalıştır: pytest -q''', "l": "python"},

    {"k": ["cli yaz", "komut satiri uygulama", "argparse yaz"],
     "a": "argparse ile CLI:",
     "c": '''import argparse

parser = argparse.ArgumentParser(description="Dosya araçları")
parser.add_argument("path", help="dosya yolu")
parser.add_argument("-n", "--lines", type=int, default=10)
args = parser.parse_args()

with open(args.path, encoding="utf-8") as f:
    for i, line in enumerate(f):
        if i >= args.lines:
            break
        print(line, end="")''', "l": "python"},

    {"k": ["json oku yaz", "json dosya", "json dump load"],
     "a": "JSON dosyası okuma / yazma:",
     "c": '''import json

data = {"isim": "Demir", "diller": ["Python", "JS"]}
with open("data.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

with open("data.json", "r", encoding="utf-8") as f:
    loaded = json.load(f)
print(loaded["isim"])''', "l": "python"},

    # --- Tanımlar: "X nedir" → açıklama (kod değil) ---
    {"k": ["dimai nedir", "dim ai nedir", "dimai ne"],
     "a": "**DimAI**, dış ücretli AI API'si kullanmayan, kendi kendini eğiten bir kod asistanıdır.\n\n• **Bilgi tabanı (KB)** — hazır kod ve kavram açıklamaları\n• **Öğrenilmiş hafıza** — web'den bulup kaydettiği bilgiler\n• **Beceriler** — matematik, birim, saat, çeviri\n• **Küçük nöral model** — karakter seviyesinde deneysel üretim\n\nKod, hesap veya bilgi sor — hepsine bakabilirim."},

    {"k": ["react nedir", "react ne demek", "react js nedir"],
     "a": "**React**, Meta (Facebook) tarafından geliştirilen, kullanıcı arayüzü yazmak için kullanılan bir **JavaScript kütüphanesidir**.\n\n• **Bileşen (component)** tabanlı: UI parçalara bölünür\n• **State / props** ile veri yönetimi\n• **Virtual DOM** ile verimli güncelleme\n• Genelde **JSX** sözdizimi kullanılır\n\nTek sayfa uygulamaları (SPA), dashboard ve mobil (React Native) için yaygındır. Örnek için `react component yaz` de."},

    {"k": ["react hook nedir", "hooks nedir", "react hooks nedir", "hook nedir react"],
     "a": "**React Hook**, fonksiyon bileşenlerinde state ve yan etki kullanmanı sağlayan özel fonksiyonlardır.\n\nSık kullanılanlar:\n• `useState` — durum tutar\n• `useEffect` — yan etki (fetch, abonelik)\n• `useRef` — DOM / mutable ref\n• `useMemo` / `useCallback` — hesap / fonksiyon önbelleği\n\nClass bileşenlerindeki lifecycle'ın modern karşılığıdır. Kod için `react component yaz` de."},

    {"k": ["useeffect nedir", "useeffect ne ise yarar", "use effect nedir"],
     "a": "**useEffect**, React'te bileşen çizildikten sonra yan etki çalıştırmak için kullanılan hook'tur.\n\nTipik işler: API çağrısı, event listener, timer, dış sistem senkronu.\n\n```js\nuseEffect(() => {\n  // mount / bağımlılık değişince\n  return () => { /* cleanup */ };\n}, [deps]);\n```\n\nBağımlılık dizisi `[]` ise yalnızca ilk mount'ta çalışır."},

    {"k": ["async await nedir", "async nedir", "await nedir", "asenkron nedir"],
     "a": "**async/await**, asenkron (beklemeden devam eden) kodu senkron gibi yazmanı sağlayan sözdizimidir.\n\n• `async function` her zaman bir **Promise** döner\n• `await` Promise sonucunu bekler, UI/thread'i kilitlemeden\n• JS, Python (`asyncio`), C# ve benzeri dillerde vardır\n\nPython örneği için `asyncio yaz` de."},

    {"k": ["pandas nedir", "pandas ne demek", "pandas kutuphanesi"],
     "a": "**pandas**, Python'da tablo verisi (CSV, Excel, SQL sonuçları) işlemek için kullanılan kütüphanedir.\n\n• Ana yapı: **DataFrame** (satır × sütun)\n• Filtreleme, gruplama, birleştirme, eksik veri temizliği\n• Veri bilimi ve analiz işlerinin standardı\n\nKurulum: `pip install pandas`. Kod için `pandas` diye sor."},

    {"k": ["tailwind nedir", "tailwind css nedir", "tailwindcss nedir"],
     "a": "**Tailwind CSS**, hazır utility class'larla arayüz stillendirmeni sağlayan bir CSS framework'üdür.\n\nÖrnek: `class=\"flex items-center gap-2 p-4 bg-slate-900 text-white\"`\n\n• Ayrı CSS dosyası yazmayı azaltır\n• Tasarım sistemi (renk, spacing) tutarlı kalır\n• JIT derleyici ile kullanılan class'lar üretilir\n\nKlasik CSS örneği için `css ortala` de."},

    {"k": ["jwt nedir", "json web token nedir", "jwt ne demek"],
     "a": "**JWT (JSON Web Token)**, kimlik doğrulama bilgisini imzalı bir string olarak taşıyan formattır.\n\nYapı: `header.payload.signature` (Base64).\n\n• Sunucu login sonrası token verir\n• İstemci her istekte `Authorization: Bearer …` gönderir\n• Sunucu imzayı doğrular — oturum için sık kullanılır\n\nGizli anahtarı asla frontend'e koyma."},

    {"k": ["graphql nedir", "graph ql nedir"],
     "a": "**GraphQL**, API'lerden tam olarak ihtiyaç duyduğun alanları sorgulamanı sağlayan bir sorgu dilidir (Facebook kökenli).\n\n• Tek endpoint (genelde `/graphql`)\n• Over-fetching / under-fetching azalır\n• REST'e alternatif; şema + tipler zorunlu\n\nÖrnek: `{ user(id: 1) { name email } }`"},

    {"k": ["redis nedir", "redis ne demek"],
     "a": "**Redis**, bellekte çalışan hızlı bir **anahtar-değer** veri deposudur (çoğunlukla cache / kuyruk / oturum).\n\n• Çok düşük gecikme\n• String, hash, list, set, sorted set yapıları\n• TTL ile otomatik silme\n\nTipik kullanım: API cache, rate limit, session store."},

    {"k": ["kubernetes nedir", "k8s nedir", "kubernetes ne demek"],
     "a": "**Kubernetes (K8s)**, konteynerleri (Docker vb.) otomatik dağıtıp ölçekleyen bir orkestrasyon sistemidir.\n\n• Pod / Deployment / Service kavramları\n• Sağlık kontrolü, yeniden başlatma, yatay ölçekleme\n• Bulut ve on-prem ortamların standardı\n\nDocker tek makine; Kubernetes filo yönetimidir."},

    {"k": ["nginx nedir", "nginx ne demek"],
     "a": "**Nginx**, yüksek performanslı web sunucusu ve reverse proxy'dir.\n\n• Statik dosya sunma\n• Load balancing\n• TLS sonlandırma (HTTPS)\n• API gateway / rate limit önü\n\nÇoğu production kurulumunda uygulama sunucusunun önünde durur."},

    {"k": ["ci cd nedir", "cicd nedir", "ci/cd nedir", "continuous integration"],
     "a": "**CI/CD** = Continuous Integration / Continuous Delivery (veya Deployment).\n\n• **CI:** her commit'te otomatik test / build\n• **CD:** onaylı sürümü otomatik staging/production'a alma\n\nAraçlar: GitHub Actions, GitLab CI, Jenkins, CircleCI.\nAmaç: elle deploy hatalarını ve \"bende çalışıyor\" sorununu azaltmak."},

    {"k": ["prometheus nedir", "prometheus monitoring"],
     "a": "**Prometheus** (yazılım), sistem ve uygulama metriklerini toplayan açık kaynaklı bir **izleme (monitoring)** sistemidir.\n\n• Zaman serisi veritabanı\n• Pull modeli ile hedef scrapeleri\n• PromQL sorgu dili\n• Sıkça Grafana ile görselleştirilir\n\nNot: Yunan mitolojisindeki Prometheus ile karıştırma — DevOps'ta monitoring kastedilir."},

    {"k": ["prisma nedir", "prisma orm nedir"],
     "a": "**Prisma**, TypeScript/Node ekosisteminde popüler bir **ORM**'dir.\n\n• `schema.prisma` ile veri modeli\n• Tip güvenli client üretir\n• PostgreSQL, MySQL, SQLite, MongoDB desteği\n\nSQL yazmadan güvenli sorgular için kullanılır."},

    {"k": ["zod nedir", "zod validation"],
     "a": "**Zod**, TypeScript için runtime şema doğrulama kütüphanesidir.\n\n• API body / form verisini doğrular\n• Şemadan TypeScript tipi çıkarır (`z.infer`)\n• `safeParse` ile hata mesajı üretir\n\nÖrnek: `z.object({ email: z.string().email() })`"},

    {"k": ["nextjs nedir", "next.js nedir", "next js nedir"],
     "a": "**Next.js**, React üzerine kurulu bir full-stack framework'tür (Vercel).\n\n• App Router / sayfa yönlendirme\n• SSR, SSG, ISR, Server Components\n• API route'ları\n• Production'a hazır React uygulamaları için yaygın seçim"},

    {"k": ["closure nedir", "closures nedir", "kapama nedir programlama"],
     "a": "**Closure (kapama)**, bir fonksiyonun tanımlandığı kapsamın değişkenlerini sonradan da hatırlamasıdır.\n\n```js\nfunction sayac() {\n  let n = 0;\n  return () => ++n;\n}\nconst artir = sayac();\nartir(); // 1\n```\n\nJS, Python ve birçok dilde callback / factory kalıplarının temelidir."},

    {"k": ["python decorator nedir", "decorator nedir", "dekorator nedir"],
     "a": "**Decorator (dekoratör)**, mevcut bir fonksiyonu sarmalayıp davranış ekleyen Python kalıbıdır (`@decorator`).\n\n```python\ndef logla(fn):\n    def sari(*a, **k):\n        print(\"çağrıldı\", fn.__name__)\n        return fn(*a, **k)\n    return sari\n\n@logla\ndef topla(x, y): return x + y\n```\n\nLogging, yetki kontrolü, cache için sık kullanılır. Kod için `decorator yaz` de."},

    {"k": ["sql join nedir", "join nedir sql", "inner join nedir"],
     "a": "**SQL JOIN**, iki (veya daha fazla) tabloyu ortak sütuna göre birleştirir.\n\n• **INNER JOIN** — her iki tarafta eşleşenler\n• **LEFT JOIN** — soldakilerin hepsi + sağda eşleşenler\n• **RIGHT / FULL** — benzer mantık diğer yönlerde\n\nÖrnek: siparişleri kullanıcı adlarıyla listelemek."},

    {"k": ["nosql nedir", "no sql nedir", "nosql ne demek"],
     "a": "**NoSQL**, klasik ilişkisel (tablo + SQL) modele sıkı bağlı olmayan veritabanı ailesidir.\n\nTürler:\n• Belge: MongoDB\n• Anahtar-değer: Redis\n• Sütun: Cassandra\n• Graf: Neo4j\n\nEsnek şema ve yatay ölçek için tercih edilir; karmaşık join'ler zayıftır."},

    {"k": ["mongodb nedir", "mongo db nedir"],
     "a": "**MongoDB**, JSON benzeri **BSON belgeler** saklayan popüler bir NoSQL veritabanıdır.\n\n• Koleksiyon = tablo benzeri\n• Belge = satır (esnek alanlar)\n• Yatay ölçek (sharding) güçlü\n• Node/Python ekosisteminde çok kullanılır"},

    {"k": ["git rebase nedir", "rebase nedir", "git rebase ne"],
     "a": "**git rebase**, commit geçmişini başka bir taban üzerine yeniden uygular; geçmişi doğrusal tutmak için kullanılır.\n\n• `merge` → birleştirme commit'i ekler\n• `rebase` → commit'leri kaydırır (geçmişi yeniden yazar)\n\nPaylaşılan branch'te force-push riskli olabilir; feature branch'lerde sıkça tercih edilir."},

    {"k": ["docker compose nedir", "docker-compose nedir", "compose nedir docker"],
     "a": "**Docker Compose**, birden fazla konteyneri tek `docker-compose.yml` ile tanımlayıp birlikte çalıştırma aracıdır.\n\nÖrn: web + postgres + redis aynı anda `docker compose up`.\n\nTek konteyner için Dockerfile; çok servisli geliştirme ortamı için Compose."},

    {"k": ["websocket nedir", "web socket nedir", "websockets nedir"],
     "a": "**WebSocket**, tek TCP bağlantısı üzerinden **çift yönlü** (sunucu↔istemci) gerçek zamanlı iletişim protokolüdür.\n\n• Chat, canlı skor, işbirliği editörleri\n• HTTP'den upgrade ile başlar\n• REST'e göre sürekli açık kanal\n\nAlternatif: SSE (sunucu→istemci tek yön)."},

    {"k": ["oauth nedir", "oauth2 nedir"],
     "a": "**OAuth 2.0**, \"Google/GitHub ile giriş\" gibi **yetkilendirme** protokolüdür.\n\n• Kullanıcı şifresini 3. parti uygulamaya vermez\n• Access token ile sınırlı izin verir\n• OpenID Connect kimlik katmanı ekler\n\nSık akış: Authorization Code (+ PKCE)."},

    {"k": ["cors nedir", "cors ne demek", "cross origin"],
     "a": "**CORS (Cross-Origin Resource Sharing)**, tarayıcının farklı origin'lerden (domain/port) API çağrısını kontrol eden güvenlik mekanizmasıdır.\n\n• `Access-Control-Allow-Origin` header'ı kritik\n• Preflight (`OPTIONS`) karmaşık isteklerde gelir\n• Backend'de doğru CORS ayarı yoksa frontend \"blocked by CORS\" görür\n\nNot: GNSS/CORS ağlarıyla karıştırma — web'de bu kastedilir."},

    {"k": ["dns nedir", "dns ne demek", "domain name system"],
     "a": "**DNS (Domain Name System)**, alan adlarını IP adreslerine çeviren internet \"rehberidir\".\n\n`example.com` → `93.184.216.34`\n\nKayıt türleri: A, AAAA, CNAME, MX, TXT.\nTarayıcı her sitede önce DNS sorar."},

    {"k": ["tcp vs udp", "tcp udp fark", "tcp nedir", "udp nedir"],
     "a": "**TCP** vs **UDP**:\n\n• **TCP:** güvenilir, sıralı, bağlantılı (web, email, SSH)\n• **UDP:** hızlı, bağlantısız, paket kaybı olabilir (oyun, video, DNS)\n\nTCP \"teslimat garantisi\" ister; UDP \"hız\" ister."},

    {"k": ["rest api nedir", "rest nedir api", "restful nedir"],
     "a": "**REST API**, kaynakları URL + HTTP metodlarıyla yöneten yaygın API tarzıdır.\n\n• `GET` oku · `POST` oluştur · `PUT/PATCH` güncelle · `DELETE` sil\n• Genelde JSON döner\n• Stateles: her istekte kimlik/token gerekir\n\n\"API nedir\" daha genel; REST onun en popüler uygulamasıdır."},

    {"k": ["typescript interface vs type", "interface vs type", "type vs interface"],
     "a": "**TypeScript `interface` vs `type`:**\n\n• İkisi de şekil/tip tanımlar\n• `interface` birleştirilebilir (declaration merging)\n• `type` birleşim (`A | B`), tuple, mapped type için daha esnek\n• Nesne şekilleri için çoğu ekip `interface` tercih eder\n\nPratikte ikisi de çalışır; tutarlı ol."},

    {"k": ["turkiye baskenti", "turkiyenin baskenti", "ankara baskent"],
     "a": "**Türkiye'nin başkenti Ankara'dır.** 13 Ekim 1923'te başkent ilan edildi. En kalabalık şehir ise İstanbul'dur."},

    # --- Round 2 tanımlar / karşılaştırmalar ---
    {"k": ["vue nedir", "vuejs nedir", "vue.js nedir"],
     "a": "**Vue.js**, kullanıcı arayüzü için progressive bir JavaScript framework'üdür.\n\n• Öğrenmesi React/Angular'a göre daha yumuşak\n• Tek dosya bileşenleri (`.vue`)\n• Reactivity sistemi + Composition API\n\nKüçük widget'tan büyük SPA'ya kadar ölçeklenir."},

    {"k": ["svelte nedir", "sveltejs nedir"],
     "a": "**Svelte**, derleme zamanında JavaScript'e dönüşen bir UI framework'üdür.\n\n• Runtime'da Virtual DOM taşımaz\n• Daha az boilerplate\n• `.svelte` dosyalarında HTML/CSS/JS bir arada\n\nPerformans ve sadelik odaklı alternatif."},

    {"k": ["angular nedir", "angularjs nedir"],
     "a": "**Angular**, Google destekli, TypeScript tabanlı full-featured bir frontend framework'tür.\n\n• CLI, routing, forms, DI hazır gelir\n• Büyük kurumsal uygulamalar için tercih edilir\n• React/Vue'ye göre daha \"batteries included\""},

    {"k": ["flutter nedir", "flutter dart"],
     "a": "**Flutter**, Google'ın **Dart** diliyle mobil/web/masaüstü UI yazdıran toolkit'idir.\n\n• Tek kod tabanı → iOS + Android (+ web/desktop)\n• Widget ağacı\n• Hot reload ile hızlı geliştirme"},

    {"k": ["postgresql nedir", "postgres nedir"],
     "a": "**PostgreSQL (Postgres)**, gelişmiş açık kaynaklı ilişkisel veritabanıdır.\n\n• Güçlü SQL desteği, JSONB, full-text search\n• ACID, güvenilirlik\n• Web backend'lerin en sık tercih ettiği DB'lerden"},

    {"k": ["mysql nedir", "my sql nedir"],
     "a": "**MySQL**, yaygın kullanılan açık kaynaklı ilişkisel veritabanıdır.\n\n• LAMP yığınının klasik parçası\n• Okuma ağırlıklı web uygulamalarında sık\n• MariaDB onun topluluk çatallaması"},

    {"k": ["elasticsearch nedir", "elastic search nedir"],
     "a": "**Elasticsearch**, JSON belgeleri üzerinde hızlı **full-text arama** yapan dağıtık arama motorudur.\n\n• ELK/Elastic Stack'in kalbi\n• Log, ürün arama, analitik\n• REST API ile konuşur"},

    {"k": ["kafka nedir", "apache kafka nedir"],
     "a": "**Apache Kafka**, yüksek hacimli olay/mesaj akışı için dağıtık bir **event streaming** platformudur.\n\n• Producer → topic → consumer\n• Log tabanlı, ölçeklenebilir\n• Mikroservisler arası event bus olarak sık kullanılır"},

    {"k": ["rabbitmq nedir", "rabbit mq nedir"],
     "a": "**RabbitMQ**, AMQP tabanlı bir **mesaj kuyruğu**dır.\n\n• İşleri asenkron dağıtır\n• Exchange + queue modeli\n• Kafka'dan daha klasik queue; daha düşük gecikmeli iş kuyrukları için uygun"},

    {"k": ["grpc nedir", "g rpc nedir"],
     "a": "**gRPC**, Google'ın HTTP/2 + Protocol Buffers kullanan RPC framework'üdür.\n\n• Hızlı, tip güvenli servis çağrıları\n• Mikroservisler arası iletişimde yaygın\n• REST/JSON'a göre daha kompakt"},

    {"k": ["microservices nedir", "mikroservis nedir", "microservice nedir"],
     "a": "**Mikroservis**, büyük uygulamayı bağımsız deploy edilebilen küçük servislere bölme mimarisidir.\n\n• Her servis kendi DB/API'sine sahip olabilir\n• Ölçekleme ve ekip özerkliği artar\n• Bedeli: ağ karmaşıklığı, gözlemlenebilirlik ihtiyacı"},

    {"k": ["serverless nedir", "server less nedir"],
     "a": "**Serverless**, sunucu yönetmeden olay tetiklemeli fonksiyon çalıştırma modelidir (AWS Lambda, Cloud Functions).\n\n• Kullandığın kadar öde\n• Otomatik ölçek\n• Soğuk başlangıç ve vendor lock-in dikkat"},

    {"k": ["cdn nedir", "content delivery network"],
     "a": "**CDN (Content Delivery Network)**, statik içeriği kullanıcıya yakın sunuculardan dağıtan ağdır.\n\n• Daha hızlı yükleme, daha az origin yükü\n• Cloudflare, Fastly, CloudFront örnekleri\n• JS/CSS/görseller için standart"},

    {"k": ["jwt vs session", "session vs jwt", "jwt session fark"],
     "a": "**JWT vs Session:**\n\n• **Session:** sunucu state tutar (cookie + server store)\n• **JWT:** istemci token taşır, sunucu genelde stateless doğrular\n\nJWT ölçeklemede kolay; iptal/refresh ve sızıntı riski yönetilmeli. Session kontrolü sunucuda daha kolay."},

    {"k": ["rest vs graphql", "graphql vs rest", "rest graphql fark"],
     "a": "**REST vs GraphQL:**\n\n• **REST:** kaynak URL'leri + HTTP metodları, birden fazla endpoint\n• **GraphQL:** tek endpoint, istemci alan seçer\n\nGraphQL over-fetch azaltır; cache ve karmaşıklık maliyeti vardır. Basit CRUD için REST hâlâ çok uygun."},

    {"k": ["sql vs nosql", "nosql vs sql", "sql nosql fark"],
     "a": "**SQL vs NoSQL:**\n\n• **SQL:** tablolar, şema, join, güçlü tutarlılık (Postgres/MySQL)\n• **NoSQL:** esnek belge/key-value, yatay ölçek (Mongo/Redis)\n\nİlişkili veri + rapor → SQL. Esnek belge + yüksek yazma → NoSQL. Çoğu sistem ikisini birden kullanır."},

    {"k": ["big o nedir", "big-o nedir", "buyuk o nedir", "time complexity nedir"],
     "a": "**Big-O**, algoritmanın girdi büyüdükçe nasıl yavaşladığını (asimptotik karmaşıklık) anlatır.\n\n• O(1) sabit · O(log n) iyi · O(n) doğrusal\n• O(n log n) iyi sıralama · O(n²) Nested döngü · O(2ⁿ) patlama\n\n\"Algoritma nedir\" ile birlikte düşün; örnek için `binary search yaz`."},

    {"k": ["heap nedir programlama", "heap nedir", "stack nedir programlama", "stack nedir bellek"],
     "a": "**Stack vs Heap (bellek):**\n\n• **Stack:** fonksiyon çağrıları, lokal değişkenler — hızlı, otomatik temizlenir\n• **Heap:** dinamik tahsis (`new`/objeler) — esnek, GC/manuel yönetim\n\nAyrıca **heap** veri yapısı (öncelik kuyruğu) ayrı bir kavramdır."},

    {"k": ["garbage collector nedir", "gc nedir", "cop toplayici nedir"],
     "a": "**Garbage Collector (GC)**, artık referansı kalmayan nesneleri otomatik temizleyen bellek yöneticisidir.\n\n• Java, Go, C#, JS, Python'da var\n• C/C++'ta genelde manuel (`free`)\n• Pause / throughput trade-off'ları vardır"},

    {"k": ["npm nedir", "node package manager"],
     "a": "**npm**, Node.js paket yöneticisidir.\n\n• `package.json` bağımlılıkları\n• `npm install` / `npx`\n• npm registry'den kütüphane indirir\n\nAlternatifler: yarn, pnpm."},

    {"k": ["pip nedir", "pip python"],
     "a": "**pip**, Python paket yükleyicisidir.\n\n• `pip install requests`\n• PyPI deposundan paket çeker\n• Sanal ortam (`venv`) ile birlikte kullan"},

    {"k": ["virtualenv nedir", "venv nedir", "python venv"],
     "a": "**venv / virtualenv**, projeye özel izole Python ortamıdır.\n\n• Bağımlılıklar sistem Pyhton'unu kirletmez\n• `python -m venv .venv` → aktive et → `pip install`"},

    {"k": ["linux nedir"],
     "a": "**Linux**, açık kaynaklı bir işletim sistemi çekirdeğidir; Ubuntu/Debian/Fedora gibi dağıtımların temelidir.\n\n• Sunucuların ve Android'in omurgası\n• Çok kullanıcılı, güçlü terminal/araç ekosistemi"},

    {"k": ["bash nedir", "bash shell"],
     "a": "**Bash**, Linux/macOS'ta yaygın bir komut satırı kabuğudur (shell).\n\n• Komut çalıştırma + script (`.sh`)\n• Pipe, yönlendirme, değişkenler\n• Otomasyonun temel aracı"},

    {"k": ["cron nedir", "crontab nedir"],
     "a": "**cron**, Unix/Linux'ta zamanlanmış görev çalıştırıcıdır.\n\n• `crontab -e` ile planlanır\n• Örn: her gece yedek al, her 5 dk health-check\n• Format: `dakika saat gün ay haftanın_günü komut`"},

    {"k": ["ssl nedir", "tls nedir", "ssl tls nedir"],
     "a": "**TLS** (eski adıyla sıkça **SSL** denir), ağ trafiğini şifreleyen protokoldür.\n\n• HTTPS = HTTP + TLS\n• Sertifika (CA) ile kimlik doğrulama\n• Bugün SSL 3.0 ölü; pratikte TLS 1.2/1.3 kullanılır"},

    {"k": ["regex nedir", "regular expression nedir", "duzenli ifade"],
     "a": "**Regex (regular expression)**, metinde kalıp aramak için mini bir dildir.\n\n• `\\d+` rakamlar · `^` baş · `$` son · `.*` herhangi\n• Validasyon, parse, arama-değiştirmede kullanılır\n\nÖrnek için `regex örneği` de."},

    {"k": ["hash nedir", "hashing nedir", "hash fonksiyonu"],
     "a": "**Hash**, veriyi sabit uzunlukta özet değere çeviren fonksiyondur.\n\n• Aynı girdi → aynı özet\n• Küçük değişiklik → tamamen farklı özet\n• Şifre saklama (salt + bcrypt/argon2), bütünlük, dict/key\n\nŞifreleri düz hash'leme (MD5) yeterli değildir."},

    {"k": ["karadelik nedir", "kara delik nedir", "black hole nedir"],
     "a": "**Karadelik**, kütleçekimi ışığın bile kaçamayacağı kadar güçlü olan uzay-zaman bölgesidir.\n\n• Olay ufku: dönüşü olmayan sınır\n• Yıldız çökmesi veya galaksi merkezlerinde oluşur\n• Einstein göreliliği + modern astronomi ile incelenir"},

    {"k": ["ataturk kimdir", "mustafa kemal", "mustafa kemal ataturk"],
     "a": "**Mustafa Kemal Atatürk** (1881–1938), Türkiye Cumhuriyeti'nin kurucusu ve ilk cumhurbaşkanıdır.\n\n• Kurtuluş Savaşı'nın askeri/siyasi lideri\n• Cumhuriyet, laiklik, harf inkılabı gibi reformlar\n• 10 Kasım 1938'de İstanbul'da vefat etti"},

    {"k": ["rust nedir", "rust dili", "rust programming"],
     "a": "**Rust**, bellek güvenliğini derleme zamanında öne çıkaran modern bir sistem programlama dilidir.\n\n• Ownership / borrowing modeli\n• Null ve data-race hatalarını azaltır\n• Sistem, CLI, WebAssembly, performans kritik servisler"},

    {"k": ["go nedir", "golang nedir", "go dili nedir"],
     "a": "**Go (Golang)**, Google'ın geliştirdiği sade ve hızlı bir programlama dilidir.\n\n• Goroutine ile kolay eşzamanlılık\n• Statik tip, hızlı derleme\n• Bulut / mikroservis / CLI araçlarında çok yaygın\n\nNot: Japon Go tahta oyunuyla karıştırma."},

    {"k": ["kotlin nedir", "kotlin dili"],
     "a": "**Kotlin**, JVM üzerinde çalışan, Android'in resmi dili olan modern bir programlama dilidir.\n\n• Java ile uyumlu\n• Null-safety\n• Kısa sözdizimi\n• Backend (Ktor/Spring) ve multiplatform da kullanılır"},

    {"k": ["swift nedir", "swift dili", "swift programming"],
     "a": "**Swift**, Apple'ın iOS/macOS uygulamaları için geliştirdiği programlama dilidir.\n\n• Safe, hızlı, modern sözdizimi\n• Objective-C'nin yerini alır\n• SwiftUI ile arayüz\n\nNot: Taylor Swift ile karıştırma — yazılımda dil kastedilir."},

    {"k": ["terraform nedir"],
     "a": "**Terraform**, altyapıyı kod olarak (IaC) tanımlayan bir HashiCorp aracıdır.\n\n• `.tf` dosyalarıyla bulut kaynakları\n• Plan → apply\n• AWS/GCP/Azure sağlayıcıları"},

    {"k": ["ansible nedir"],
     "a": "**Ansible**, ajan gerektirmeden sunucu yapılandırma / otomasyon aracıdır.\n\n• YAML playbook'lar\n• SSH ile çalışır\n• Kurulum, deploy, yapılandırma otomasyonu"},

    {"k": ["jenkins nedir", "jenkins ci"],
     "a": "**Jenkins**, açık kaynaklı bir **CI/CD** sunucusudur.\n\n• Pipeline ile otomatik build/test/deploy\n• Plugin ekosistemi geniş\n\nNot: ABD'deki Jenkins County ile karıştırma."},

    {"k": ["s3 nedir", "amazon s3 nedir", "aws s3"],
     "a": "**Amazon S3**, AWS'nin nesne depolama (object storage) servisidir.\n\n• Dosya/blob saklama, yüksek dayanıklılık\n• Bucket + key modeli\n• Statik site, yedek, medya için sık kullanılır"},

    {"k": ["lambda nedir", "aws lambda nedir", "lambda aws"],
     "a": "**AWS Lambda**, olay tetiklemeli **serverless** fonksiyon çalıştırma servisidir.\n\n• Sunucu yönetmezsin\n• İstek/olay başına ölçeklenir\n• S3, API Gateway, cron tetikleyicileriyle kullanılır"},

    {"k": ["docker nedir", "docker ne demek"],
     "a": "**Docker**, uygulamayı bağımlılıklarıyla birlikte **konteyner**de paketleyen teknolojidir.\n\n• Image → container\n• 'Bende çalışıyor' sorununu azaltır\n• Compose ile çok servisli ortam"},

    {"k": ["pointer nedir", "isaretci nedir", "pointer programming"],
     "a": "**Pointer (işaretçi)**, bellekteki bir adresı tutan değişkendir (C/C++/Rust'ta sık).\n\n• Doğrudan bellek erişimi\n• Hızlı ama dikkat: dangling pointer, buffer overflow\n\nNot: Anita Pointer ile karıştırma."},

    {"k": ["mutex nedir", "lock nedir programlama"],
     "a": "**Mutex (mutual exclusion)**, paylaşılan kaynağa aynı anda tek thread'in girmesini sağlayan kilit mekanizmasıdır.\n\n• Race condition önler\n• Yanlış kullanım deadlock yaratabilir"},

    {"k": ["deadlock nedir", "kilitlenme nedir"],
     "a": "**Deadlock (kilitlenme)**, iki veya daha fazla işlemin birbirini beklemesiyle hiçbiri ilerleyememesi durumudur.\n\n• Klasik: A kilidi B'yi, B kilidi A'yı bekler\n• Önlem: kilit sırası, timeout, deadlock detection"},

    {"k": ["solid nedir", "solid prensipleri"],
     "a": "**SOLID**, nesne yönelimli tasarım için 5 prensiptir:\n\n• **S**ingle Responsibility\n• **O**pen/Closed\n• **L**iskov Substitution\n• **I**nterface Segregation\n• **D**ependency Inversion\n\nDaha bakımı kolay kod için rehber."},

    {"k": ["dry nedir", "dont repeat yourself"],
     "a": "**DRY (Don't Repeat Yourself)**, bilginin tek bir yerde tanımlanması prensibidir.\n\n• Kopyala-yapıştır yerine fonksiyon/modül\n• Aşırı DRY da zararlı olabilir (yanlış soyutlama)\n\nNot: müzik parçası 'Dry County' ile karıştırma."},

    {"k": ["unit test nedir", "birim test nedir"],
     "a": "**Unit test (birim test)**, kodun en küçük parçasını (fonksiyon/sınıf) izole test etmektir.\n\n• Hızlı geri bildirim\n• Regresyonları yakalar\n• pytest / Jest / JUnit gibi araçlar"},

    {"k": ["tdd nedir", "test driven development"],
     "a": "**TDD (Test-Driven Development)**: önce test yaz → kırmızı, sonra kod → yeşil, sonra refactor.\n\n• Tasarımı netleştirir\n• Aşırıya kaçmadan kullanıldığında kalite artar"},

    {"k": ["agile nedir", "cevik nedir yazilim"],
     "a": "**Agile**, yazılımda kısa döngülerle, geri bildirime göre ilerleyen çevik geliştirme yaklaşımıdır.\n\n• Scrum, Kanban gibi çerçeveler\n• Çalışan yazılım + müşteri işbirliği öncelikli"},

    {"k": ["scrum nedir", "scrum agile"],
     "a": "**Scrum**, Agile'ın popüler bir çerçevesidir.\n\n• Sprint, Product Owner, Scrum Master, Daily\n• Backlog → Sprint → Review/Retro\n\nYazılım ekiplerinde iş planlama ritmi sağlar."},

    {"k": ["promise nedir", "promise js", "javascript promise"],
     "a": "**Promise**, JavaScript'te asenkron işlemin ileride tamamlanacağını temsil eden nesnedir.\n\n• pending → fulfilled / rejected\n• `.then` / `.catch` veya `async/await`\n\nNot: şarkı adı 'Promise' ile karıştırma."},

    {"k": ["callback nedir", "callback function"],
     "a": "**Callback**, başka bir fonksiyona argüman olarak verilen ve sonra çağrılan fonksiyondur.\n\n• Olaylar, async I/O, dizi metodları (`map`)\n• Aşırı iç içe callback → 'callback hell' → Promise/async"},

    {"k": ["mvc nedir", "model view controller"],
     "a": "**MVC (Model–View–Controller)**, uygulamayı üç kata ayıran mimari kalıptır.\n\n• Model: veri/iş kuralları\n• View: arayüz\n• Controller: istekleri yönlendirir\n\nWeb framework'lerinde klasik."},

    {"k": ["orm nedir", "object relational mapping"],
     "a": "**ORM (Object-Relational Mapping)**, nesneleri veritabanı tablolarına eşleyen katmandır.\n\n• Örn: Prisma, SQLAlchemy, Hibernate, Eloquent\n• SQL yazmayı azaltır; N+1 gibi tuzaklara dikkat"},

    {"k": ["cookie nedir", "http cookie", "cerez nedir"],
     "a": "**HTTP cookie**, tarayıcının sakladığı küçük veri parçasıdır.\n\n• Oturum, tercihler, izleme\n• `Set-Cookie` / `Cookie` header\n• HttpOnly, Secure, SameSite bayrakları önemli\n\nNot: film/şarkı isimleriyle karıştırma — web'de HTTP cookie."},

    {"k": ["localstorage nedir", "local storage nedir"],
     "a": "**localStorage**, tarayıcıda origin bazlı anahtar-değer saklama API'sidir.\n\n• ~5MB, kalıcı (sekme kapanınca silinmez)\n• Sadece string; hassas veri koyma\n• Alternatif: sessionStorage, IndexedDB"},

    {"k": ["blob nedir programlama", "blob nedir", "binary large object"],
     "a": "**BLOB (Binary Large Object)**, büyük ikili veri (dosya, görüntü, video) saklama kavramıdır.\n\n• DB'de blob sütunu veya object storage (S3)\n• JS'te `Blob` / `File` API\n\nNot: 'blob' yaratık görselleriyle karıştırma."},

    {"k": ["list comprehension nedir", "python list comprehension", "liste ureteci nedir"],
     "a": "**List comprehension**, Python'da listeyi tek satırda üretmenin kısa yoludur.\n\n```python\nkareler = [x*x for x in range(10) if x % 2 == 0]\n```\n\nOkunaklı filtre+map için ideal; aşırı karmaşıksa normal döngü yeğlenir."},

    {"k": ["generator nedir", "generator nedir python", "python generator"],
     "a": "**Generator**, Python'da `yield` ile tembel (lazy) değer üreten fonksiyondur.\n\n• Tüm listeyi belleğe almaz\n• Iterator protokolü\n• Büyük veri akışlarında bellek dostu"},

    {"k": ["rest api nasil tasarlanir", "rest tasarim", "api tasarimi"],
     "a": "**REST API tasarım ipuçları:**\n\n• Kaynak adları çoğul isim: `/users`, `/orders/5`\n• HTTP fiilleri doğru kullan (GET/POST/PUT/PATCH/DELETE)\n• Tutarlı JSON şeması + anlamlı status kodları\n• Versiyonlama (`/v1/...`), sayfalama, hata formatı\n• Kimlik: token/OAuth\n\nKod istersen `flask api yaz` de."},

]
