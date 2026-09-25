# 34 Gaon — Social Web Collect Notes / नोट्स

## Summary / सारांश

- Searches run: ~48 WebSearch queries (Hindi umbrella terms, English umbrella terms, per-village names, shrine/fair names, org names, hashtags, known-creator names, allowed_domains-restricted variants).
- Unique URLs collected: **11** (all in `social_web.jsonl`)
- By platform: Facebook = 8, Instagram = 3, YouTube = 0 (no YouTube hit found that clearly names a specific one of the 34 villages — several generic "old village"/army-exercise YouTube videos appeared but were excluded per the brief's rule that YouTube hits must name a village).
- By village: `34-gaon` (umbrella/region) = 8, `khiyana` (unconfirmed) = 1, `unknown` = 2.
- Per-village-name hits (bhojrasar, kumbhana, thoiya, manera, khanisar, motlai, duder, chidasar, meusar, kolana, ajeetwana, ladera, bhanabasti, nathor, berawala, kanolai, dhannasar, rina, motasar, bhunwala, chakdo, dewasar, machhranwali, kankraliyo, lakhor-chhoti, lakhor-moti, jagor, rampura, duderiya, hathusar, hindor, tidasar, birmana, likhmisar, kumbhasar, kachrana): **0 direct hits**. Every per-village query (Hindi and English spellings, with "गांव", "पुराना", "महाजन", "बीकानेर" qualifiers) returned only unrelated Facebook/Instagram noise (other villages of the same name elsewhere in India, generic "old village" content, unrelated people).

निष्कर्ष: गूगल/बिंग-आधारित WebSearch टूल से फेसबुक रील्स और इंस्टाग्राम रील्स का इंडेक्स बहुत कमज़ोर है, खासकर छोटे क्रिएटर्स की हिंदी/बागड़ी सामग्री का। ज़्यादातर परिणाम जेनेरिक "गांव" वीडियो या पूरी तरह असंबंधित पन्ने थे।

## Why recall was low / कम नतीजे क्यों मिले

1. The WebSearch tool's `site:facebook.com` / `site:instagram.com` operator did not reliably restrict results — most queries returned generic village-life content, news-page videos, or completely unrelated profiles rather than true site-restricted hits. Switching to the `allowed_domains` parameter helped marginally but the underlying index of FB/IG reels for this hyper-local Rajasthani topic appears very thin.
2. Facebook/Instagram Reels are algorithmically served and largely not crawled/indexed by general web search, especially content from small personal accounts (which is exactly what this project needs — displaced families' own reels).
3. Village names in this list are short, common Rajasthani agricultural-village names (Rina, Rampura, Birmana, Dewasar, Likhmisar etc.) that collide heavily with same-named villages elsewhere in Rajasthan/India, burying any real hits under noise.
4. Shrine/fair name searches (Nathu Dada Dhora, Peer Baba Kanolai Dham, Dada Pamma ji Maharaj Kumbhana) returned mostly unrelated "Peer Baba"/"Dada" devotional pages from other regions (Haryana, UP, Bihar) — these terms are common across North Indian folk religion.
5. Searching by the already-known creator names (Dinesh Beniwal, Chhaganlal Jakhar, Rameshwer Godara, Mukesh Jaat Phalwan, Sunil Beniwal, Rajuram Dhatrwal) mostly surfaced same-named but unrelated people, except one possible Instagram match for Dinesh Beniwal (different handle spelling than previously known — flagged, unconfirmed).

## What did surface / जो मिला

The only genuine, geographically-confirmed hits are all tied to the **Mahajan Field Firing Range as a place name** (news/army-exercise/bomb-discovery content) rather than to nostalgia/heritage reels about the specific 34 villages:

- Two Instagram reels + one Facebook video about a live bomb found near Mahajan qasba and on the Mahajan–Sherpura link road (Lunkaransar) — regional news reels, useful for showing the area is still live-fire-hazardous, not for village heritage content itself.
- One Facebook post about a blast in the Bajju area (a known IGNP resettlement chak for displaced 34-gaon families) — worth a manual look for comment threads that might mention village origin.
- Several Facebook video/photo posts from news pages (Arjansar station page, Zee Rajasthan News, Times Now Navbharat) about military exercises at Mahajan Field Firing Range — confirms the location but is generic army-exercise news, not community content.
- One Facebook page, "Nathu Dada Ka Diwana", whose name matches the Nathu Dada Dhora shrine near Khiyana — **flagged as unconfirmed**, page content was not accessible through search snippets so it could equally be devotion to an unrelated "Nathu Dada" figure elsewhere. Worth a manual visit.
- One Instagram profile for "Dinesh Beniwal" (@dinesh__beniwal_) that may or may not be the same already-known creator (handle differs from previously known "dineshbeniwalll") — flagged for manual verification.

## Hubs worth a person following manually / मैन्युअल रूप से फॉलो करने लायक

1. **facebook.com/p/Nathu-Dada-Ka-Diwana-100076226135788/** — possible devotee page for the Nathu Dada Dhora shrine near Khiyana; needs a logged-in check to confirm it's actually about the Bikaner-region shrine and not a different Nathu Dada.
2. **facebook.com/Arjansarsationofficial** — an "Arjansar Station" official-style page that regularly posts Mahajan Field Firing Range news; a village very close to the firing range, could be a useful ongoing source for regional content and possibly linked posts from residents/ex-residents.
3. **facebook.com/humarabikanerpage** and **Zee Rajasthan News / Times Now Navbharat / Punjab Kesari FB pages** — regional Bikaner news pages that periodically cover Mahajan Field Firing Range events (bomb discoveries, army exercises); scanning their post history directly on Facebook (not via this search tool) could turn up village-tagged content or commenters who are ex-residents.
4. Already-known hubs from the brief (Dinesh Beniwal, Chhaganlal Jakhar, Rameshwer Godara, Mukesh Jaat Phalwan, Sunil Beniwal, Rajuram Dhatrwal, मुकेश नायक कृष्ण नगर, Bharat Speaks page, YouTube channels Dinesh Beniwal / Akshay Godara / Shubh Journey / Rssuthar Jaisalmer / Apna 465 Rd) remain the strongest known hubs — none could be re-confirmed or expanded via this web-search pass; direct in-platform search (logged into Facebook/Instagram) will likely be far more productive for these than the general web search tool used here.

## Queries that worked vs. returned nothing / कौन से सर्च काम आए

**Worked (returned at least one genuinely relevant, geographically-confirmed URL):**
- "महाजन-शेरपुरा गांव जिंदा बम instagram reel"
- "34 गांव महाजन फायरिंग रेंज विस्थापित" (restricted to instagram.com)
- "रणजीतपुरा बज्जू 34 गांव विस्थापित नाथू दादा"
- "site:facebook.com "34 गाँव" महाजन फायरिंग रेंज"
- "भोजरासर गांव महाजन फायरिंग रेंज facebook.com"
- "34 गांव महाजन फायरिंग रेंज गांव भ्रमण reel" (restricted to facebook.com)
- "नाथू दादा धोरा खिंयाणा मेला facebook" / "Nathu Dada Ka Diwana facebook खिंयाणा महाजन"
- "Dinesh Beniwal instagram 34 गांव महाजन"

**Returned nothing usable (pure noise — other-village namesakes, unrelated pages, generic "old village" content):**
- All per-village-name + "facebook.com"/"reel" queries for: kumbhana, thoiya, manera, duder, chidasar, kolana, nathor, berawala, khanisar, motlai, bhojrasar (as standalone village query), khiyana (as standalone village query)
- "34 गांव एरिया" facebook
- "पुराणा 34 गाँव" / "पुराने 34 गांव" (both scripts)
- "#34gaav facebook OR instagram"
- "#nathudada instagram", "#khiyana instagram reel" (returned unrelated same-spelled accounts)
- "कानोलाई पीर बाबा धाम मेला बीकानेर", "डाडा पम्मा जी महाराज कुम्भाणा facebook", "कुम्भाणा गढ़ होली facebook"
- "महाजन फील्ड फायरिंग रेंज विस्थापित विकास समिति" (org name — no FB/IG presence found; only press results)
- "Bharat Speaks" facebook 34 गांव / "Bharat Speaks facebook page 34 गांव विस्थापित" (the known Bharat Speaks page itself did not surface via web search — must be found via direct Facebook navigation)
- Searches on known creators Chhaganlal Jakhar, Rameshwer Godara, Mukesh Jaat Phalwan, Sunil Beniwal — no matching accounts surfaced
- "Khajuwala Pugal Chhatargarh IGNP 34 गांव विस्थापित परिवार"
- "34 gaon mahajan old village visit vlog" (youtube.com) — only generic unrelated village vlogs

## Recommendation / सुझाव

Given the very low recall from general web search, the most productive next step is **direct in-platform search** (a human logged into Facebook/Instagram searching Hindi terms like "34 गांव", "पुराणा 34 गाँव", "#khajuwala", "#nathudada", and visiting the already-known creators' profiles/followers/tagged-in lists) rather than further iterations of this external web-search approach. This collect pass should be treated as a low-yield first pass; the bulk of real reels almost certainly exist but are outside what this tool's search index reaches.
