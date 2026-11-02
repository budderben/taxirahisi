# TaxRahisi - Android Mobile Application

Programu ya Simu ya Mkononi kwa ajili ya Mfumo wa TaxRahisi (Mamlaka ya Mapato Tanzania - TRA na Sekta Isiyo Rasmi).

Official Android mobile client for the **TaxRahisi** informal sector presumptive tax initiative in Tanzania.

---

## 📦 Pakua na Sakinisha (Installation)

Fayili ya APK iko hapa:
`android_app/TaxRahisi.apk`

### 1. Sakinisha kupitia ADB (Android Debug Bridge):
```bash
adb install android_app/TaxRahisi.apk
```
Au sasisha (update):
```bash
adb install -r android_app/TaxRahisi.apk
```

### 2. Sakinisha kwenye Simu Halisi (Physical Phone / Sideloading):
1. Tuma fayili ya `TaxRahisi.apk` kwenye simu yako kupitia **USB Cable**, **WhatsApp**, **Telegram**, au **Bluetooth**.
2. Kwenye simu, fungua fayili ya `TaxRahisi.apk`.
3. Ruhusu "Install from Unknown Sources" (Ruhusu kusakinisha kutoka chanzo hiki).
4. Bonyeza **Install** (Sakinisha).

---

## 🌟 Vipengele Muhimu (Key Features)

1. **Uendeshaji Bila Intaneti (Offline Capable)**:
   - Mfumo mzima umejumuishwa ndani ya APK (`assets/www/`).
   - Wafanyabiashara wadogo masokoni wanaweza kukokotoa kodi, kufanya mahesabu ya awamu (Robo mwaka, mwezi, wiki), na kufanya majaribio ya USSD hata bila bando la intaneti.

2. **Kikokotoo cha Kodi ya Makadirio (Presumptive Tax - Cap 332)**:
   - Viwango rasmi vya Sheria ya Kodi ya Mapato Sura ya 332:
     - Hadi 4,000,000 TZS: Bure (0 TZS)
     - 4,000,001 - 7,000,000 TZS: 100,000 TZS (au 3% kwa wenye vitabu)
     - 7,000,001 - 11,000,000 TZS: 250,000 TZS
     - 11,000,001 - 14,000,000 TZS: 450,000 TZS
     - Zaidi ya 14,000,000 TZS: 3.5%
   - Mgawanyo wa awamu za kulipa (Robo Mwaka, Kila Mwezi, Kila Wiki).

3. **USSD Simulator na Kupiga Simu Halisi (`*150*88#`)**:
   - Skrini ya mfano wa simu ya kawaida (feature phone / simu ya tochi).
   - Kitufe cha **"Piga *150*88# Kwenye Simu Halisi"** kinachofungua kipiga simu (Dialer) cha Android kiotomatiki (`Intent.ACTION_DIAL`).

4. **Malipo ya GePG na Mitandao ya Simu**:
   - Huzalisha Nambari ya Kumbukumbu ya Malipo ya Serikali (GePG Control Number `991XXXXXXXXX`).
   - Huwezesha majaribio ya STK Push kwa **M-Pesa**, **Tigo Pesa**, **Airtel Money**, na **HaloPesa**.
   - Huzalisha risiti ya kielektroniki ya TRA yenye uwezo wa kushirikiwa kupitia WhatsApp au SMS kwa kubonyeza kitufe kimoja.

5. **Kadi ya Mlipakodi Kidijitali (Digital Compliance Badge)**:
   - Kitambulisho cha kidijitali chenye nembo ya TRA, picha ya mfanyabiashara, TIN, Chama cha Wafanyabiashara (mfano: VIBINDO, UWAWAMA), na QR Code ya uhakiki.

6. **Lugha Mbili (Kiswahili & Kiingereza)**:
   - Badilisha lugha wakati wowote kwa kubonyeza kitufe cha 🌐 juu ya skrini.

---

## 🛠️ Muundo wa Mradi (Project Structure)

```text
android_app/
├── TaxRahisi.apk                 # Final signed, aligned release/debug APK
├── build.sh                      # Automated build & signing script
├── settings.gradle               # Gradle multi-project definition
├── build.gradle                  # Root build script
├── app/
│   ├── build.gradle              # App module build script
│   └── src/main/
│       ├── AndroidManifest.xml   # App manifest with permissions & config
│       ├── java/com/taxrahisi/app/
│       │   ├── MainActivity.java     # WebView controller & lifecycle
│       │   └── WebAppInterface.java  # Native Android - JavaScript bridge
│       ├── res/                  # App colors, strings, styles, icons
│       └── assets/www/           # Standalone mobile web client & images
```

---

## 🔨 Jinsi ya Kujenga Upya APK (Rebuilding the APK)

Endapo utafanya mabadiliko kwenye kodi au muonekano, jenga upya APK kwa kuendesha:

```bash
cd /home/ben/Desktop/taxRahisi/android_app
chmod +x build.sh
./build.sh
```

Hii itakusanya kodi, kutengeneza `classes.dex`, kufungasha raslimali na `aapt`, kupanga kwa `zipalign`, na kusaini kwa `apksigner`.
