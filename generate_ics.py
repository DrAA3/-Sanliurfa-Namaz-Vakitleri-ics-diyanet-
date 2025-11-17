import asyncio
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
from ics import Calendar, Event
from zoneinfo import ZoneInfo
from playwright.async_api import async_playwright

AYLAR_TR_EN = {
    "Ocak": "January", "Şubat": "February", "Mart": "March", "Nisan": "April",
    "Mayıs": "May", "Haziran": "June", "Temmuz": "July", "Ağustos": "August",
    "Eylül": "September", "Ekim": "October", "Kasım": "November", "Aralık": "December"
}

# Şanlıurfa sayfası. Şehir değiştirmek istersen bu URL'yi güncellersin.
URL = "https://namazvakitleri.diyanet.gov.tr/tr-TR/9831/sanliurfa-icin-namaz-vakti"

async def fetch_html():
    # Playwright: siteyi tarayıcı gibi açıp tabloyu yükler
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(locale="tr-TR")
        page = await context.new_page()
        await page.goto(URL, wait_until="networkidle")
        # Tablo yüklenene kadar bekle
        await page.wait_for_selector("table.vakit-table tbody tr", timeout=30000)
        html = await page.content()
        await browser.close()
        return html

def parse_and_build_ics(html: str) -> Calendar:
    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("table.vakit-table tbody tr")
    cal = Calendar()

    for row in rows:
        cols = [c.get_text(strip=True) for c in row.find_all("td")]
        if len(cols) < 10:
            continue

        # Miladi tarih: "17 Kasım 2025 Pazartesi" -> "17 November 2025"
        parts = cols[2].split()
        if len(parts) < 3:
            continue
        gun, ay_tr, yil = parts[0], parts[1], parts[2]
        ay_en = AYLAR_TR_EN.get(ay_tr, ay_tr)
        date_str_en = f"{gun} {ay_en} {yil}"
        try:
            date = datetime.strptime(date_str_en, "%d %B %Y").date()
        except:
            continue

        vakitler = {
            "İmsak": cols[4],
            "Güneş": cols[5],
            "Öğle": cols[6],
            "İkindi": cols[7],
            "Akşam": cols[8],
            "Yatsı": cols[9],
        }

        for isim, saat in vakitler.items():
            try:
                dt_local = datetime.strptime(
                    f"{date.strftime('%Y-%m-%d')} {saat}", "%Y-%m-%d %H:%M"
                ).replace(tzinfo=ZoneInfo("Europe/Istanbul"))
                ev = Event()
                ev.name = isim   # sade adlar
                ev.begin = dt_local
                ev.end = dt_local + timedelta(minutes=30)
                cal.events.add(ev)
            except:
                continue

    return cal

async def main():
    html = await fetch_html()
    cal = parse_and_build_ics(html)
    with open("sanliurfa_namaz_vakitleri.ics", "w", encoding="utf-8") as f:
        f.writelines(cal)
    print(f"Toplam etkinlik sayısı: {len(cal.events)}")

if __name__ == "__main__":
    asyncio.run(main())
