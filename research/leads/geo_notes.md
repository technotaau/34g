तैयार: TechnoTaau Team शोध सत्र, 25 सितंबर 2026

# Geo track: नक्शे, स्थान-नाम datasets और गांवों की जगह

Track files: `research/leads/geo.jsonl` (19 records), `research/leads/files/geo/` (12 files, 8.4 MB), जिनमें `geo_points.geojson` (427 points) भी है।
Polygon test हर जगह OSM way 412765540 से किया गया (`data/mffr_range_polygon.geojson`, ray-casting)। Census नक्शों से मिले points गांव की **ज़मीन** की जगह बताते हैं (polygon centroid या label), **आबादी (abadi) की जगह नहीं**।

## सबसे बड़ी खोजें (ranked)

1. **1961 census tehsil map पर range polygon ठीक 32 गांवों को घेरता है।**
   District Census Handbook Bikaner 1961 (censusindia NADA catalog 29011, PDF page 266, "Teh. Lunkaransar") में हर गांव की सीमा (polygon) बनी है और उस पर location code लिखा है। Unpopulated गांवों के code box में हैं। मैंने इसे 54 control points से georeference किया (affine, median residual 2.0 km) और OSM polygon ऊपर रखा (`files/geo/overlay_osm_polygon_on_census1961_tehsil_map.jpg`)। Range की सीमा पुरानी गांव-सीमाओं के साथ-साथ चलती है। नतीजा:
   - 27 गांवों के polygon का 85-100% हिस्सा range के अंदर है: 6, 7, 15, 16, 17, 18, 21, 23, 25-31, 33, 41-50 और 82 (1961 में 82 = Motolai)।
   - छोटे box वाले टुकड़े 19, 20, 22, 32 और 40 भी अंदर हैं।
   - कुल 32 गांव बनते हैं। यह वही सूची है जो 1991 तक census से ग़ायब होती है (docs/census-village-list-findings.md)।
   - **बिरमाणा (1961 code 81) का लगभग 42% हिस्सा range के अंदर है।** बाकी गांवों का 0-15% है, जो georef की ±2 km गलती के भीतर है।
   - इससे "33 गांव = 32 पूरे गांव + बिरमाणा का हिस्सा" वाली बात को नक्शे से सहारा मिलता है। यह सबूत है, अंतिम फैसला नहीं; अंतिम फैसला भूमि-अवार्ड से होगा।
   - Code का मिलान: 1961 के codes 1-79, 1971 के codes के बराबर हैं। 80 के बाद 1961 का code = 1971 का code + 1। 1961 में 80 Khokhrana, 81 Birmana, 82 Motolai, 83 Lakhawar, 84 Ajeetmana और 85 Karnali है (`files/dch_bikaner_1961.txt`, लगभग line 4390-4430 और 18370-18520)।
