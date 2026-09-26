# आवाज़ वाला सहायक: Gemini Live, ElevenLabs और Sarvam की तुलना

तैयार: TechnoTaau Team शोध सत्र, 26 सितंबर 2026

**इस्तेमाल का मामला:** हिंदी (और बागड़ी) में realtime voice assistant, जो (क) बुज़ुर्गों से बात करके विस्थापित गांवों की यादें दर्ज करे, और (ख) हमारे जांचे हुए तथ्यों (system prompt / tool call से दिए गए) से सवालों के जवाब दे। शुरुआती बजट लगभग शून्य।

**तरीका:** नीचे हर संख्या और उद्धरण आज (26 सितंबर 2026) खोले गए official पन्नों से है। उद्धरण अंग्रेज़ी में ज्यों के त्यों रखे हैं। जो बात किसी official पन्ने पर नहीं मिली, वह अंत में "जो जांचा नहीं जा सका" में है; वहां कोई अंदाज़ा नहीं लिखा गया। जहां हमने ख़ुद हिसाब लगाया है, वहां "हमारा हिसाब" लिखा है।

---

## 1. एक नज़र में तुलना

| पहलू | Google Gemini Live API | ElevenLabs Agents | Sarvam AI |
|---|---|---|---|
| **मुफ़्त शुरुआत** | Free Tier: Live models के लिए "Free of charge" (rate limit AI Studio में दिखती है, पन्ने पर संख्या नहीं) | Free plan: "15 minutes of calls included" हर महीने | "₹100 worth of free credits" signup पर, "Credits are universal and never expire" |
| **Paid दाम (तुलना लायक)** | gemini-3.8-live: audio input "$0.005/min", audio output "$0.018/min" | "$0.080" प्रति अतिरिक्त call-minute + LLM अलग ("Based on usage and varies by model") | STT "₹30" प्रति घंटा; TTS (Bulbul v3) "₹30" प्रति 10K अक्षर; Voice Agents का प्रति-मिनट दाम official पन्ने पर **नहीं मिला** |
| **हमारा हिसाब: एक घंटे की बातचीत** | यादें (सहायक 20% बोले): ≈ $0.52; सवाल-जवाब (सहायक 50% बोले): ≈ $0.84; ऊपर से थोड़े text tokens | $4.80 + LLM का ख़र्च | अपना pipeline जोड़ें तो मोटे तौर पर ₹60-115 (TTS अक्षर-गिनती अनुमान पर; नीचे देखें) |
| **Realtime speech-to-speech** | हां, native audio ("audio-to-audio models") | हां, पर pipeline: Scribe (STT) + LLM + TTS | Voice Agents: हां, "ASR → LLM → TTS loop" |
| **Barge-in (बीच में टोकना)** | हां | हां ("Configure turn-taking, interruptions") | हां (`user_interrupt` event) |
| **Tool / function calling** | हां (3.8 Live में async function calling) | हां (client, webhook, MCP tools) + Knowledge Base/RAG | हां (API tool, Knowledge Base) |
| **दोनों तरफ़ का transcript** | हां (input और output transcription) | हां (post-call webhook, dashboard) | हां (SDK `transcriptCallback` में `USER` और `BOT`) |
| **Audio recording** | API नहीं रखती; हमारा अपना client दोनों तरफ़ की audio सहेज सकता है | हां, default चालू; "post_call_audio" webhook पूरी बातचीत का audio भेजता है | हां, "Get recordings" API |
| **Hindi** | हां (99 भाषाओं की सूची में `hi`) | हां; Scribe v2 में Hindi का WER "(>5% to ≤10% WER)" | हां, मुख्य भाषा; 22 भारतीय भाषाएं (STT), 11 (TTS/Voice Agents) |
| **राजस्थानी / मारवाड़ी / बागड़ी** | सूची में नहीं | सूची में नहीं | सूची में नहीं; केवल "Includes dialects and accents of the above languages" |
| **Training पर data** | Free tier: हां, और human review भी; Paid: नहीं | Default हां; account में "Data use" से opt-out | Default हां ("Default Policy: Opt-In"); account settings या ईमेल से opt-out |
| **Data कहां** | Paid में भी "any country in which Google or its agents maintain facilities" | Default US; India residency केवल Enterprise | Voice Agents: "all data, including any PII, stays within India" |
| **Static site पर लगाना** | कोई तैयार widget नहीं; ephemeral token के लिए छोटा backend चाहिए | एक पंक्ति का widget; backend ज़रूरी नहीं (पर agent public रहेगा) | Dashboard से embed snippet; SDK के लिए backend चाहिए |
| **फ़ोन / WhatsApp** | partners के ज़रिए (Voximplant आदि) | Twilio/SIP, WhatsApp (calls + voice notes) | भारतीय telephony (Exotel, Vobiz, Smartflo…), Sarvam से नंबर किराये पर; WhatsApp पर voice केवल Enterprise |
| **Nonprofit / शिक्षा** | Gemini API के लिए कोई nonprofit credit नहीं मिला | Impact Program: "12 months of free Pro access" (पंजीकृत nonprofit) | Startup Program: "6–12 months of credits" (startups के लिए) |

