# social2: सोशल और कम्युनिटी प्लेटफॉर्म sweep (YouTube harvest के अलावा)

तैयार: TechnoTaau Team शोध सत्र, 25 सितंबर 2026

Records: `research/leads/social2.jsonl` (120 records). Files: `research/leads/files/social2/` (12 WebP photos, 640 px, कुल 0.8 MB; कोई video नहीं)।
`social_web.jsonl` और `youtube.jsonl` (183 IDs) में पहले से मौजूद URL दोबारा नहीं जोड़े गए।

## तरीका और गिनती

- WebSearch: लगभग 99 queries (Hindi, English, romanised; site: और allowed_domains के साथ Facebook, Instagram, X, Threads, ShareChat, Moj/Josh, Koo, Pinterest, Quora, Dailyhunt, Telegram, Blogspot/WordPress/Medium, Jatland, Wikimapia, Spotify)।
- YouTube: `ytsearch20:` की 104 queries (5 unresolved नाम, हर गांव का नाम, Nathu Dada, Pamma ji, Pir Baba Kanolai, सुलेरा, रणजीतपुरा आदि), 8 playlist searches, 5 seed channels के playlists और community posts, 6 नए channels की पूरी upload list।
- Dailymotion public API: 24 terms. JioSaavn public API: 33 searches + artist page. SoundCloud (`scsearch30:`): 14 terms. Telegram `t.me/s/<channel>?q=`: 2 channels x 9 terms. Josh tag pages: 7।
- कुल लगभग 350 queries।
- ~70 YouTube videos का पूरा metadata (upload date, description) लिया गया; उसके बाद YouTube ने yt-dlp को "Sign in to confirm you're not a bot" देना शुरू किया। इसे bypass नहीं किया; बाकी 30 records में date खाली है (title/channel oEmbed से भरे)।

## सबसे बड़ी खोजें (महत्व के क्रम में)