2. **1971 census Map No. 2.3 "Lunkaransar Tehsil"** (DCH 1971 Part X-A/B, catalog 28480, PDF p.177; p.178 पर amenities map)। इसमें हर राजस्व गांव का नाम, code, जनसंख्या का dot और गांव की सीमा है। इसी से वे गांव locate हुए जो 1955 के AMS नक्शे पर नहीं छपे थे: चिड़ासर (Cheedasar 29), बेरावाला (Beranwala 17), लिखमीसर (42), कंकरालियो (Kankroliya 47) और तीनों "रेख" टुकड़े (19, 20, 22)। दोनों census नक्शों की जगहें आपस में 0.3-3 km के भीतर मिलती हैं (`files/geo/census_map_village_locations.csv`)।
3. **पांच अनसुलझे नाम (नाथौर, माच्छरांवाली, टिडासर, कचराणा, चकड़ो) किसी भी नक्शे या dataset में नहीं मिले।** जांचे गए स्रोत: 1961 और 1971 के census नक्शे, AMS की चारों sheets, NGA GNS (पूरे भारत में नाम-pattern search), GeoNames, OSM (Overpass regex और Nominatim) और Wikidata। इसलिए ये राजस्व गांव नहीं थे। ये ढाणियों या बास के नाम, या बाद के या बोलचाल के नाम होने चाहिए। नीचे हर नाम के लिए सबसे करीबी सुराग दिया है।
4. **OSM polygon का क्षेत्रफल census से मेल खाता है।** OSM polygon 135,996 ha है। Census में 1991 का आंकड़ा 136,411 ha और 2011 का 136,406 ha है (फ़र्क −0.3%)। 2011 census tehsil map (DCH 2011 Part XII-A, catalog 1022, PDF p.112) पर range एक खाली "गांव" 069202 के रूप में दिखता है, और नक्शे पर नापा गया उसका क्षेत्रफल लगभग 135,750 ha है। पूर्वी और दक्षिणी सीमा OSM से मिलती है। पश्चिमी सीमा कई km अलग है, जो शायद tehsil नक्शे का खिंचाव है (`files/geo/overlay_osm_polygon_on_census2011_tehsil_map.jpg`)।
5. **AMS NH 43-9 "Mailsi" sheet उतार ली** (`files/geo/ams_nh43-09_mailsi.jpg`)। Range polygon इस sheet में घुसता ही नहीं (73.5E पर polygon की सबसे उत्तरी latitude 28.993N है)। इसलिए "गायब sheet में बचे गांव होंगे" वाली संभावना ख़त्म होती है। चारों AMS sheets पढ़ने के बाद भी चिड़ासर, बेरावाला, लिखमीसर, कंकरालियो और रेख टुकड़ों के नाम किसी sheet पर नहीं छपे हैं।

## हर गांव पर नया क्या मिला

Best location = AMS abadi (जहां है), नहीं तो 1961 और 1971 census नक्शों का औसत। "ज़मीन अंदर" = 1961 polygon का वह हिस्सा जो OSM polygon के अंदर है।

| slug | census नाम (code 1971) | best lat, lon | स्रोत | range में? | ज़मीन अंदर | भरोसा |
|---|---|---|---|---|---|---|
| chidasar | Cheedasar (29) | 28.9687, 73.5543 | 1961 + 1971 census नक्शे | अंदर, किनारे से 3.4 km | 93% | medium (±2-3 km) |
| berawala | Beranwala (17) | 28.7083, 73.4900 | 1961 + 1971 | अंदर, 10.8 km | 100% | medium |
| likhmisar | Likhmisar (42) | 28.9434, 73.6608 | 1961 + 1971 | अंदर, 8.0 km | 100% | medium |
| kankraliyo | Kankroliya (47) | 28.8822, 73.6514 | 1961 + 1971 | अंदर, 8.4 km | 100% | medium |
| kolana? | Rekh Chudana (19, unpopulated, 969 acre) | 28.6806, 73.5930 | 1961 box + 1971 circle, लाडेरा के पास | अंदर, 1.9 km | छोटा टुकड़ा | जगह medium, "कोलाणा = चूडाणा" low |
| bhanabasti | Rekh Bhanabasti (20) | 28.6886, 73.6077 | 1961 + 1971 | अंदर, 1.0 km | छोटा टुकड़ा | medium |
| ajeetwana | Rekh Ajeetmana (22) | 28.6560, 73.5883 | 1961 + 1971 | अंदर, 1.2 km | छोटा टुकड़ा | medium |
| hindor | Hindor (30) | 28.9679, 73.5988 (AMS); census नक्शे 28.973, 73.606; OSM locality 28.9666, 73.6005 | तीनों मेल खाते हैं | अंदर, 4.3 km | 100% | high |
| kumbhasar | Kumbhasar (43) | 28.9267, 73.6746 (AMS "Kumbasar"); census 28.926, 73.680 | मेल खाते हैं | अंदर, 7.6 km | 100% | high |
| rina | Raimalwali @ Reena (16) | 28.6565, 73.4654 (AMS "Raemalwali") | census नक्शे पुष्टि करते हैं | अंदर, 7.0 km | 99% | high |
| dhannasar | Kummana की बास (18) | कुम्भाणा की ज़मीन का centroid 28.7295, 73.5814 | 1961 + 1971 | अंदर | 100% | बास की ठीक जगह अज्ञात |
| birmana | Beermana (1971 का 80, 1961 का 81) | 28.5917, 73.5131 (AMS, सीमा से 0.4 km अंदर); OSM 28.5925, 73.5187 (0.1 km बाहर) | 1961 polygon | सीमा पर | 42% | medium |
| lakhor-chhoti | Lakhaur Chhoti (32) | 29.0024, 73.6655 (AMS "Lakhor Khurd"); GNS/GeoNames "Lakhor Chhoti" 29.0007, 73.6770 | | अंदर | छोटा टुकड़ा | high |
| jagatsinghpura | Jagatsinghpura (40, 1961 में unpopulated) | 28.925, 73.74 (AMS "Jagsingpura") | | अंदर | छोटा टुकड़ा | high |

