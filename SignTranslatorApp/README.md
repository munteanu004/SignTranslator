# SignTranslator - Aplicație Mobilă React Native

O aplicație modernă pentru traducerea limbajului semnelor în vorbire și invers, cu design inspirat din SignTalker.

## 🎨 Design

Design-ul aplicației este inspirat din [SignTalker de pe Behance](https://www.behance.net/gallery/165769721/SignTalker-Sign-language-translation)

**Paletă de culori:**
- Primară: `#45C8C2` (Turcoaz)
- Fundal: `#FFFFFF` (Alb)
- Fundal secundar: `#E8E8E8` / `#F5F5F5`
- Text: `#111111` (Negru) / `#666666` (Gri)
- Font: Poppins (System default)

## 📱 Caracteristici

- **Translation** - Traduce text/voce în limbaj al semnelor cu avatar animat
- **Conversation** - Conversație în timp real cu traducere bidirecțională
- **Avatar** - Vizualizare și personalizare avatar pentru semne
- **Account** - Setări profil, limbă aplicație, limbaj semnelor

## 🚀 Instalare și Rulare

### Cerințe preliminare

```bash
Node.js v18+
npm sau yarn
Android Studio (pentru Android)
Xcode (pentru iOS - doar macOS)
```

### Instalare dependențe

```bash
cd SignTranslatorApp
npm install
```

### Rulare pe Android

```bash
# Pornește Metro Bundler
npm start

# În alt terminal, rulează pe Android
npm run android
```

### Rulare pe iOS (doar macOS)

```bash
cd ios
pod install
cd ..
npm run ios
```

## 📁 Structura Proiectului

```
SignTranslatorApp/
├── src/
│   ├── screens/
│   │   ├── HomeScreen.tsx          # Ecran Translation
│   │   ├── ConversationScreen.tsx  # Ecran Conversation
│   │   ├── AccountScreen.tsx       # Ecran Account/Settings
│   │   ├── LoginScreen.tsx         # Ecran Login
│   │   └── SignupScreen.tsx        # Ecran Sign Up
│   └── theme/
│       └── colors.ts               # Paletă culori
├── android/                        # Cod nativ Android
├── ios/                            # Cod nativ iOS
└── App.tsx                         # Punct de intrare + navigație
```

## 🔧 Tehnologii Folosite

- **React Native 0.82** - Framework pentru aplicații mobile
- **React Navigation** - Navigare (Stack + Bottom Tabs)
- **React Native Vector Icons** - Iconițe Material Community
- **TypeScript** - Type safety

## 🎯 Funcționalități Implementate

- ✅ Design complet SignTalker
- ✅ Login/Signup cu email și social (Facebook, Google)
- ✅ Bottom Navigation cu 4 taburi
- ✅ Ecran Translation cu selector limba + avatar
- ✅ Ecran Conversation pentru chat în timp real
- ✅ Ecran Account cu setări profil
- ✅ Interfață intuitivă și modernă

## 🔗 Integrare Backend Python

Backend-ul Python existent (cu modelele WLASL, How2Sign, HamNoSys) va fi integrat prin:

1. **API REST** - Server Flask/FastAPI
2. **WebSocket** - Pentru streaming video în timp real
3. **React Native Bridge** - Pentru comunicare nativă

### Endpoint-uri necesare:

```
POST /api/text-to-sign    - Convertește text în video semne
POST /api/voice-to-sign   - Convertește audio în video semne
POST /api/sign-to-text    - Convertește video semne în text
POST /api/sign-to-voice   - Convertește video semne în audio
```

## 📦 Build Production

### Android APK

```bash
cd android
./gradlew assembleRelease
# APK-ul va fi în: android/app/build/outputs/apk/release/
```

### Android AAB (Google Play)

```bash
cd android
./gradlew bundleRelease
# AAB-ul va fi în: android/app/build/outputs/bundle/release/
```

## 🐛 Debugging

```bash
# Pornește React Native Debugger
npm run start

# Vezi log-uri Android
npm run android -- --verbose

# Curăță cache
npm start -- --reset-cache
```

## 👥 Contribuție

Aplicație dezvoltată pentru traducerea limbajului semnelor cu AI.

## 📄 Licență

MIT License