1. **Jatland: Dhatarwal "12 गांव" का वंश-समूह (search snippet से, page blocked)।** https://www.jatland.com/home/Dhatarwal (HTTP 403, सिर्फ WebSearch के सारांश पढ़े गए, page खुद नहीं देखा)। सारांशों के अनुसार नाथू धतरवाल (जन्म VS 1380 = 1323 ई., धात्री, सुजानगढ़) बड़ेरण (लूणकरणसर) आकर बसे और Asoj badi 9 VS 1444 (1387 ई.) को सिंध के हमलावरों से लड़ते हुए मरे। उनके परिवार के नाम पर बसे गांव: **कुम्भाणा** (बड़े बेटे कुम्भा), **खींयेरा/खियाणा** (दूसरे बेटे खिंया), **ठोईयां** (बेटी थोइली, बेनीवालों में ब्याही), **भानाबस्ती** (ताऊ भाना), चूड़ाना (भाना के छोटे भाई चूड़ा), **अजीतमाना** (अजीता), **नाथौर/नाथूवास** (नाथू की याद में)। अगर पुष्टि हो तो 34 में से 6 गांव एक ही धतरवाल समूह हैं, और "Nathor = Nathuwas" alias को सहारा मिलता है। मौत की तिथि (आसोज बदी 9) और मेले की तिथि एक ही है। विश्वास: मध्यम-कम (snippet only)। अलग pages: /Thoiya, /Kumbhana, /Nathuwas, /Chudana (सभी blocked)।
2. **नाथू दादा मंदिर, खियाणा (MFFR के अंदर): दो समर्पित YouTube channels जो harvest में नहीं थे।** "NATHU DADA TEMPLE (MFFR)" https://www.youtube.com/channel/UCWUv4r2QQnqzgJpwyqbZ8DA (लगभग 76 uploads, 2019-10-05 से 2025-09-16, एक भी youtube.jsonl में नहीं) और "Nathu Dada Studio" https://www.youtube.com/channel/UCGwoWYcumsF0-HeF9L6idkQ (38 videos + 77 shorts, 2022-2023 मेले)। इसी channel का video HSLIjaAMyg8 दिखाता है कि **रणजीतपुरा** (विस्थापितों का बसाव क्षेत्र) में भी नाथू दादा का मंदिर है, और rISfho6UUr4 / uLDr8UN1f30 सोनियासर (श्री डूंगरगढ़) में नया मंदिर।
3. **nathudada.wordpress.com (2016-12-28)** https://nathudada.wordpress.com/2016/12/28/3/ : "नाथू दादा जी की देवली ... तहसील लूणकरणसर के गाँव **सूलेरा के पास खीयाणा** मे महाजन फील्ड फायरिंग रेंज में ... भव्य मन्दिर का निर्माण धत्तरवाल समुदाय द्वारा ... आसोज महीने की कृष्ण पक्ष नवमी को प्रतिवर्ष मेला"; और देवदास रांकावत की राजस्थानी जीवनी **"मुळकती मौत कळपती काया"** का ज़िक्र। लेखक की पुष्टि: https://rajasthanibooks.blogspot.com/2009/09/blog-post.html (देवदास रांकावत: मुळकती मौत, गांव थारै नांव आदि)।
4. **Rssuthar Jaisalmer की playlist "कानोलाई गाँव जो अब मिलेट्री ऐरिया में आ चूका है (कन्हळाई गाँव)"** https://www.youtube.com/playlist?list=PLqEtSu6muiGSoQL6NnH4y4XWJkwyW3BRI : 89 videos (76 नए)। कानोलाई के सुथार (धामु) परिवार आज रामनगर (लूणकरणसर), ढाणी 10 KYD / 32 हैड खाजूवाला, 6 व 9 DKD रावला, महादेववाली, किशन नगर में दिखते हैं; "भूरिया बाबा मंदिर, South Camp महादेववाली, Mahajan field firing range Military Area" (20Dj1Nd3Gyw)। Seed channel होने के बावजूद playlist-level समूह harvest में नहीं आया। इसी channel की "नाथू दादा धोरा मन्दिर खींयाणा" playlist (20 videos, 11 नए, 2018-10-03 और 2019-09-24 की shooting)।
5. **कानोलाई के दो photo-posts (Dinesh Beniwal, YouTube community, लगभग दिसंबर 2025)**: "खारिया कुआँ कानोलाई गाँव में" https://www.youtube.com/post/UgkxPKlz314pNynMw9gxJmCR2ty-283MxUIn और "पीर बाबा धाम कानोलाई" https://www.youtube.com/post/Ugkx6-KkPf07csk95oVq0zT-6LWTeeuZ8xeo । 12 photos सहेजी: `files/social2/ytpost_dineshbeniwal_kanolai_*.webp` (लाल पत्थर की जगत वाला गहरा कुआँ; हरे रंग का पीर बाबा थान, हरे झंडे, "...जी महाराज कानोलाई..." लिखा)।
6. **JioSaavn पर Ajay Thori के खियाणा गीत**: "Khiyana Ri Dharti Mathe Dado Dhum Machave" (2023-08-23), "Khiyana Ra Raja" और "Khiyana Ra Lal" (2024-09-27), कुल 9 नाथू दादा tracks (https://www.jiosaavn.com/artist/ajay-thori-songs/dDMYd8tdFj0_)। इनका YouTube रूप r41hVMsN3mk (40k views)।
7. **सहीराम दुसाद (पूर्व भाजपा देहात जिलाध्यक्ष) MFFR से विस्थापित**: Bhaskar खबर की blog copy (सितंबर 2020) https://24hoursnewsforindian.blogspot.com/2020/09/blog-post_617.html : "महाजन फील्ड फायरिंग रेंज के लिए जब जमीन एक्वायर की जा रही थी तो उसी के दायरे में उनका मूल आवास भी आ गया ... उन्होंने अपना मूल आवास सत्तासर को बनाया"। मूल गांव का नाम नहीं दिया।
8. **Younish Ali Parihar का video** 6mEtnzIyfhQ (2024-05-13): "1984 मे चोंतिस गाँव खाली करवा कर दिए ओर 50 गांव अभी भी बाकी है जिसकी जमीन हमारी आर्मी के हक में है" (बिना सबूत का दावा; 1992-96 विस्तार की ओर इशारा हो सकता है)।

## 33 बनाम 34, और गांव-सूची पर असर

- इस track में 33-vs-34 पर कोई नया दस्तावेज़ नहीं मिला। सोशल media में हर जगह "34 गांव / चोंतिस गाँव" और "1984" (कभी 1984-85) ही बोला जाता है; Nathu Dada Studio "34 गाँवों वाला एरिया" / "एरिया वाला मेळा" शब्द इस्तेमाल करता है।
- Unresolved नामों पर: **नाथौर** के लिए Jatland snippet "Nathor (Nathuwas) - नाथू धतरवाल की याद में बसाया" मिलता है (ऊपर #1)। माच्छरांवाली, टिडासर, कचराणा, चकड़ो: YouTube, WebSearch, Dailymotion, JioSaavn में कोई सही hit नहीं (Tidasar = ओडिशा के Soura videos, Chakdo = गुजराती छकड़ा, Machhranwali = पाकिस्तानी channel)।

## हर गांव पर नया क्या मिला

- **खियाणा / खींयाणा / खिंयारा**: मंदिर "सूलेरा के पास", MFFR के अंदर (nathudada.wordpress); मेला आसोज बदी 9; धतरवालों का मूल स्थान (Jatland snippet)। 2017 (ojm6kdAEbx0) से 2025-09-25 (gl5yOJos80c) तक हर साल के मेले/जागरण के video; कुश्ती दंगल की परंपरा (Rssuthar playlist, Nathu Dada Studio boF5O2Lz1js "विदेशी पहलवानों की कुश्ती")। 2022 मेले में सरपंच महेंद्र धतरवाल का भाषण nVvq0qY6bGQ (देखना बाकी)। "temple on satellite" short V6nUH7eCCpE से मंदिर की जगह निकाली जा सकती है।
- **कानोलाई / कन्हळाई**: पीर बाबा धाम और खारिया कुआँ की 12 photos (Dinesh Beniwal posts)। सुथार (धामु) परिवारों का बसाव: रामनगर (लूणकरणसर), 10 KYD खाजूवाला, 6/9 DKD रावला, महादेववाली (Rssuthar playlist; विश्वास मध्यम, titles पर आधारित)। रामनगर की "चौपड़ जैसी 40-60 फिट चौड़ी गलियां" (hHiLxT6X2mo) : योजनाबद्ध पुनर्वास गांव हो सकता है, जांचें।
- **कुम्भाणा**: Jatland snippet: नाथू के बड़े बेटे कुम्भा के नाम पर। indianrajputs.com: बीका राठौड़ों की रतनसिंहोत शाखा का ताजीमी ठिकाना, Double Tazim, महाजन के बाद दूसरा; महाजन पट्टे के 63 गांवों में से 9 कुम्भाणा पट्टे में (https://www.indianrajputs.com/view/mahajan)। "डाडा पम्मा जी": श्री विजयनगर (श्रीगंगानगर) का "डाडा पम्मा राम मेला/गुरुद्वारा" नाम से मिलता है, पर कुम्भाणा से संबंध का कोई सबूत नहीं; शायद अलग परंपरा (दर्ज नहीं किया)।
- **ठोईयां**: Jatland snippet: नाथू की बेटी थोइली के नाम पर, जो बेनीवालों में ब्याही।
- **भानाबस्ती**: Jatland snippet: नाथू के ताऊ भाना के नाम पर (पहली बार इस गांव के बारे में कोई बात मिली)।
- **अजीतमाना / अजीतवाणा**: Jatland snippet: अजीता के नाम पर। YouTube -ugtbbLlz1c में आज का बसा हुआ "अजीतमाना, लूणकरणसर" दिखता है : पुराना गांव है या नया, पक्का नहीं।
- **नाथौर / नाथूवास**: ऊपर देखें।
- **खानीसर**: "पुराना गांव खानीसर जाने का रास्ता" wSeKsKcf3aI (2023-08-01, channel बीकानेर दर्शन, 6 views)।
- **रणजीतपुरा** (बसाव क्षेत्र): नाथू दादा मंदिर HSLIjaAMyg8।
- **मेऊसर, बिरमाणा**: मिले hits शायद नामराशि गांव हैं (मेऊसर में स्कूल; "Chak 4 DWM Birmana")। विश्वास कम, सिर्फ़ भ्रम से बचने के लिए दर्ज।
- बाकी गांव (भोजरासर, मोटलाई, मणेरां, दुदेर, चिड़ासर, कोलाणा, बेरावाला, धन्नासर, रिणा, मोटासर, भुंवाला, देवासर, कंकरालियो, लखोर, जागोर, रामपुरा, दुदेरिया, हाथूसर, हिन्दोर, लिखमीसर, कुम्भासर): इस track में youtube.jsonl से आगे कुछ नया नहीं।

## बार-बार पोस्ट करने वाले creators (seed_channels.json के उम्मीदवार)

| creator | platform / id | क्या | सुझाव |
|---|---|---|---|
| NATHU DADA TEMPLE (MFFR) | YouTube UCWUv4r2QQnqzgJpwyqbZ8DA | खियाणा मंदिर, 2019-2025, ~76 uploads, रणजीतपुरा मंदिर | जोड़ें |
| Nathu Dada Studio | YouTube UCGwoWYcumsF0-HeF9L6idkQ | मेला 2022-23, "34 गाँवों वाला एरिया" | जोड़ें |
| Rssuthar Jaisalmer (पहले से seed) | playlists PLqEtSu6muiGSoQL6NnH4y4XWJkwyW3BRI, PLqEtSu6muiGRGqYuM5H28o7jemfyq78By | कानोलाई परिवार, नाथू दादा धोरा | playlists भी harvest करें |
| Dinesh Beniwal (पहले से seed) | YouTube /posts | कानोलाई photo posts | community posts भी पढ़ें |
| PRADEEP DHATARWAL OFFICIAL | YouTube UCNSIzTcwgw-ZY0svrFACxog | नाथू दादा जीवन कथा, मेला 2025 | जोड़ें (कम मात्रा) |
| Kumawat sound lunkaransar | YouTube UC569Vz-euNAfTIBgd_1qXKg, playlist PLsX9-CclQFuwdqP_TH_LKP8KTAsmoZo1Y | 2023 जागरण की 21 recordings | playlist जोड़ें |
| SINGER AJAY THORI | YouTube UCcxe8Y6TGNxiM-KHKqgleZw; JioSaavn artist dDMYd8tdFj0_ | खियाणा गीत | वैकल्पिक |
| Diary Of Indiaa | YouTube UC-RyqLHtGxmEcZG1y13-MUw | नाथू दादा इतिहास (20k views x2) | वैकल्पिक |
| New Anjani Music / MR GODARA MUSIC / MKB Music | UC0eEftij6dWbLuG5pFOQBvQ / UCWX318k-2xXmJ3UWJI8_afA / UC72HpHHJljzvuTR1VCxzYIw | महावीर सांखला के खियाणा भजन | नहीं (सामान्य भजन labels); सिर्फ़ search से |
| Younish Ali Parihar | UCeZFaFcIx_EHfIcluHaME8g | 1 video (34 गांव) | नहीं |

## जो नहीं पहुंच पाए (एक इंसान browser में खोले)

- Jatland (HTTP 403 to curl और WebFetch): https://www.jatland.com/home/Dhatarwal , /Thoiya , /Kumbhana , /Nathuwas , /Chudana , /Lunkaransar । **सबसे ज़रूरी**: Dhatarwal page का पूरा text और उसकी संदर्भ-पुस्तक।
- Facebook: place page https://www.facebook.com/pages/Field%20Firing%20Range%20Mahajan/283917615793054/ (login)। Facebook/Instagram की site-search से गांवों के reels लगभग नहीं मिलते; सिर्फ़ news/army posts।
- Instagram topic pages https://www.instagram.com/popular/mahajan-field-firing-ranges/ और /popular/mahajan-firing-range/ (script से load; HTML में posts नहीं)।
- Wikimapia https://wikimapia.org/8672878/MAHAJAN-FIRING-RANGE (cookie/JS bot check, bypass नहीं किया)।
- Reddit (search.json 403, old.reddit login, pullpush agents के लिए मना), Quora (403), Medium (403)।
- Wayback Machine (web.archive.org tunnel बार-बार बंद) : Koo archive और X के पुराने posts नहीं देख पाए। nitter.net नहीं खुला।
- Josh/Moj/ShareChat/Chingari: सिर्फ़ app में; web पर tag pages खाली shell (#nathudada, #khiyanadham, #34gaon, #34gaav)।
- YouTube: ~30 videos की upload date (bot check के बाद)। TGStat channel search (script-only)।

## अगले कदम

1. किसी को Jatland Dhatarwal page खोलकर "12 गांव" की सूची, हर गांव का संस्थापक और उद्धृत पुस्तक नोट करनी है; फिर villages.json में नाथौर = नाथूवास और भानाबस्ती/अजीतमाना/ठोईयां के संस्थापक की बात (स्रोत सहित) जोड़ने का फैसला।
2. देवदास रांकावत की "मुळकती मौत कळपती काया" की प्रति ढूंढें (राजस्थानी साहित्य अकादमी / बीकानेर पुस्तकालय); book track को सौंपें।
3. seed_channels.json में ऊपर वाले 2-3 channels जोड़ें और harvester को playlists और /posts भी पढ़ना सिखाएं।
4. nVvq0qY6bGQ (सरपंच महेंद्र धतरवाल भाषण), RKE03AkwQdQ / UAgSr2c5Rpw (इतिहास), V6nUH7eCCpE (satellite) को सुनकर/देखकर notes बनाएं।
5. Rssuthar Jaisalmer से संपर्क कर कानोलाई के बुजुर्गों (रामनगर, 10 KYD) से oral history; सहीराम दुसाद के परिवार/साथियों से उनका मूल गांव पूछना (diaspora track)।
6. Facebook/Instagram/ShareChat/Josh पर logged-in इंसान: #nathudada, #khiyanadham, "34 गांव", "एरिया वाला मेळा", कानोलाई, कुम्भाणा खोजे।
7. YouTube bot check हटने पर बाकी ~30 videos की date भरें (`yt-dlp --skip-download --dump-json`, बिना cookies)।

## Personal data

7 records `personal_data: true, privacy_review: pending`: indianrajputs Kumbhana (परिवार के नाम), Rssuthar के कानोलाई videos Eu87mykSDJI, 2iStTK3HAXk, qfx8fErumPk, lLCFZWslqWY, कानोलाई playlist, बिरमाणा playlist (निजी व्यक्तियों के नाम/ढाणी titles में)। किसी का फोन नंबर या पता अलग से दर्ज नहीं किया (कुछ YouTube descriptions में singers के नंबर हैं; उन्हें records में नहीं उतारा)।