बाकी 20 गांवों की जगह AMS से पहले से तय है। 1961 नक्शे पर उनकी ज़मीन का 85-100% हिस्सा अंदर है (पूरी सूची `census_map_village_locations.csv` में)।

**Namesakes, जिनसे भ्रम हो सकता है:**
- Hindor नाम का दूसरा गांव 29.0944, 73.8660 पर है (सूरतगढ़ तहसील)। यह GeoNames, GNS और OSM में है और range के बाहर है।
- Likhmisar Utrada/Dikhnada (27.90N, श्रीडूंगरगढ़)।
- Kumbhasar (नोखा, 27.535N) और Kumbhasar (सिरसा, हरियाणा)।
- Dhanasar (29.18N, 74.34E)।
- Nathusar (1951 की सूची में; 2011 code 069333; OSM 28.3803, 73.9439)। यह आज भी मौजूद है और range के बाहर है।

### पांच अनसुलझे नाम: सबसे अच्छा सबूत

| नाम | सबसे करीबी सुराग | जगह | range में? | भरोसा |
|---|---|---|---|---|
| नाथौर (Nathor / नाथुवास) | OSM hamlet "Nathuwas" (node 7335802789) | 28.5073, 73.2631 | बाहर, 9.9 km दक्षिण-पश्चिम | low। पुनर्वास की ढाणी भी हो सकती है और कोई और गांव भी |
| माच्छरांवाली | कहीं कुछ नहीं मिला (census 1961/71 नक्शे, AMS, GNS, GeoNames, OSM, Wikidata) | — | — | — |
| टिडासर | कहीं कुछ नहीं मिला | — | — | — |
| कचराणा | सिर्फ़ ध्वनि-समानता: Khokharana / Khonkharana (1961 का 80, 1971 का 79, आज मौजूद) | OSM 28.5511, 73.5711 | बाहर, 6.5 km | low |
| चकड़ो | Chak Jor / चकजोहड़ (1971 का 35, unpopulated, 4,889 acre) | 1961 label 28.965, 73.779; OSM village 28.9829, 73.8120 | 1961 नक्शे पर polygon range के ठीक बाहर; OSM 1.4 km बाहर | low |

एक और सुराग: 1955 के AMS NH 43-14 पर कुम्भाणा की ज़मीन के भीतर एक दूसरी बस्ती "Barjansar" छपी है (28.7633, 73.5604, अंदर, किनारे से 10.4 km)। यह "बास धन्नासर" हो सकती है, पर यह पुष्ट नहीं है (low)। इसी तरह AMS पर "Amarpura" (Dooder की ज़मीन पर) और "Dhani Duder" भी हैं। यानी इन गांवों की अपनी ढाणियां थीं, और अनसुलझे नाम शायद ऐसी ही ढाणियों के हैं।

## Georeferencing notes (हर नक्शे का)

