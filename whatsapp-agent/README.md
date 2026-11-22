# WhatsApp AI Agent (Claude)

Agent ka jawaaba farriimaha WhatsApp, isagoo isticmaalaya Claude iyo **WhatsApp Cloud API** (habka rasmiga ah ee Meta, lambarkaaga lama xirayo).

Qaab-dhismeedka:

```
Telefoonkaaga → WhatsApp → Meta → Render (app.py) → Claude
                                         ↓
Telefoonkaaga ← WhatsApp ← Meta ← jawaabta
```

Waxaad u baahan tahay 3 akoon oo bilaash ah in la furo: **Anthropic**, **Meta for Developers**, **Render**. Claude-na lacag yar ayuu ku baxaa (credits).

---

## Tallaabada 1: Furaha Claude (Anthropic API key)

1. Tag **platform.claude.com**, akoon samee.
2. **Billing** → ku shub credits (lacag yar ayaa ku filan tijaabada).
3. **API Keys** → **Create Key** → koobi garee (`sk-ant-...`).
4. Meel ammaan ah ku keydi. **Cidna ha la wadaagin, GitHub-na ha geline.**

✅ Haysataa: `ANTHROPIC_API_KEY`

## Tallaabada 2: App-ka Meta + WhatsApp

1. Tag **developers.facebook.com** → ku gal akoonkaaga Facebook.
2. **My Apps** → **Create App**.
3. Marka la weydiiyo isticmaalka (use case), dooro kan WhatsApp ah (tusaale "Connect with customers through WhatsApp"). Haddii la weydiiyo Business portfolio, mid samee.
4. App-ka gudihiisa: **WhatsApp → API Setup**. Halkan waxaad ka heleysaa:
   - **Temporary access token** → `WHATSAPP_TOKEN`
   - **Phone number ID** → `WHATSAPP_PHONE_ID`
   - Lambar tijaabo ah oo Meta ku siisay (**From**)
   - Version-ka API-ga ee ku qoran tusaalaha koodhka (tusaale `v21.0`) → `GRAPH_VERSION`
5. Qaybta **To**: ku dar **lambarkaaga telefoonka** oo xaqiiji code-ka laguu soo diro.
6. Tijaabi: riix **Send message**. Haddii farriin "Hello World" telefoonkaaga ku timaaddo, tallaabadani way dhammaatay.
7. **App settings → Basic** → **App secret** → **Show** → `WHATSAPP_APP_SECRET`
8. Samee eray sir ah oo adigu dooratay (tusaale `walaqaye-2026-xyz`) → `WHATSAPP_VERIFY_TOKEN`

✅ Haysataa: `WHATSAPP_TOKEN`, `WHATSAPP_PHONE_ID`, `WHATSAPP_APP_SECRET`, `WHATSAPP_VERIFY_TOKEN`, `GRAPH_VERSION`

⚠️ Token-ka "temporary" wuxuu dhacaa 24 saac kadib. Tijaabada waa ku filan. Kadib eeg "Tallaabada 6".

## Tallaabada 3: Server-ka ku shid Render

1. Tag **render.com** → **Sign up with GitHub**.
2. **New → Web Service** → dooro repo-ga `Walaqaye`.
3. Buuxi:
   - **Branch:** branch-ka uu koodhkani ku jiro
   - **Root Directory:** `whatsapp-agent`
   - **Runtime:** Python
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `gunicorn app:app --workers 1 --threads 8 --timeout 120`
   - **Instance type:** Free
4. **Environment Variables**: ku dar 6-da qiime ee kor ku xusan (eeg `.env.example`).
5. **Create Web Service** → sug ilaa "Live" ka muuqdo.
6. Koobi garee URL-ka (tusaale `https://whatsapp-agent-xxxx.onrender.com`). Browser-ka ku fur. Waa inaad aragtaa: *"WhatsApp agent wuu shaqeynayaa"*.

## Tallaabada 4: Meta ku xir server-kaaga (webhook)

1. Meta app → **WhatsApp → Configuration** → **Webhook** → **Edit**.
2. **Callback URL:** `https://whatsapp-agent-xxxx.onrender.com/webhook` (ha ilaawin `/webhook`)
3. **Verify token:** erayga sirta ah ee `WHATSAPP_VERIFY_TOKEN`
4. **Verify and save**.
5. **Webhook fields** → **messages** → **Subscribe**.

## Tallaabada 5: Tijaabi

Telefoonkaaga, WhatsApp-ka ugu qor lambarka tijaabada ee Meta: *"Cimilada Muqdisho maxay tahay?"*

Jawaab ayaa kuu imaanaysa. Farriinta koowaad waxay qaadan kartaa ilaa 1 daqiiqo, sababtoo ah Render Free wuu seexdaa marka aan la isticmaalin.

**Haddii jawaab aan la helin:** Render → **Logs**. Halkaas ayaa khaladka ka muuqanaya.

| Khaladka logs-ka | Sababta |
|---|---|
| `KeyError: 'WHATSAPP_TOKEN'` | Environment variable ayaa maqan |
| `WhatsApp khalad: 401` | Token-ku wuu dhacay ama waa khalad |
| `authentication_error` | `ANTHROPIC_API_KEY` waa khalad |
| `credit balance is too low` | Credits ku shub Anthropic |
| Webhook verify wuu fashilmay | URL-ka ama verify token-ka waa khalad |

## Tallaabada 6: Ka hor intaadan dadka kale u furin

- **Token joogto ah:** Meta Business Settings → System Users → samee System User → token cusub oo `whatsapp_business_messaging` leh.
- **Lambar dhab ah:** ku dar lambar ganacsi (WhatsApp → Phone numbers). Lambar ku jira WhatsApp-ka caadiga ah waa in marka hore laga saaro.
- **Xusuusta:** hadda waxay ku jirtaa RAM, wayna lumaysaa marka server-ku dib u kaco. Ku beddel database.
- **Daaqadda 24 saac:** qof waxaad si xor ah ugu jawaabi kartaa kaliya 24 saac gudahood marka uu kuu soo qoro.

## Sida agent-ka loo beddelo

- **Shakhsiyadda iyo tilmaamaha:** beddel `SYSTEM_PROMPT` gudaha `app.py` (ama environment variable `SYSTEM_PROMPT`).
- **Tools cusub:** ku dar `TOOLS` (sharraxaad + `input_schema`) kadibna ku dar `execute_tool`. `get_weather` waa tijaabo oo keliya.