---

## 2. Google AI Studio / Gemini Live API

**स्रोत:**
- https://ai.google.dev/gemini-api/docs/pricing (Last updated 2026-09-24)
- https://ai.google.dev/gemini-api/docs/live (2026-09-15)
- https://ai.google.dev/gemini-api/docs/live-guide (2026-09-18)
- https://ai.google.dev/gemini-api/docs/live-session (2026-09-15)
- https://ai.google.dev/gemini-api/docs/rate-limits
- https://ai.google.dev/gemini-api/docs/billing (2026-09-20)
- https://ai.google.dev/gemini-api/terms (2026-04-28, "Effective March 23, 2026")
- https://ai.google.dev/gemini-api/docs/usage-policies (2026-06-09)

### मुफ़्त और दाम
- Models: `gemini-3.8-live`, `gemini-3.8-live-extended-thinking`, `gemini-3.1-flash-live-preview` ("Our low-latency, audio-to-audio models optimized for real-time voice agents and live dialogue").
- Free Tier: input और output दोनों "Free of charge"। Paid Tier: "$0.75 (text)", "$3.00 or $0.005/min (audio)" input; "$4.50 (text)", "$12.00 or $0.018/min (audio)" output। audio का हिसाब "25 tokens per second of audio"।
- Free से Paid: "Upgrading from the Free Tier to the Paid Tier means linking a billing account and prepaying to add a minimum of $5"। Prepay credits: "unused credits expire after 12 months and are non-refundable"।
- $300 वाला Google Cloud credit काम का नहीं: "If you opened your account after March 2, 2026, you can't use these credits to pay for Gemini API and AI Studio usage"।
- Free tier की सटीक rate limits पन्ने पर नहीं हैं: "View your active rate limits in AI Studio"। Tier 1 (billing जुड़ने पर) में "$10" प्रति 10 मिनट की spend limit है।

**हमारा हिसाब (paid, `gemini-3.8-live`):** mic पूरे मिनट खुला रहे तो input ≈ $0.005/min।
- यादें दर्ज करना (सहायक 20% समय बोले): 0.005 + 0.2 × 0.018 ≈ **$0.0086/min**, यानी लगभग $0.52/घंटा।
- सवाल-जवाब (सहायक 50% बोले): ≈ **$0.014/min**, यानी लगभग $0.84/घंटा।
- $5 के न्यूनतम prepay से मोटे तौर पर 350-580 मिनट बनते हैं। तथ्यों वाले text tokens ($0.75/1M) इसमें अलग जुड़ेंगे, पर हमारे छोटे डेटा के लिए यह मामूली है। हर turn पर पुराना context दोबारा गिना जाता है या नहीं, यह पन्नों पर साफ़ नहीं मिला।

### क्षमता
- "Barge-in: Users can interrupt the model at any time"
- "Tool use: Integrates tools like function calling and Google Search"। 3.8 Live में "Asynchronous function calling … Supported (default)", यानी तथ्य लाते समय बातचीत नहीं रुकती।
- "Audio transcriptions: Provides text transcripts of both user input and model output" (`input_audio_transcription`, `output_audio_transcription`)
- "Affective dialog" और "Proactive audio" भी मौजूद हैं।
- Latency: केवल "low-latency" लिखा है, कोई ms संख्या नहीं।
- Audio format: input "raw 16-bit PCM audio, 16kHz", output "24kHz"; protocol "Stateful WebSocket connection (WSS)"।
- सीमाएं: "Audio-only sessions are limited to 15 minutes" (context window compression से बढ़ सकती है), और "The lifetime of a connection is limited as well, to around 10 minutes", जिसके लिए session resumption चाहिए। लंबी interview के लिए यह code में संभालना होगा।
- Recording: API audio नहीं सहेजती। पर browser में हमारा code बुज़ुर्ग की mic audio और model की 24kHz audio, दोनों ख़ुद सहेज सकता है।