- **AMS NH 43-9 Mailsi (5000x3930 px, 1:250,000):** neatline corners TL(287,278)=72°E/30°N, TR(4183,284)=73.5°E/30°N, BL(266,3258)=72°E/29°N, BR(4201,3261)=73.5°E/29°N। Bilinear interpolation। 1 px ≈ 37 m। GNS के 5 points से जांच की: गलती 0.2-0.5 km।
- **AMS NH 43-14 Sardarshahr (5000x3779):** TL(337,256)=73.5/29, TR(4224,248)=75/29, BL(327,3194)=73.5/28, BR(4250,3184)=75/28। repo के 34 AMS points इस georef से symbols पर ठीक बैठते हैं।
- **AMS NH 43-13 Bikaner (5000x3947):** TL(314,315)=72/29, TR(4204,308)=73.5/29, BL(299,3267)=72/28, BR(4232,3259)=73.5/28।
- **1971 Map 2.3 (rotated file, 3401x2561 px):** 55 control points (`georef_control_points.csv`)। Global quadratic RMS 2.8 km; local 7-point weighted affine, leave-one-out median 2.4 km, p90 4.6 km। Map note: "population size dots do not represent actual abadi sites"।
- **1961 p.266 (300 dpi, 3152x3906 px):** printed graticule ticks top 73°30'=x958, 73°45'=x1670, 74°00'=x2380; right 28°45'=y1819, 28°30'=y2568। Ticks से गलती 7.6 km (median) आती है, यानी ये ticks भरोसेमंद नहीं हैं। 54 control points (village polygon centroid बनाम AMS/GNS/OSM abadi) से affine: median 2.0 km, RMS 2.6 km। Polygon centroid flood-fill से निकाले।
- **2011 DCH p.112 (250 dpi, 2068x2924):** 23 control points, affine RMS 1.9 km।

## जो नहीं पहुंच पाए (human के लिए URLs)

- **Soviet General Staff maps:** http://maps.vlasenko.net/smtm100/ पर 503/timeout आया, और download.maps.vlasenko.net resolve नहीं हुआ। loadmap.net ने "Forbidden" दिया। mapstor.com पैसे वाली दुकान है। चाहिए sheets: **1:100k H-43-100, H-43-111, H-43-112, H-43-123, H-43-124**; **1:200k H-43-XXVI, H-43-XXXII**। इन पर गांव Cyrillic में होंगे, और 1:100k पर ढाणियां भी हो सकती हैं। अनसुलझे नामों के लिए यही सबसे उम्मीद वाला स्रोत है।
- **web.archive.org:** इस मशीन से हर request पर connection reset हुआ। इसलिए Wayback copies नहीं देखी जा सकीं।
- **Wikimapia:** https://wikimapia.org/#lat=28.80&lon=73.55&z=11 पर JS-cookie bot check है और API key चाहिए। किसी व्यक्ति को browser में इलाका देखना होगा।
- **Survey of India** (https://onlinemaps.surveyofindia.gov.in/, Nakshe): login चाहिए। 1:50k sheets degree sheet 44H और 44G में हैं।
- **USGS EarthExplorer** (CORONA/KH-9): search के लिए account चाहिए। Area: 28.55-29.04N, 73.30-73.80E।
- **Bhuvan:** WMS host जवाब नहीं दे रहा, और download के लिए login चाहिए।
- **1981 DCH p.153:** tehsil map scan नहीं हुआ, पन्ने पर सिर्फ़ शीर्षक है।

## अगले कदम

1. Soviet 1:100k sheet H-43-111 और H-43-112 किसी और मशीन या browser से उतारें, और Cyrillic नाम पढ़ें। Transliteration के उदाहरण: Натхор/Нáтхор, Мачхранвали, Тидасар, Качрана, Чакдо।
2. बुज़ुर्गों को `census_map_village_locations.csv` और 1961 overlay नक्शा दिखाएं, और पूछें कि पांच नाम किस गांव की ढाणी थे (जैसे Barjansar, Amarpura, Dhani Duder)।
3. भूमि-अवार्ड (RTI) में बिरमाणा का अधिग्रहित रकबा देखें। 1961 नक्शे के हिसाब से बिरमाणा का लगभग 42% हिस्सा अंदर आता है।
4. कोई USGS account बनाकर CORONA frames (1965-72) की entity IDs दर्ज करे। उन पर हर abadi दिखेगी, और तब census नक्शों की ±2-3 km वाली जगहें पक्की हो सकेंगी।
5. Census 1981 की छपी handbook (Part XIII-A) का tehsil map census library से मंगवाएं।
6. Wikidata पर 32 गांवों के items बनाए जा सकते हैं, पर यह तभी करें जब project फैसला करे।
