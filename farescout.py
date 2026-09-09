import requests
import time
import sys


# ---------------------------------
# SABİTLER
# ---------------------------------

API_KEY = "ignav_T9g-QLY7TZC1JTvOevNmrWDJr2F06fty"
IGNAV_URL = "https://ignav.com/api/fares/one-way"
KUR_URL = "https://api.exchangerate.dev/v1/latest/USD?symbols=TRY"

TIMEOUT = 10          # saniye - istek zaman aşımı
MAX_DENEME = 3        # başarısız istek için tekrar deneme sayısı
BEKLEME_SURESI = 2    # denemeler arası bekleme (saniye)

HAVALIMANLARI = {
    "istanbul": ["IST", "SAW"],
    "ankara": ["ESB"],
    "izmir": ["ADB"],
    "antalya": ["AYT"],
    "adana": ["COV"],
    "trabzon": ["TZX"],
    "ordu": ["OGU"],
    "samsun": ["SZF"],
    "bodrum": ["BJV"],
    "dalaman": ["DLM"],
    "gaziantep": ["GZT"],
    "kayseri": ["ASR"],
    "konya": ["KYA"],
    "diyarbakir": ["DIY"],
    "erzurum": ["ERZ"],
}


# ---------------------------------
# GENEL YARDIMCI: TEKRAR DENEMELİ İSTEK
# ---------------------------------

def istek_gonder(method, url, **kwargs):
    """
    Verilen HTTP isteğini timeout ile gönderir, ağ hatası/timeout durumunda
    MAX_DENEME kadar tekrar dener. Başarısız olursa None döner.
    """
    kwargs.setdefault("timeout", TIMEOUT)

    for deneme in range(1, MAX_DENEME + 1):
        try:
            response = requests.request(method, url, **kwargs)
            return response
        except requests.exceptions.Timeout:
            print(f"⏱️  Zaman aşımı ({deneme}/{MAX_DENEME}) - {url}")
        except requests.exceptions.ConnectionError:
            print(f"🔌 Bağlantı hatası ({deneme}/{MAX_DENEME}) - {url}")
        except requests.exceptions.RequestException as e:
            print(f"❌ İstek hatası ({deneme}/{MAX_DENEME}): {e}")

        if deneme < MAX_DENEME:
            time.sleep(BEKLEME_SURESI)

    return None


# ---------------------------------
# KULLANICI GİRİŞİ
# ---------------------------------

def kullanicidan_bilgi_al():
    kalkis = input("Kalkış şehri: ").strip().lower()
    varis = input("Varış şehri: ").strip().lower()
    tarih = input("Gidiş tarihi (YYYY-AA-GG): ").strip()

    while True:
        maks_fiyat_str = input("En fazla kaç TL ödemek istiyorsun? ").strip()
        try:
            maksimum_fiyat = float(maks_fiyat_str)
            if maksimum_fiyat <= 0:
                print("⚠️  Lütfen 0'dan büyük bir sayı gir.")
                continue
            break
        except ValueError:
            print("⚠️  Geçerli bir sayı gir (örnek: 3500).")

    return kalkis, varis, tarih, maksimum_fiyat


def sehir_dogrula(sehir, etiket):
    """Şehrin havalimanı listesinde olup olmadığını kontrol eder."""
    if sehir not in HAVALIMANLARI:
        print(f"❌ {etiket} şehri bulunamadı: '{sehir}'")
        print(f"   Desteklenen şehirler: {', '.join(sorted(HAVALIMANLARI))}")
        return None
    return HAVALIMANLARI[sehir]


def tarih_dogrula(tarih):
    """Basit YYYY-AA-GG format kontrolü."""
    parcalar = tarih.split("-")
    if len(parcalar) != 3 or not all(p.isdigit() for p in parcalar):
        print(f"❌ Geçersiz tarih formatı: '{tarih}' (beklenen: YYYY-AA-GG)")
        return False
    yil, ay, gun = parcalar
    if not (1 <= int(ay) <= 12 and 1 <= int(gun) <= 31):
        print(f"❌ Geçersiz tarih değeri: '{tarih}'")
        return False
    return True


# ---------------------------------
# DÖVİZ KURU
# ---------------------------------

def dolar_kuru_al():
    """USD/TRY kurunu getirir. Başarısız olursa None döner."""
    response = istek_gonder("GET", KUR_URL)

    if response is None:
        print("❌ Dolar kuru alınamadı (bağlantı sorunu).")
        return None

    if response.status_code != 200:
        print(f"❌ Dolar kuru alınamadı (HTTP {response.status_code}).")
        return None

    try:
        veri = response.json()
        kur = veri["rates"]["TRY"]
        return float(kur)
    except (ValueError, KeyError, TypeError):
        print("❌ Dolar kuru verisi beklenen formatta değil.")
        return None


# ---------------------------------
# UÇUŞ ARAMA
# ---------------------------------