### Hindi और बागड़ी
- live-guide: "Live API supports the following 99 languages", जिनमें "Hindi | hi" है। (overview पन्ना "70 supported languages" कहता है; दोनों पन्ने अलग संख्या बताते हैं।)
- "Native audio output models can switch between languages naturally during conversation"
- राजस्थानी, मारवाड़ी या बागड़ी सूची में नहीं है।

### Data नीति (सबसे अहम)
- **Free tier:** "When you use Unpaid Services … Google uses the content you submit to the Services and any generated responses to provide, improve, and develop Google products" और "human reviewers may read, annotate, and process your API input and output … Do not submit sensitive, confidential, or personal information to the Unpaid Services."
  - मतलब: **बुज़ुर्गों की असली यादें free tier पर कभी न भेजें।**
- **Paid tier:** "Google doesn't use your prompts … or responses to improve our products"। Logs "for a limited period of time, solely for detecting and preventing violations"; usage-policies के अनुसार यह अवधि "fifty-five (55) days" है। "This data may be stored transiently or cached in any country in which Google or its agents maintain facilities."
- India "Available regions" की सूची में है।
- **उम्र की शर्त (ध्यान दें):** "You also will not use the Services as part of a website, application, or other service … that is directed towards or is likely to be accessed by individuals under the age of 18." हमारा "पूछिए" हिस्सा नई पीढ़ी के लिए है, इसलिए यह शर्त हमारे लिए असली रुकावट हो सकती है। लगाने से पहले यह तय करना होगा कि यह सहायक केवल वयस्कों (18+) के लिए है।

### लगाने की मेहनत
- "Client-to-server: Your frontend code connects directly to the Live API"। पर "for production … we recommend using ephemeral tokens instead of standard API keys"। इसलिए token बनाने के लिए एक छोटी backend सेवा (Cloud Run या कोई serverless function) चाहिए; बाकी सारा काम static पन्ने के JavaScript में हो सकता है।
- कोई drop-in widget नहीं है। Partners: LiveKit, Pipecat, Voximplant (फ़ोन कॉल), Agora, Firebase AI Logic।

