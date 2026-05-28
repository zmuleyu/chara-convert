# AI Character Card Converter & Export Tool Links

> **Compiled:** 2026-05-27  
> **Scope:** Verified online links for AI character card conversion, export, migration, and editing tools across major platforms.  
> **Format:** Each entry includes name, URL, type, supported platforms, and brief description.

---

## Table of Contents

1. [Universal / Multi-Platform Converters](#1-universal--multi-platform-converters)
2. [Character.AI Export Tools](#2-characterai-export-tools)
3. [Browser Extensions](#3-browser-extensions)
4. [Online Card Editors](#4-online-card-editors)
5. [Chub.ai / CharacterHub Tools](#5-chubai--characterhub-tools)
6. [Open-Source Libraries & CLI Tools](#6-open-source-libraries--cli-tools)
7. [OpenClaw / Agent Runtime Integrations](#7-openclaw--agent-runtime-integrations)
8. [Platform-Specific Import/Export Notes](#8-platform-specific-importexport-notes)
9. [Related Resources & Guides](#9-related-resources--guides)

---

## 1. Universal / Multi-Platform Converters

These tools support conversion between multiple character card formats (Tavern V2/V3, JSON, YAML, platform-specific formats).

| # | Tool | URL | Type | Supports | Notes |
|---|------|-----|------|----------|-------|
| 1.1 | **Character Card Converter** | https://charactercardconverter.com/ | Web (Zero-Server) | TavernAI V2, SillyTavern, CharacterAI, Agnai, Backyard AI (Faraday), Voxta, TextGenWebUI + 48 hyper-specific conversion tools | Privacy-first, browser-based JS processing. No server upload. Established 2025. |
| 1.2 | **Character Card Converter — Universal Tool** | https://charactercardconverter.com/tools/universal/index.html | Web | Cross-platform universal conversion | "Rosetta Stone" for digital personas. Handles schema translation, metadata chunking (tEXt/zTXt), normalization. |
| 1.3 | **Character Card Converter — About / Mission** | https://charactercardconverter.com/about.html | Info | — | Data sovereignty mission statement. Zero-server architecture explanation. |

---

## 2. Character.AI Export Tools

Tools specifically designed to export characters and chats from Character.AI.

| # | Tool | URL | Type | Export Format | Notes |
|---|------|-----|------|---------------|-------|
| 2.1 | **CAI Tools** (irsat000) — GitHub | https://github.com/irsat000/CAI-Tools | Browser Extension (Chrome/Firefox) | Character cards, chat histories (readable/transferable), offline history | Most widely used CAI extension. Memory manager, background/font controls, clone/import characters, mass swipe. Mobile support via Firefox/Kiwi. |
| 2.2 | **CAI Tools** — Chrome Web Store | https://www.crxsoso.com/webstore/detail/nbhhncgkhacdaaccjbbadkpdiljedlje | Chrome Extension | Same as above | Chrome distribution. |
| 2.3 | **CAI Tools** — Firefox Add-ons | https://addons.mozilla.org/en-US/firefox/addon/cai-tools/ | Firefox Extension | Same as above | Official Firefox distribution. Also on Android Firefox. |
| 2.4 | **CAI Tools** — Guide / Docs | https://irsat.gitbook.io/cai-tools/ | Documentation | — | Official guide including known issues. |
| 2.5 | **CAI Tools** — Patreon | https://www.patreon.com/Irsat | Support | — | Membership/donations for premium features. |
| 2.6 | **Character.ai Exporter** — Firefox | https://addons.mozilla.org/en-US/firefox/addon/character-ai-exporter/ | Firefox Extension | PNG with embedded metadata (Janitor format), TXT, bulk ZIP export | Exports YOUR OWN characters only. Privacy-first, local storage only. Automatic caching on edit page visits. |
| 2.7 | **Wilds AI Exporter** (framersai) — GitHub | https://github.com/framersai/universal-ai-chat-story-exporter | Chrome Extension (Open Source) | Character.AI chat export | Free, open-source Chrome extension for exporting CAI chats. |
| 2.8 | **Character.AI Official Export** | Settings → Legal & Privacy → Export Data | Official Platform Feature | ZIP with JSON (user.json, character.json, message.json) | Official data export. Takes hours to days. Includes pinned memory (sometimes). Does NOT produce importable character cards. |

---

## 3. Browser Extensions

General-purpose browser extensions for character card management across platforms.

| # | Tool | URL | Type | Platforms | Notes |
|---|------|-----|------|-----------|-------|
| 3.1 | **CAI Tools** (see 2.1–2.5) | — | Chrome/Firefox | Character.AI → SillyTavern, Janitor AI | Character card + chat export/import. |
| 3.2 | **Character.ai Exporter** (see 2.6) | — | Firefox | Character.AI → Janitor format PNG | Own characters only. |
| 3.3 | **Janitor AI Scraper** | https://addons.mozilla.org/firefox/addon/janitor-ai-scraper/ | Firefox Extension | Janitor AI → PNG (Character V2 Spec) | Scrapes public Janitor AI characters for import into SillyTavern. Some limitations with lorebooks and multiple greetings. |
| 3.4 | **Chatbot Manager** (for Janitor AI export) | Chrome Web Store / Firefox Add-ons | Browser Extension | Janitor AI → Character card | Used by MegaNova Chat for Janitor AI character import workflow. |
| 3.5 | **Chub Card Extractor** (see 5.3) | — | Browser Extension | Chub.ai | Extracts cards, lorebooks, presets. |

---

## 4. Online Card Editors

Browser-based editors for creating and modifying character cards without installation.

| # | Tool | URL | Type | Format Support | Notes |
|---|------|-----|------|----------------|-------|
| 4.1 | **Chara Snap** | https://www.charasnap.com/ | Web Editor | SillyTavern V2 PNG, V3 PNG, CHARX, JSON | Free, no account. 100% client-side. Full lorebook editor. Mobile-friendly. Export to PNG or JSON. Compatible with SillyTavern, RisuAI, Agnai, Backyard AI, Janitor AI, Venus AI, OpenRoleplay. |
| 4.2 | **CCEditor** (lenML) | https://lenml.github.io/CCEditor | Web Editor | V1, V2, V3, compatibility mode | Multi-language UI (EN/ZH/JP/KR). Built-in Monaco code editor. Local history management. Direct card loading via URL (`?load_url=`). |
| 4.3 | **CCEditor** — GitHub | https://github.com/lenML/CCEditor | Open Source | Same as above | AGPL-3.0. Actively developed. |
| 4.4 | **zer0gear's Tavern Card Editor** — GitHub | https://github.com/zer0thgear/character-card-editor | Desktop/Web | V2/V3 spec | Node.js app. Granular editing (reorder greetings, swap main greeting, lorebook import, remove asterisks). Live version available. Not a chat frontend — editor only. |
| 4.5 | **AI Character Card Generator** (SillyTavern) — AIPRM GPT | https://app.aiprm.com/gpts/g-k2XkHmLPL/ai-character-card-generator-sillytavern | GPT Tool | JSON V2 | Generates V2 character cards via ChatGPT/Claude prompts. |

---

## 5. Chub.ai / CharacterHub Tools

Tools for downloading, scraping, and extracting character cards from Chub.ai / CharacterHub.

| # | Tool | URL | Type | Function | Notes |
|---|------|-----|------|----------|-------|
| 5.1 | **Chub Card Extractor** (korenko-git) | https://github.com/korenko-git/chub-card-extractor | Browser Extension | Extract cards from Chub.ai | TypeScript + Vite. Extracts characters, lorebooks, presets. Packages into ZIP with JSON, Markdown/HTML, images. |
| 5.2 | **Chub.ai Card Downloader** (Samueras) | https://github.com/Samueras/chub_downloader | Python GUI App | Download Chub.ai cards | Standalone .exe available. Download by URL/path, search with filters (tags, creator, token count). Saves JSON + images + HTML overview. API token support for restricted content. |
| 5.3 | **Chub.ai Character Link Mass Scraper** (GentleBurr) | https://github.com/GentleBurr/chub-charlink-scraper | Bookmarklet / Userscript | Bulk-scrape Chub.ai character links | Universal: works on Android (Firefox/Chrome/Edge), iOS Safari, Desktop. Auto-updating. Tag filtering. Direct import into SillyTavern via URL paste. |
| 5.4 | **pyllmchat** (beep39) | https://github.com/beep39/pyllmchat | Python Library | Chat with Chub.ai characters | Supports TabbyAPI, LLamacpp, KoboldAI, exllama. Loads character cards via `chat.char.load`. |

---

## 6. Open-Source Libraries & CLI Tools

Programmatic libraries and command-line tools for character card manipulation.

| # | Tool | URL | Language | Function | Notes |
|---|------|-----|----------|----------|-------|
| 6.1 | **aichar** (HubertKasperek / Hukasx0) | https://github.com/HubertKasperek/aichar | Python (Rust-backed via PyO3/Maturin) | Read/edit/create/export AI characters | Supports JSON, YAML, PNG cards. Compatible with TavernAI, SillyTavern, TextGenerationWebUI, AI-companion, Pygmalion. Neutral export format for universal compatibility. Used by Character Factory. |
| 6.2 | **tavern_card_tools** (Barafu) | https://github.com/Barafu/tavern_card_tools | Rust | CLI tools for SillyTavern cards | `print`, `print_all`, `baya_get` (Backyard AI URL extractor), `de8` (remove asterisks). Windows .exe releases available. |
| 6.3 | **chara_convert** (321BadgerCode) | https://github.com/321BadgerCode/chara_convert | Perl | Convert PNG V2 cards to JSON/YAML | For Oobabooga Text Generation WebUI. Uses exiftool for metadata extraction. |
| 6.4 | **SillyTavern Character Generator** (cha1latte) | https://github.com/cha1latte/sillytavern-character-generator | AI Prompt | Generate V2 cards via LLM | Two versions: Standard (600–1000 tokens) and Small Model (400–600 tokens). Upload prompt to Claude/GPT/Gemini/DeepSeek. |
| 6.5 | **airole** (easychen) | https://github.com/easychen/airole | Node.js / Web | AI character card creator from image | Upload character image → AI analyzes → generates attributes. Export JSON or PNG. Optional Google Drive backup. |
| 6.6 | **characterai-dumper** | https://www.libhunt.com/compare-CAI-Tools-vs-characterai-dumper | Python | Character.AI data export | Alternative to CAI Tools. See LibHunt comparison page for details. |

---

## 7. OpenClaw / Agent Runtime Integrations

Tools for importing SillyTavern character cards into agent runtimes and messaging platforms.

| # | Tool | URL | Runtime | Function | Notes |
|---|------|-----|---------|----------|-------|
| 7.1 | **SillyTavern Cards Skill** (pearyj) | https://github.com/pearyj/sillytavern-cards-skill | OpenClaw | Import & roleplay with V2/V3 cards on WhatsApp/Telegram/Discord | Persistent memory across sessions. `/character import`, `/character play`, `/character list` commands. Pure Node.js PNG parser (zero deps). Also listed on openclaw/skills registry. |
| 7.2 | **SoulTavern** (imphillip) | https://github.com/imphillip/SoulTavern | Hermes-Agent, OpenClaw | Convert V2 cards to SOUL.md personas | Stdlib-only Python (≥3.10). Targets: `--target hermes` (SOUL.md + HERMES.md) or `--target openclaw` (SOUL.md + AGENTS.md + IDENTITY.md). Oversized card handling. Used by agentbox.id. |
| 7.3 | **openclaw-tavern** (garfeildma) | https://github.com/garfeildma/openclaw-tavern | OpenClaw | SillyTavern-compatible roleplay skill | V1/V2 PNG and JSON import. Lorebook import. Session lifecycle, long memory (SQLite embeddings), multimodal (`/rp speak`, `/rp image`, `/rp video`). |
| 7.4 | **SillyTavern Cards Skill** — OpenClaw Registry | https://github.com/openclaw/skills/blob/main/skills/pearyj/sillytavern-cards-skill/SKILL.md | OpenClaw | Registry entry | Official skill definition for OpenClaw. |

---

## 8. Platform-Specific Import/Export Notes

### 8.1 Character.AI
- **Official export:** Settings → Legal & Privacy → Export Data → ZIP with JSON. No character card format.
- **CAI Tools extension:** Downloads characters as cards + chat histories. Best tool available.
- **Character.ai Exporter (Firefox):** Exports own characters as PNG (Janitor format) or TXT.
- **Limitation:** Many CAI characters have private definitions — cannot be fully exported.

### 8.2 Chai
- **No official export tool found.** Chai is a closed mobile ecosystem.
- Characters would need manual rebuilding for migration.

### 8.3 FictionLab
- **No export functionality** as of early 2026 (per multiple reviews).
- Characters stay on-platform. Manual recreation required elsewhere.

### 8.4 PolyBuzz
- **Supports IMPORT** of existing character cards (Tavern/Character.AI → PolyBuzz).
- **No export tool found.** Closed ecosystem — cannot bulk export conversations or characters.
- PolyBuzz → FictionLab/Swerve migration requires manual rebuilding.

### 8.5 Nomi
- **No export tool found.** Closed ecosystem with Mind Map / Memory Hub.
- Up to 10 custom characters. Manual rebuilding required for migration.

### 8.6 Dopple
- **No export tool found.** Closed ecosystem.
- Dopple → Swerve/Emochi/Chub migration requires manual rebuilding.

### 8.7 Janitor AI
- **Native import/export:** Supports character cards (PNG V2). Can directly import without extensions (per community reports as of 2026).
- **Janitor AI Scraper extension:** Exports public Janitor AI characters as PNG V2 for SillyTavern.
- **Chatbot Manager extension:** Used for export to other platforms (e.g., MegaNova Chat).

### 8.8 SillyTavern
- **Native format:** Tavern V2/V3 PNG (JSON embedded in tEXt metadata chunk).
- **Chat import from:** Character.AI (via CAI Tools), TavernAI, Text Generation WebUI, Agnai, KoboldAI Lite, RisuAI.
- **Export chats:** `.jsonl` (full metadata) or `.txt` (plain text, not re-importable).
- **Docs:** https://docs.sillytavern.app/usage/core-concepts/chatfilemanagement/

### 8.9 Agnai
- **Native import:** Character cards V2 PNG.
- Listed as supported import source in SillyTavern docs.
- Open source: https://github.com/agnaistic/agnai

### 8.10 RisuAI
- **Native support:** Character card V2 PNG.
- Supports multiple APIs, lorebook, emotion images, group chats, plugins.
- Open source: https://github.com/kwaroran/RisuAI
- Bulk chat export/import has been requested (GitHub issue #583).

### 8.11 Pephop AI
- Supports import/export of **JSON character cards** from TavernAI.

### 8.12 Backyard AI / Faraday
- Uses Character Card V2 format.
- Supported by CharacterCardConverter.com universal tools.

---

## 9. Related Resources & Guides

| # | Resource | URL | Type | Description |
|---|----------|-----|------|-------------|
| 9.1 | **SillyTavern Docs — Chat File Management** | https://docs.sillytavern.app/usage/core-concepts/chatfilemanagement/ | Official Docs | How to import/export chats and manage character cards in SillyTavern. |
| 9.2 | **SillyTavern Docs — GitHub** | https://github.com/SillyTavern/SillyTavern-Docs/blob/main/Usage/Characters/chatfilemanagement.md | Official Docs | Source for chat file management docs. |
| 9.3 | **Tavern Studio** | https://tavernstudio.com/ | Native App | Windows/Android native client. SillyTavern-compatible. LAN sync, encrypted storage, WebView cards. |
| 9.4 | **Character-Tavern.com — Chub Import Guide** | https://character-tavern.com/docs/chub | Guide | How to import Chub Venus cards into Character Tavern. |
| 9.5 | **AI Character Card Converter — Guides & Specs** | https://charactercardconverter.com/ (Browse All Guides) | Technical Docs | Repair docs, specification deep dives, privacy guides for card formats. |
| 9.6 | **Export Character AI Chats (2026 Guide)** | https://aiinsightsnews.net/how-to-export-character-ai-chat/ | Guide | Comprehensive guide on official CAI export, manual copy, JSON parsing, and troubleshooting. |
| 9.7 | **FictionLab AI Review 2026** | https://aiinsightsnews.net/ictionlab-ai/ | Review | Confirms FictionLab has no character export as of early 2026. |
| 9.8 | **Chub AI vs Janitor AI Migration Guide** | https://www.roborhythms.com/chub-ai-vs-janitor-ai-before-switching/ | Guide | Migration checklist for Janitor AI → Chub AI. |
| 9.9 | **How to Import Janitor AI Characters to MegaNova** | https://blog.meganova.ai/how-to-import-trending-janitor-ai-characters-to-meganova-chat/ | Guide | Uses Chatbot Manager extension for Janitor AI export. |
| 9.10 | **Janitor AI Character Builder (Nivrao)** | https://www.nivrao.com/janitor-ai-character-builder | Tool | Character builder with Janitor-formatted export. |
| 9.11 | **Nomi AI vs PolyBuzz Comparison** | https://www.aigirlfriendscout.com/comparisons/nomi-ai-vs-polybuzz | Review | Confirms PolyBuzz supports character card import (from Tavern/CAI). |
| 9.12 | **PolyBuzz vs Emochi Guide** | https://zeroskillai.com/polybuzz-ai-vs-emochi-ai/ | Review | Notes PolyBuzz is a closed ecosystem with no bulk export. |

---

## Summary Matrix

| Platform | Can Export Card | Can Import Card | Known Tool | Notes |
|----------|-----------------|-----------------|------------|-------|
| Character.AI | ⚠️ Partial (CAI Tools) | ❌ No | CAI Tools, CAI Exporter | Private defs hidden; chats exportable |
| Chai | ❌ No | ❌ No | — | Closed ecosystem |
| FictionLab | ❌ No | ❌ No | — | No export as of 2026 |
| PolyBuzz | ❌ No | ✅ Yes (V2 cards) | — | Can import, cannot export |
| Nomi | ❌ No | ❌ No | — | Closed ecosystem |
| Dopple | ❌ No | ❌ No | — | Closed ecosystem |
| Janitor AI | ✅ Yes (PNG V2) | ✅ Yes | Janitor AI Scraper, native | Direct import without extensions possible |
| SillyTavern | ✅ Yes (PNG V2/V3, JSON) | ✅ Yes (PNG V2/V3, JSON) | Native | De facto open standard |
| Chub.ai / Venus | ✅ Yes (PNG V2) | ✅ Yes (PNG V2) | chub_downloader, Card Extractor | Largest card repository |
| Agnai | ✅ Yes | ✅ Yes | Native | Open source |
| RisuAI | ✅ Yes | ✅ Yes | Native | Open source |
| Backyard AI / Faraday | ✅ Yes (V2) | ✅ Yes (V2) | Native | |
| Pephop AI | ✅ Yes (JSON) | ✅ Yes (JSON) | Native | |
| Tavern Studio | ✅ Yes | ✅ Yes | Native | Windows/Android app |

**Legend:** ✅ = Yes / Fully supported  |  ⚠️ = Partial / Workaround required  |  ❌ = No / Not supported

---

## Methodology

This list was compiled through systematic web search across 7 dimensions:
1. Generic/multi-platform converters
2. Character.AI-specific export tools
3. Chai/FictionLab/PolyBuzz/Nomi-specific tools
4. Browser extensions (Chrome/Firefox)
5. GitHub open-source projects
6. Online card editors
7. OpenClaw/agent runtime integrations

Each link was verified against search result content. Tools marked with GitHub URLs are open-source. Web tools marked "Zero-Server" process data locally in the browser.

---

*End of report.*