def tek_rota_ucus_ara(kalkis_kodu, varis_kodu, tarih):
    """Tek bir kalkış-varış kombinasyonu için IGNAV API'den uçuşları çeker."""
    headers = {
        "X-Api-Key": API_KEY,
        "Content-Type": "application/json",
    }
    data = {
        "origin": kalkis_kodu,
        "destination": varis_kodu,
        "departure_date": tarih,
    }

    response = istek_gonder("POST", IGNAV_URL, headers=headers, json=data)

    if response is None:
        print(f"❌ {kalkis_kodu} → {varis_kodu}: bağlantı kurulamadı.")
        return []

    if response.status_code != 200:
        print(f"❌ {kalkis_kodu} → {varis_kodu}: arama başarısız (HTTP {response.status_code}).")
        return []

    try:
        veri = response.json()
    except ValueError:
        print(f"❌ {kalkis_kodu} → {varis_kodu}: yanıt JSON formatında değil.")
        return []

    itineraries = veri.get("itineraries")
    if not itineraries:
        # Uçuş bulunamamış olabilir, bu bir hata değil
        return []

    return itineraries


def ucuslari_isle(itineraries, dolar_kuru, maksimum_fiyat, kalkis_kodu, varis_kodu):
    """Ham itinerary listesini filtreleyip standart formata çevirir."""
    uygun_ucuslar = []

    for ucus in itineraries:
        try:
            fiyat_usd = ucus["price"]["amount"]
            fiyat_tl = float(fiyat_usd) * dolar_kuru

            if fiyat_tl > maksimum_fiyat:
                continue

            outbound = ucus["outbound"]
            segment = outbound["segments"][0]

            uygun_ucuslar.append({
                "havayolu": outbound.get("carrier", "Bilinmiyor"),
                "ucus_no": segment.get("flight_number", "?"),
                "kalkis": segment.get("departure_time_local", "?"),
                "varis": segment.get("arrival_time_local", "?"),
                "fiyat": fiyat_tl,
                "kalkis_havalimani": kalkis_kodu,
                "varis_havalimani": varis_kodu,
            })
        except (KeyError, IndexError, TypeError, ValueError):
            # Beklenmeyen/eksik veri yapısına sahip tek bir uçuşu atla,
            # tüm aramayı çökertme
            print("⚠️  Beklenmeyen formatta bir uçuş kaydı atlandı.")
            continue

    return uygun_ucuslar


def tum_rotalarda_ara(kalkis_havalimanlari, varis_havalimanlari, tarih, dolar_kuru, maksimum_fiyat):
    """Tüm kalkış x varış kombinasyonlarını gezip uygun uçuşları toplar."""
    tum_ucuslar = []

    for kalkis_kodu in kalkis_havalimanlari:
        for varis_kodu in varis_havalimanlari:
            print(f"🔍 Aranıyor: {kalkis_kodu} → {varis_kodu} ...")
            itineraries = tek_rota_ucus_ara(kalkis_kodu, varis_kodu, tarih)
            uygun = ucuslari_isle(itineraries, dolar_kuru, maksimum_fiyat, kalkis_kodu, varis_kodu)
            tum_ucuslar.extend(uygun)

    return tum_ucuslar


# ---------------------------------
# SONUÇ GÖSTERİMİ
# ---------------------------------

def sonuclari_yazdir(uygun_ucuslar):
    print()
    print("=" * 50)
    print("✈️  UYGUN UÇUŞLAR")
    print("=" * 50)

    if not uygun_ucuslar:
        print("❌ Belirttiğin fiyatın altında uçuş bulunamadı.")
        return

    for ucus in uygun_ucuslar:
        print()
        print("Havayolu:", ucus["havayolu"])
        print("Uçuş:", ucus["ucus_no"])
        print("Rota:", ucus["kalkis_havalimani"], "→", ucus["varis_havalimani"])
        print("Kalkış:", ucus["kalkis"])
        print("Varış:", ucus["varis"])
        print("Fiyat:", round(ucus["fiyat"], 2), "TL")
        print("-" * 50)


# ---------------------------------
# ANA AKIŞ
# ---------------------------------

def main():
    kalkis, varis, tarih, maksimum_fiyat = kullanicidan_bilgi_al()

    kalkis_havalimanlari = sehir_dogrula(kalkis, "Kalkış")
    if kalkis_havalimanlari is None:
        sys.exit(1)

    varis_havalimanlari = sehir_dogrula(varis, "Varış")
    if varis_havalimanlari is None:
        sys.exit(1)

    if not tarih_dogrula(tarih):
        sys.exit(1)

    dolar_kuru = dolar_kuru_al()
    if dolar_kuru is None:
        sys.exit(1)

    print()
    print("Güncel USD/TRY kuru:", dolar_kuru)

    uygun_ucuslar = tum_rotalarda_ara(
        kalkis_havalimanlari, varis_havalimanlari, tarih, dolar_kuru, maksimum_fiyat
    )

    uygun_ucuslar.sort(key=lambda x: x["fiyat"])

    sonuclari_yazdir(uygun_ucuslar)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⏹️  İşlem kullanıcı tarafından durduruldu.")
        sys.exit(0)