### Nonprofit
- Google for Nonprofits (https://www.google.com/nonprofits/) में Gemini app, Gemini Notebook और Google Cloud के offer दिखते हैं। Gemini **API** के लिए कोई nonprofit credit official पन्नों पर नहीं मिला।

---

## 3. ElevenLabs Agents (ElevenAgents)

**स्रोत:**
- https://elevenlabs.io/pricing/agents
- https://elevenlabs.io/pricing/api
- https://elevenlabs.io/impact-program
- https://elevenlabs.io/docs/eleven-agents/overview
- https://elevenlabs.io/docs/models
- privacy docs: retention, audio-saving, zrm
- https://elevenlabs.io/docs/overview/administration/data-residency
- https://elevenlabs.io/privacy-policy ("Updated 20 May 2026")
- https://elevenlabs.io/terms-of-use ("Last Updated: 31 March 2026")

### मुफ़्त और दाम
- Free: "$0per month", "15 minutes of calls included", "4 Concurrent Calls", "Knowledge Base", "Multilingual", "Widget"। "Commercial License" Starter ($6) से शुरू होता है।
- Paid (सभी plans पर): "Additional call minutes cost $0.08 per minute … LLM usage is billed separately on top, based on the model you choose."
- Plans: Starter $6 (75 min), Creator $22 / पहला महीना $11 (275 min), Pro $99 (1,238 min)।
- Telephony: "ElevenLabs adds no telephony fee"। Twilio या SIP provider अपना शुल्क अलग लेते हैं।
- भुगतान: "We accept Credit Card, Apple Pay, and Google Pay." (free account के लिए card चाहिए या नहीं, यह पन्ने पर नहीं लिखा)

**हमारा हिसाब:** $0.08 × 60 = **$4.80/घंटा + LLM**। यह Gemini Live से लगभग 6-9 गुना महंगा है।

### क्षमता
- Pipeline: "we use Scribe to transcribe your speech, an LLM … and our TTS model"।
- Component latency (pricing/api पन्ने से): v3 Conversational TTS "Low latency (~280ms)", Flash "~75ms", Scribe v2 Realtime "~150ms"। पूरी बातचीत की end-to-end latency की कोई संख्या नहीं मिली।
- "Configure turn-taking, interruptions, and timeout settings"
- Tools: Client tools, Webhook tools, Code tools, MCP tools, System tools। Knowledge Base और RAG plans में शामिल हैं। हमारे तथ्य Knowledge Base में सीधे डाले जा सकते हैं।
- Transcript और audio:
  - "Transcription webhooks (post_call_transcription): Contains full conversation data including transcripts"
  - "Audio webhooks (post_call_audio): Contains minimal data with base64-encoded audio of the full conversation"
  - Audio saving: "By default, audio recordings are enabled."

### Hindi और बागड़ी
- Eleven v3 / v3 Conversational की सूची में "Hindi (hin)" है। Multilingual v2 में भी Hindi है।
- Scribe v2 (STT) में Hindi "High Accuracy (>5% to ≤10% WER)" श्रेणी में है। तीनों में से केवल यही एक प्रकाशित गुणवत्ता संकेत है।
- Agents docs: "Selecting the All option … will configure the agent to support 31 languages"।
- ध्यान दें: "Language selection is fixed for the duration of the call"। पर एक "Language detection" system tool भी है।
- राजस्थानी, मारवाड़ी या बागड़ी किसी सूची में नहीं।

### Data नीति
- Training: "We may process your Personal Data to research, develop, train and/or otherwise improve our AI models. This may include processing audio, text…"। Opt-out: "You may opt out of our use of your Personal Data for training at any time by navigating to the 'Data use' menu in the 'Terms and Privacy' section"। Opt-out केवल आगे के data पर लागू होता है।
- Retention: "By default, ElevenLabs retains conversation data for 2 years"। इसे दिनों में घटाया जा सकता है।
- Zero Retention Mode: "Enterprise customers can use Zero Retention Mode"। यानी हमारे लिए उपलब्ध नहीं।
- Data location: "all Personal Data will be transferred to the United States for storage." India residency (`in.residency.elevenlabs.io`) है, पर "Data residency is an Enterprise feature"।
- भारत के निवासियों के लिए policy में "Right to nominate" और "Right of grievance redressal" का अलग खंड है (DPDP से मेल खाता)।

### लगाने की मेहनत
- सबसे आसान: `<elevenlabs-convai agent-id="…">` और एक `<script>` tag। पर "Widgets currently require public agents with authentication disabled", इसलिए कोई भी हमारे minutes ख़र्च कर सकता है।
- SDKs: JavaScript, React, Python, Swift, Kotlin। WhatsApp: "Message conversations — text, voice notes … Calls — inbound and outbound"।
- Post-call webhook से transcript और audio सहेजने के लिए एक endpoint (छोटा backend) चाहिए।

### Nonprofit
- Impact Program: "we provide free access to ElevenLabs technology for nonprofit organizations … professors, and their students"।
- पात्रता: "Registered nonprofit organizations in good standing. We prioritize organizations working in healthcare, education, and culture." Verification "Goodstack" से होता है।
- लाभ: "Approved nonprofits receive 12 months of free Pro access"। Pro में 1,238 call-minutes प्रति महीना हैं; हर साल दोबारा आवेदन।
- Directory में "Culture" श्रेणी और heritage संस्थाएं (जैसे Concord Covered Bridge Historic District) दिखती हैं, यानी हमारे जैसा काम इस program के दायरे में आता है।

---

## 4. Sarvam AI

**स्रोत:**
- https://www.sarvam.ai/api-pricing
- https://docs.sarvam.ai/api/getting-started/pricing
- https://docs.sarvam.ai/api/getting-started/ratelimits
- https://docs.sarvam.ai/api/getting-started/commercial-licensing
- https://docs.sarvam.ai/api/getting-started/models/saaras
- https://docs.sarvam.ai/api/getting-started/models/bulbul
- https://docs.sarvam.ai/conversations/overview
- https://docs.sarvam.ai/conversations/build/models
- https://docs.sarvam.ai/conversations/deploy/deploy-with-code
- https://docs.sarvam.ai/api/platform/data-retention
- https://docs.sarvam.ai/changelog
- https://www.sarvam.ai/products/conversational-agents
- https://www.sarvam.ai/privacy-policy ("Updated on: July 29, 2026")
- https://www.sarvam.ai/startup-program

### मुफ़्त और दाम
- "Every new user receives ₹100 in credits." "Credits are universal and never expire."
- Signup credits से बनी audio के commercial अधिकार: "These credits are **not** limited to evaluation-only or non-commercial use."
- Paid ("Pay as you go", "No monthly commitment"):
  - Speech to Text: "₹30" प्रति घंटा ("Priced per hour, billed per second"); diarization के साथ ₹45
  - Bulbul v3 TTS: "₹30" प्रति 10K अक्षर (यानी ₹3 प्रति 1,000 अक्षर)
  - Sarvam 105B LLM: "₹29.28" input / "₹73.2" output प्रति 1M tokens
- **Voice Agents (पुराना नाम Samvaad) का प्रति-मिनट दाम किसी official पन्ने पर नहीं मिला।** Docs का pricing पन्ना इसे सूचीबद्ध नहीं करता। एक news search में "₹1 per minute" दिखा, पर वह official स्रोत नहीं है, इसलिए यहां नहीं माना गया।

**हमारा हिसाब (Model APIs जोड़कर अपना pipeline):**
- STT: ₹0.50/मिनट।
- TTS: मान लें सहायक एक पूरे मिनट बोलने में ~900 अक्षर बोलता है। यह अनुमान है, जांचा नहीं। तो 20% बोलने पर ≈ ₹0.54, 50% पर ≈ ₹1.35।
- कुल मोटे तौर पर ₹1.0-1.9/मिनट, यानी ₹60-115/घंटा, + थोड़ा LLM।
- ₹100 के मुफ़्त credit से केवल STT के लिए **200 मिनट** (पक्का हिसाब) बनते हैं।

### क्षमता
- Voice Agents: "A real-time ASR → LLM → TTS loop"। Product पन्ना: "<500ms … Real-time latency"।
- Barge-in: SDK event "`user_interrupt` (barge-in)"।
- Transcript: "`transcript_callback` … A live transcript of both sides of the call"। Recordings के लिए "Get recordings" API।
- Tools और Knowledge Base: "Agents can call your systems … through tools"। "API tool" और "Knowledge Base" docs में हैं।
- "60-minute max call length (raised from 25 in August 2026)"। लंबी interview के लिए यह Gemini की 10-15 मिनट की सीमा से बेहतर है।
- STT `saaras:v4` में **Keyterm Prompting** है: "up to 50 domain-specific names, places"। अब यह streaming WebSocket पर भी चलता है। हमारे 34 गांवों के नाम 50 की सीमा में आ जाते हैं।

### Hindi और बागड़ी
- Saaras: "23 languages (22 Indian + English)", "Includes dialects and accents of the above languages", "Code-mixed audio support", "Intelligent Proper Noun and Entity Preservation"।
- Bulbul v3 TTS: "11 languages (10 Indian + English)", Hindi सहित।
- Voice Agents: "Agents operate across 11 languages: Hindi, …"।
- Product FAQ: "Our AI models are specifically trained on Indian languages and dialects"।
- राजस्थानी, मारवाड़ी या बागड़ी का नाम कहीं नहीं है। Hindi की कोई WER संख्या भी प्रकाशित नहीं मिली।

### Data नीति
- Training: "Default Policy: Opt-In. We use Your content (including inputs, uploads, prompts, or generated outputs) to train, fine-tune, and/ or improve our AI models unless you explicitly opt-out through your account settings or by writing to" (ईमेल)। **Account बनाते ही opt-out करना ज़रूरी है।**
- DPDP: "Axonwise Private Limited (doing business as Sarvam AI) is the Data Fiduciary under the Digital Personal Data Protection Act, 2023"।
- Voice Agents: "Every model in the Voice Agents stack … is self-hosted by Sarvam" और "Data residency in India: all data, including any PII, stays within India"।
- पर सामान्य privacy policy कहती है: "Personal data may be transferred to and processed in countries outside India, including: United States: Cloud infrastructure". यानी Model APIs के लिए India residency की ऐसी पक्की बात नहीं लिखी।
- Retention: "Until an Owner sets a retention period, your workspace's data is retained indefinitely." Model APIs के लिए "No retention (0 days)" चुना जा सकता है; Voice Agents के लिए "not yet supported"। सबसे छोटा विकल्प "1 day" है।

### लगाने की मेहनत
- Widget: "Copy the embed snippet from the dashboard. Paste it into your site"। "A widget is a small call-or-chat button … no phone number needed"।
- SDK (Web TypeScript, Python, React Native, Flutter)। SDK के साथ यह चेतावनी है: "Never expose production API keys in browser code … proxy WebSocket connections through your backend"।
- फ़ोन: Exotel, Twilio, Smartflo, Vobiz आदि, या "rent a number from Sarvam"। बिना smartphone वाले बुज़ुर्गों के लिए साधारण फ़ोन कॉल एक असली रास्ता है।
- WhatsApp: "Text agents, and voice agents on WhatsApp, are available to enterprise customers on request."

### Nonprofit
- Nonprofit program नहीं मिला। Startup Program: "API credits 6–12 months of credits matched to your scale"। Form में "Funding" और "Product stage" पूछे जाते हैं, इसलिए हम पात्र हैं या नहीं, यह पता नहीं।

---

## 5. रास्ते में मिले विकल्प (गहराई से नहीं देखे)

- **OpenAI Realtime** (https://developers.openai.com/api/docs/pricing):
  - `gpt-realtime-2.1`: audio input "$32.00", output "$64.00" प्रति 1M tokens।
  - `gpt-realtime-2.1-mini`: "$10.00" / "$20.00"।
  - Gemini Live ($3/$12) से कई गुना महंगा। Free tier नहीं दिखा।
- **Gemini 3.5 Transcribe** (उसी Google pricing पन्ने पर): "~$0.005 per min for Transcribe", "custom vocabulary biasing" और "speaker diarization" के साथ। पुरानी recordings को बाद में लिखने के लिए यह सस्ता विकल्प है (paid tier पर)।
- **Bhashini** (bhashini.gov.in): पन्ना केवल JavaScript से खुलता है, सामग्री नहीं पढ़ी जा सकी। जांचा नहीं।
- **Google Cloud STT/TTS:** नहीं देखा।

---

## 6. हमारे लिए सिफ़ारिश

**तीन हिस्सों वाला रास्ता। एक ही सेवा पर सब कुछ न टिकाएं।**

1. **Realtime सहायक (बोलकर पूछना और बातचीत से याद दर्ज करना): Gemini Live API, पर केवल Paid tier पर ($5 prepay से)।**
   - तीनों में सबसे सस्ता: यादें ≈ $0.52/घंटा, सवाल-जवाब ≈ $0.84/घंटा। ElevenLabs $4.80/घंटा + LLM।
   - Native audio, barge-in, async function calling (तथ्य लाते हुए बातचीत चलती रहे), दोनों तरफ़ के transcript, और Hindi।
   - $5 देते ही data "not used to improve our products" हो जाता है। Free tier पर बुज़ुर्गों की असली बात भेजना terms के ख़िलाफ़ सलाह है ("Do not submit … personal information")।
   - **दो शर्तें पहले हल करें:**
     - (क) 18 साल से कम उम्र वालों वाली शर्त। यह सहायक वयस्कों के लिए घोषित करें, या बच्चों वाला हिस्सा किसी दूसरी सेवा पर रखें।
     - (ख) 10 मिनट के connection और 15 मिनट के session की सीमा। इसके लिए session resumption और context compression लगाना होगा।

2. **मूल आवाज़ को लिखना (archive transcript) और India में data: Sarvam।**
   - `saaras:v4` batch STT, ₹30/घंटा, keyterms में 34 गांवों के नाम।
   - ₹100 के credit से 200 मिनट मुफ़्त, credit कभी expire नहीं होता, भारतीय कंपनी, और DPDP का Data Fiduciary।
   - Account बनाते ही training opt-out और retention सेट करें।
   - अगर बुज़ुर्गों तक **साधारण फ़ोन कॉल** से पहुंचना है, तो Sarvam Voice Agents सबसे सही है: India residency, 60 मिनट की call, भारतीय telephony। पर इसका प्रति-मिनट दाम Sarvam से लिखित में पूछना होगा।

3. **ElevenLabs: केवल अगर Impact Program मंज़ूर हो।**
   - अगर TechnoTaau (या साथी संस्था) पंजीकृत nonprofit है, तो आवेदन करें। 12 महीने Pro (1,238 min/महीना) मुफ़्त मिलेंगे, और एक पंक्ति के widget से "पूछिए" तुरंत साइट पर आ सकता है।
   - Impact Program के बिना: 15 मुफ़्त मिनट बहुत कम हैं, दाम सबसे ऊंचा है, data US में रहता है, और Zero Retention केवल Enterprise के लिए है।

**बागड़ी के बारे में सच:** तीनों में से किसी ने राजस्थानी, मारवाड़ी या बागड़ी को सूचीबद्ध नहीं किया है। इसलिए:
- `voice-bot-plan.md` वाली "20 clips" की परख ही असली फ़ैसला करेगी।
- **मूल audio ही असली रिकॉर्ड रहे।** इसे हमारे अपने निजी storage में रखें, किसी vendor के dashboard में नहीं।

---

## 7. Free credits से शुरू करने का तरीका (क्रम से)

1. **पहला खाता: Sarvam** (https://dashboard.sarvam.ai)
   - ₹100 मुफ़्त credit, कोई expiry नहीं।
   - खाता बनाते ही: (क) Account settings में model-training का **opt-out** करें; (ख) Settings → Workspace → Data retention में Owner छोटी अवधि सेट करे (Model APIs के लिए "No retention" संभव)।
   - फिर 20 परख-clips (परिवार की सहमति से) `saaras:v4` पर चलाएं, keyterms में गांवों के नाम डालें। ₹100 में 200 मिनट की STT आती है, जो इस परख के लिए काफ़ी है।
2. **दूसरा: Google AI Studio** (https://aistudio.google.com), Free Tier।
   - केवल team के अपने आवाज़ वाले नमूनों और नकली (बनावटी) बातचीत से Live API आज़माएं (AI Studio में "Stream")।
   - Hindi में बात, barge-in और हमारे तथ्यों वाला function call परखें। इस चरण में कोई असली याद न डालें।
   - AI Studio में Live model की free rate limit देखकर यहां लिख लें।
3. **Prototype:** static पन्ना + ephemeral token देने वाली छोटी backend सेवा + session resumption।
   - Browser में दोनों तरफ़ की audio और दोनों transcript हमारे storage में जाएं।
4. **असली बुज़ुर्गों से पहले:** उसी Google project पर billing जोड़ें और **$5 prepay** करें (Paid tier)। ध्यान रहे, credit 12 महीने में expire होता है।
   - साथ में DPDP वाली सहमति-पर्ची में साफ़ लिखें कि आवाज़ विदेशी सर्वर (Google) पर प्रोसेस होगी।
5. **ElevenLabs:** free खाता बनाकर 15 मिनट में उसी परख-सेट पर Hindi की तुलना करें।
   - अगर संस्था पंजीकृत है, तो https://elevenlabs.io/impact-program पर आवेदन करें (Goodstack verification)।
   - Account में "Data use" से training opt-out करें।
6. **साथ-साथ आवेदन:** Google for Nonprofits (Workspace और Gemini app के लिए, API credit नहीं)। चाहें तो Sarvam Startup Program भी।
   - Sarvam से ईमेल पर Voice Agents का प्रति-मिनट दाम और nonprofit छूट लिखित में मांगें।

---

## 8. जो जांचा नहीं जा सका

- Gemini Live की **free-tier rate limits** (RPM/RPD/sessions): पन्ना केवल "View your active rate limits in AI Studio" कहता है।
- Gemini Live में हर turn पर पुराने context के tokens दोबारा बिल होते हैं या नहीं: pricing पन्ने पर साफ़ नहीं। ऊपर का हिसाब केवल audio मिनटों पर है।
- Gemini Live की latency की कोई ms संख्या official पन्ने पर नहीं।
- Gemini API के लिए कोई nonprofit या startup credit: नहीं मिला।
- Live overview "70" भाषाएं कहता है और live-guide "99"। कौन सी संख्या ताज़ा है, पता नहीं (Hindi दोनों में है)।
- ElevenLabs Agents में **LLM का दाम** (केवल "varies by model"); free plan के लिए card चाहिए या नहीं; free plan पर गैर-व्यावसायिक उपयोग की सटीक शर्तें।
- ElevenLabs की end-to-end बातचीत latency (केवल अलग-अलग model की संख्याएं मिलीं)।
- **Sarvam Voice Agents का प्रति-मिनट दाम**, और क्या ₹100 का signup credit Voice Agents पर भी चलता है।
- Sarvam के लिए card या KYC चाहिए या नहीं; widget में key या abuse से सुरक्षा कैसे है; Model APIs का data India में ही रहता है या नहीं।
- किसी भी सेवा में **राजस्थानी, मारवाड़ी या बागड़ी** की गुणवत्ता। कोई संख्या नहीं मिली; केवल हमारी अपनी परख बताएगी।
- Hindi की गुणवत्ता संख्या: केवल ElevenLabs Scribe v2 ने दी (WER 5-10%)। Google और Sarvam ने Hindi WER इन पन्नों पर नहीं दिया।
- Sarvam TTS के हिसाब में "~900 अक्षर प्रति मिनट" हमारा अनुमान है।
- Bhashini: पन्ना JavaScript-only है, नहीं खुला।
- Google Cloud STT/TTS: नहीं देखा।
- डॉलर-रुपया दर: ₹ में बदलते समय उस दिन की दर देखें। यहां कोई दर नहीं मानी गई।

## QC (समन्वयक ने मूल पन्ने खोलकर जांचा, 26 सितंबर 2026)

| दावा | नतीजा |
|---|---|
| Gemini live मॉडल (`gemini-3.8-live`, `gemini-3.1-flash-live-preview`): audio in $0.005/min, out $0.018/min; free tier "Free of charge" | सही (ai.google.dev/gemini-api/docs/pricing) |
| Free tier का डेटा "to provide, improve, and develop Google products", "human reviewers may read" | सही (ai.google.dev/gemini-api/terms) |
| Gemini API किसी ऐसी सेवा में नहीं जो "likely to be accessed by individuals under the age of 18" | सही (terms)। इसलिए Gemini केवल स्वयंसेवकों (18+) के interview-tool में, सार्वजनिक या बच्चों वाले हिस्से में नहीं। |
| Paid tier का 55 दिन रखना | सही: usage-policies पर "Google retains the following data for fifty-five (55) days for the purposes of detecting and preventing violations" |
| Live session की सीमा: audio 15 मिनट, connection लगभग 10 मिनट | सही (ai.google.dev/gemini-api/docs/live-session); session resumption और compression से आगे बढ़ती है |
| Sarvam: training "Default Policy: Opt-In"; retention तय न करने पर "retained indefinitely"; STT ₹30/घंटा | सही (sarvam.ai/privacy-policy, docs.sarvam.ai/api/platform/data-retention, sarvam.ai/api-pricing) |
| ElevenLabs: "By default, ElevenLabs retains conversation data for 2 years" | सही (elevenlabs.io/docs/eleven-agents/customization/privacy/retention) |
| Sarvam: "Every new user receives ₹100 in credits" | सही (docs.sarvam.ai/api/getting-started/pricing) |
| ElevenLabs Agents: Free में 15 min, फिर $0.080/min; Impact Program: nonprofit को "12 months of free Pro access" | सही (elevenlabs.io/pricing/agents, elevenlabs.io/impact-program)। उसी पन्ने पर startups के लिए "ElevenLabs Grant" (12 महीने, 33M characters) भी है। |

**मोटा हिसाब (Gemini paid):** 1 घंटे का interview, जिसमें पूरे घंटे की आवाज़ अंदर जाए और लगभग 20 मिनट bot बोले: 60 × $0.005 + 20 × $0.018 = लगभग $0.66, यानी करीब ₹55-60 प्रति घंटा। $5 के prepay से लगभग 7-8 घंटे।
