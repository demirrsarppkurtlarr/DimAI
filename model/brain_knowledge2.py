"""DimAI knowledge pack 2 — AI/ML, DevOps, frontend, DB, CS, architecture."""

KB2: list[dict] = [
    # ---------- AI / ML ----------
    {"k": ["llm nedir", "large language model", "buyuk dil modeli"],
     "a": "**LLM (Large Language Model)**, metin üzerinde eğitilmiş büyük dil modelidir.\n\n• Token tahmin eder (sonraki kelime/parça)\n• ChatGPT, Claude, Llama, Gemini bu ailede\n• İnce ayar (fine-tune), RAG ve tool-use ile güçlenir\n• Halüsinasyon riski vardır — kritik olguları doğrula"},

    {"k": ["rag nedir", "retrieval augmented generation", "rag ne demek"],
     "a": "**RAG**, modele dış bilgiyi **arıp bağlama** ekleyerek cevap üretme yöntemidir.\n\n1. Soruyu embedding ile vektörleştir\n2. Belgelerden benzer parçaları getir\n3. Prompt'a koyup LLM'e ver\n\nGüncel/özel veride fine-tune'dan ucuz ve güncellenebilir."},

    {"k": ["embedding nedir", "vektor embedding", "text embedding"],
     "a": "**Embedding**, metin/görüntüyü sayısal **vektöre** çevirir; benzer anlamlar yakın olur.\n\n• Arama, clustering, RAG, öneri sistemleri\n• Mesafe: cosine / dot product\n• Model örnekleri: text-embedding-3, e5, bge"},

    {"k": ["transformer nedir", "transformer modeli", "attention is all you need"],
     "a": "**Transformer**, self-attention ile dizileri paralel işleyen sinir ağı mimarisidir (2017).\n\n• Encoder / decoder / decoder-only (GPT tarzı)\n• Uzun bağlamda dikkat maliyeti O(n²) (varyantlar bunu yumuşatır)\n• Modern LLM'lerin omurgası"},

    {"k": ["attention nedir", "self attention", "dikkat mekanizmasi"],
     "a": "**Attention (dikkat)**, dizideki her konumun diğer konumlara ne kadar bakacağını öğrenir.\n\n• Query / Key / Value\n• Self-attention: aynı dizinin iç ilişkileri\n• Multi-head: farklı ilişki türlerini paralel yakalar"},

    {"k": ["fine tuning nedir", "finetune nedir", "ince ayar nedir"],
     "a": "**Fine-tuning**, önceden eğitilmiş modeli kendi verinle biraz daha eğitmektir.\n\n• Stil, format, domain diline uyarlama\n• LoRA/QLoRA ile düşük maliyetli varyantlar\n• Güncel bilgi için RAG çoğu zaman daha pratik"},

    {"k": ["prompt engineering nedir", "prompt muhendisligi", "iyi prompt"],
     "a": "**Prompt engineering**, modele net talimat vererek çıktıyı yönlendirme sanatıdır.\n\n• Rol + görev + kısıt + örnek (few-shot)\n• Çıktı formatını belirt (JSON, madde)\n• Adım adım düşünmesini iste (gerekirse)\n• Belirsiz soru = belirsiz cevap"},

    {"k": ["agentic ai nedir", "ai agent nedir", "ajan yapay zeka"],
     "a": "**Agentic AI**, modelin sadece cevap yazmayıp **araç kullanıp plan yaparak** hedefe gittiği yaklaşımdır.\n\n• Araçlar: arama, kod çalıştırma, API\n• Döngü: düşün → hareket et → gözlemle\n• Güvenlik ve maliyet kontrolü kritik"},

    {"k": ["vector database nedir", "vektor veritabani", "vectordb nedir"],
     "a": "**Vector DB**, embedding vektörlerini saklayıp benzerlik araması yapar.\n\n• RAG, semantik arama, öneri\n• Örnekler: pgvector, Pinecone, Weaviate, Qdrant, Chroma\n• Index: HNSW / IVF"},

    # ---------- DevOps / cloud ----------
    {"k": ["helm nedir", "helm chart nedir", "kubernetes helm"],
     "a": "**Helm**, Kubernetes için paket yöneticisidir.\n\n• Chart = şablonlu YAML paketi\n• `helm install / upgrade / rollback`\n• Değerleri `values.yaml` ile özelleştirirsin"},

    {"k": ["argocd nedir", "argo cd nedir", "gitops argo"],
     "a": "**Argo CD**, Kubernetes için **GitOps** sürekli dağıtım aracıdır.\n\n• Git'teki desired state ↔ cluster\n• Drift görünce uyarır / senkronlar\n• PR ile deploy kültürü"},

    {"k": ["blue green nedir", "blue-green deployment", "mavi yesil deploy"],
     "a": "**Blue-green deploy**: iki özdeş ortam (blue=canlı, green=yeni).\n\n• Trafiği birden green'e kes\n• Sorun olursa anında blue'ya dön\n• Kaynak maliyeti yüksek ama rollback hızlı"},

    {"k": ["canary nedir", "canary deploy", "canary release"],
     "a": "**Canary release**, yeni sürümü önce küçük kullanıcı yüzdesine açar.\n\n• Metrikler iyi → oranı artır\n• Kötü → geri çek\n• Riski kademeli düşürür"},

    {"k": ["feature flag nedir", "feature toggle", "ozellik bayragi"],
     "a": "**Feature flag**, kodda özelliği deploy etmeden aç/kapa anahtarıdır.\n\n• A/B test, soft launch, kill switch\n• Deploy ≠ release ayırır\n• Eski flag'leri temizlemeyi unutma"},

    {"k": ["circuit breaker nedir", "devre kesici pattern"],
     "a": "**Circuit breaker**, ardışık hatalarda bağımlı servise çağrıyı keser.\n\n• Closed → Open (hata eşiği) → Half-open (deneme)\n• Cascading failure'ı önler\n• Timeout + retry ile birlikte kullanılır"},

    {"k": ["rate limiting nedir", "rate limit nedir", "istek sinirlama"],
     "a": "**Rate limiting**, bir istemcinin birim zamanda yapabileceği istek sayısını sınırlar.\n\n• Token bucket / sliding window\n• API abuse ve DoS'a karşı\n• 429 Too Many Requests"},

    {"k": ["throttling nedir", "throttle nedir"],
     "a": "**Throttling**, aşırı yükü yavaşlatarak sistemi korumaktır (rate limit'e yakın).\n\n• Gelen trafiği ertele / kuyruğa al\n• Kullanıcı deneyimini tamamen kesmek yerine yumuşatır"},

    {"k": ["backoff nedir", "exponential backoff", "geri cekilme"],
     "a": "**Backoff**, başarısız istekten sonra bekleme süresini artırmaktır.\n\n• Exponential: 1s → 2s → 4s…\n• Jitter ekle (herkes aynı anda vurmasın)\n• Retry bütçesi koy"},

    {"k": ["retry nedir", "retry pattern", "yeniden dene"],
     "a": "**Retry**, geçici hatalarda işlemi tekrar denemedir.\n\n• Sadece idempotent / güvenli işlemlerde\n• 5xx, timeout için; 4xx genelde değil\n• Backoff + max deneme şart"},

    {"k": ["observability nedir", "gozlemlenebilirlik"],
     "a": "**Observability**, sistemin iç durumunu dış sinyallerden anlama yeteneğidir.\n\n• Metrics + Logs + Traces (üç sütun)\n• Sadece monitoring'den fazlası: bilinmeyen soruları sorabilmek"},

    {"k": ["opentelemetry nedir", "otel nedir", "open telemetry"],
     "a": "**OpenTelemetry (OTel)**, metrik/log/trace toplamak için açık standarttır.\n\n• Vendor-agnostic enstrümantasyon\n• Collector → Prometheus, Jaeger, Grafana vb.\n• Modern observability omurgası"},

    {"k": ["grafana nedir", "grafana ne demek"],
     "a": "**Grafana**, metrik/log/trace için görselleştirme ve dashboard platformudur.\n\n• Prometheus, Loki, Tempo ile sık birlikte\n• Alerting kuralları\n• Operasyon ekiplerinin kontrol paneli"},

    {"k": ["jaeger nedir", "jaeger tracing"],
     "a": "**Jaeger**, dağıtık izleme (distributed tracing) sistemidir.\n\n• İsteklerin servisler arası yolunu gösterir\n• Gecikme ve hata kök nedeni analizi\n• OpenTelemetry ile beslenebilir"},

    {"k": ["cron nedir", "crontab nedir", "zamanlanmis gorev"],
     "a": "**Cron**, Unix'te zamanlanmış görev çalıştırıcıdır.\n\n• `dakika saat gün ay hafta-günü komut`\n• Örn: `0 3 * * * backup.sh` → her gün 03:00\n• Cloud'da: Cloud Scheduler, Render cron, k8s CronJob"},

    {"k": ["webhook nedir", "webhook ne demek"],
     "a": "**Webhook**, bir olay olunca karşı sisteme **HTTP POST** ile haber vermektir.\n\n• GitHub push → CI tetikle\n• Ödeme alındı → siparişi güncelle\n• İmza doğrulama + retry önemli"},

    {"k": ["sse nedir", "server sent events", "eventsource"],
     "a": "**SSE (Server-Sent Events)**, sunucudan tarayıcıya tek yönlü olay akışıdır.\n\n• `text/event-stream`\n• WebSocket'ten basit; iki yön gerekmezse yeterli\n• Chat streaming / canlı bildirim"},

    {"k": ["render nedir", "render com nedir", "render deploy"],
     "a": "**Render**, web servis / static / cron / Postgres barındıran bulut platformudur.\n\n• `0.0.0.0:$PORT` dinle\n• Free tier uyuyabilir; disk ephemeral\n• Blueprint (`render.yaml`) ile IaC"},

    {"k": ["cloudflare nedir", "cf nedir cdn"],
     "a": "**Cloudflare**, CDN + DNS + WAF + Workers sunan edge platformudur.\n\n• Trafiği yakın PoP'lardan servis eder\n• DDoS koruması, TLS, cache\n• Workers ile edge'de kod"},

    {"k": ["podman nedir", "podman vs docker"],
     "a": "**Podman**, Docker'a benzer konteyner motorudur (daemonless, rootless).\n\n• Komutlar çoğu zaman Docker ile uyumlu\n• systemd entegrasyonu güçlü\n• OCI image kullanır"},

    {"k": ["docker swarm nedir", "swarm nedir"],
     "a": "**Docker Swarm**, Docker'ın yerleşik orkestrasyon modudur.\n\n• Küçük/orta kümeler için basit\n• Günümüzde çoğu ekip Kubernetes tercih eder"},

    # ---------- Frontend / tooling ----------
    {"k": ["vite nedir", "vitejs nedir", "vite ne demek"],
     "a": "**Vite**, modern frontend build aracıdır (esbuild/Rollup).\n\n• Dev'de çok hızlı HMR\n• React/Vue/Svelte şablonları\n• Webpack'ten daha az config ile başlanır"},

    {"k": ["webpack nedir", "webpack ne demek"],
     "a": "**Webpack**, modülleri paketleyen klasik bundler'dır.\n\n• loader + plugin ekosistemi zengin\n• Config karmaşık olabilir\n• Yeni projelerde sıkça Vite tercih edilir"},

    {"k": ["babel nedir", "babeljs nedir"],
     "a": "**Babel**, modern JS/TS sözdizimini eski tarayıcıların anladığı JS'e çevirir (transpile).\n\n• Plugin/preset sistemi\n• JSX dönüşümü\n• Bugün çoğu işi TypeScript + Vite/SWC de yapar"},

    {"k": ["eslint nedir", "eslint ne demek"],
     "a": "**ESLint**, JavaScript/TypeScript kod kalitesi ve stil denetleyicisidir.\n\n• Kurallar: hata / uyarı\n• Prettier ile birlikte sık kullanılır\n• CI'da `eslint .` ile kırdır"},

    {"k": ["prettier nedir", "prettier format"],
     "a": "**Prettier**, tartışmasız kod formatlayıcıdır.\n\n• Stil savaşlarını bitirir\n• Kaydetince formatla (editor)\n• ESLint: mantık; Prettier: görünüm"},

    {"k": ["storybook nedir", "storybook ui"],
     "a": "**Storybook**, UI bileşenlerini izole geliştirme/dokümantasyon ortamıdır.\n\n• Her component için \"story\"\n• Design system ve visual test\n• React/Vue/Angular destekli"},

    {"k": ["redux nedir", "redux ne demek", "react redux"],
     "a": "**Redux**, öngörülebilir global state yönetim kütüphanesidir.\n\n• Tek store, pure reducer, action\n• Redux Toolkit ile boilerplate azalır\n• Küçük app'te Context/Zustand yetebilir"},

    {"k": ["zustand nedir", "zustand state"],
     "a": "**Zustand**, minimal React state kütüphanesidir.\n\n• Az boilerplate, hook tabanlı\n• Redux'tan hafif alternatif\n• Orta boy uygulamalarda popüler"},

    {"k": ["shadcn nedir", "shadcn ui", "shadcn/ui"],
     "a": "**shadcn/ui**, kopyalanabilir React bileşen koleksiyonudur (npm paketi gibi kilitli lib değil).\n\n• Radix + Tailwind üzerine\n• Kodu projenize ekler → tam kontrol\n• Design token'larla özelleştirilir"},

    {"k": ["nuxt nedir", "nuxtjs nedir", "nuxt 3"],
     "a": "**Nuxt**, Vue için full-stack / SSR framework'üdür (Next.js benzeri).\n\n• File-based routing\n• SSR/SSG/ISR\n• Nitro sunucu motoru"},

    {"k": ["svelte nedir", "sveltekit nedir"],
     "a": "**Svelte**, derleme zamanında DOM güncelleyen UI framework'üdür.\n\n• Runtime virtual DOM yok → küçük bundle\n• SvelteKit = routing + SSR\n• Okunabilir reaktif sözdizimi"},

    {"k": ["bun nedir", "bun js nedir", "bun runtime"],
     "a": "**Bun**, hızlı JS runtime + paket yöneticisi + bundler'dır (Zig ile yazılmış).\n\n• `bun install` çok hızlı\n• Node uyumluluğu hedefler\n• Test runner yerleşik"},

    {"k": ["deno nedir", "deno runtime"],
     "a": "**Deno**, güvenli-by-default JS/TS runtime'ıdır (Ryan Dahl).\n\n• İzin sistemi (net/fs)\n• URL import'lar, yerleşik toolchain\n• Node uyumluluk katmanı gelişiyor"},

    {"k": ["pnpm nedir", "pnpm vs npm"],
     "a": "**pnpm**, disk tasarruflu Node paket yöneticisidir.\n\n• Content-addressable store + hard link\n• Strict `node_modules` (phantom dep engeli)\n• Monorepo'da güçlü"},

    {"k": ["yarn nedir", "yarn paket", "yarn classic"],
     "a": "**Yarn**, npm alternatif paket yöneticisidir.\n\n• Classic (v1) ve Berry (v2+) hatları\n• Plug'n'Play seçeneği\n• Bugün pnpm/npm de yaygın"},

    {"k": ["poetry nedir", "python poetry"],
     "a": "**Poetry**, Python bağımlılık ve paketleme aracıdır.\n\n• `pyproject.toml` tek kaynak\n• Kilit dosyası + venv yönetimi\n• `pip` + `setuptools` karmaşasını sadeleştirir"},

    {"k": ["virtualenv nedir", "venv nedir", "sanal ortam python"],
     "a": "**virtualenv / venv**, projeye özel izole Python ortamıdır.\n\n• Sistem Python'unu kirletmez\n• `python -m venv .venv` → `source .venv/bin/activate`\n• Her proje kendi paket sürümleri"},

    # ---------- Testing ----------
    {"k": ["pytest nedir", "pytest ne demek"],
     "a": "**pytest**, Python'un popüler test framework'üdür.\n\n• `test_*.py` / `assert`\n• Fixture, parametrize, plugin'ler\n• `pytest -q` ile çalıştır"},

    {"k": ["jest nedir", "jest test"],
     "a": "**Jest**, JS test runner'ıdır (Facebook/Meta kökenli).\n\n• Birim + snapshot test\n• Mock'lar yerleşik\n• React ekosisteminde klasik"},

    {"k": ["vitest nedir", "vitest test"],
     "a": "**Vitest**, Vite tabanlı hızlı JS/TS test aracıdır.\n\n• Jest uyumlu API\n• ESM-native, HMR hissi\n• Vite projelerinde doğal seçim"},

    {"k": ["cypress nedir", "cypress e2e"],
     "a": "**Cypress**, tarayıcıda E2E test aracıdır.\n\n• Time-travel debug\n• Gerçek tarayıcıda çalışır\n• Büyük suite'lerde Playwright da sık tercih"},

    {"k": ["playwright nedir", "playwright test"],
     "a": "**Playwright**, Microsoft'un çok-tarayıcılı E2E test aracıdır.\n\n• Chromium/Firefox/WebKit\n• Auto-wait, tracing, parallel\n• Modern E2E standardı adayı"},

    {"k": ["postman nedir", "postman api"],
     "a": "**Postman**, API'leri elle denemek ve koleksiyon yönetmek için araçtır.\n\n• Request builder, env değişkenleri\n• Collection runner / test script\n• Alternatif: Insomnia, Bruno, curl"},

    {"k": ["insomnia nedir", "insomnia api"],
     "a": "**Insomnia**, hafif API istemcisidir (Postman alternatifi).\n\n• REST/GraphQL\n• Ortamlar ve plugin'ler\n• Open-source kökenli"},

    {"k": ["openapi nedir", "swagger nedir", "openapi swagger"],
     "a": "**OpenAPI** (eski adıyla Swagger spec), REST API sözleşmesini tanımlayan standarttır.\n\n• YAML/JSON şema\n• Client/SDK üretimi, mock, dokümantasyon\n• Swagger UI = etkileşimli doküman"},

    # ---------- Data / DB ----------
    {"k": ["cassandra nedir", "apache cassandra"],
     "a": "**Cassandra**, yüksek yazma ölçeği için dağıtık NoSQL (wide-column) veritabanıdır.\n\n• Masterless, çok replica\n• AP ağırlıklı (CAP)\n• Zaman serisi / olay log'ları için sık"},

    {"k": ["neo4j nedir", "graph database neo4j"],
     "a": "**Neo4j**, ilişki odaklı **graf veritabanıdır**.\n\n• Node + relationship\n• Cypher sorgu dili\n• Sosyal grafik, öneri, fraud yolları"},

    {"k": ["clickhouse nedir", "clickhouse db"],
     "a": "**ClickHouse**, analitik (OLAP) için sütunsal veritabanıdır.\n\n• Çok hızlı aggregation\n• Log/metrik/event analitikleri\n• Satır-tabanlı OLTP DB'nin yerine geçmez"},

    {"k": ["drizzle nedir", "drizzle orm"],
     "a": "**Drizzle**, TypeScript-first SQL ORM / query builder'dır.\n\n• SQL'e yakın, tip güvenli\n• Prisma'ya hafif alternatif\n• Serverless ortamda popüler"},

    {"k": ["supabase nedir", "supabase ne demek"],
     "a": "**Supabase**, Postgres üstüne Auth/Storage/Realtime/API sunan açık BaaS'tır.\n\n• Firebase alternatifi hissi\n• RLS ile güvenlik\n• Edge Functions"},

    {"k": ["firebase nedir", "google firebase"],
     "a": "**Firebase**, Google'ın mobil/web BaaS platformudur.\n\n• Auth, Firestore, Storage, FCM\n• Hızlı prototip\n• Vendor lock-in ve maliyet planı dikkat"},

    {"k": ["replication nedir", "veritabani replication", "db replication"],
     "a": "**Replication**, veriyi birden fazla kopyada tutmaktır.\n\n• Primary → replica (okuma ölçeği)\n• Yüksek erişilebilirlik\n• Lag ve failover planı gerekir"},

    {"k": ["sharding nedir", "db sharding", "veritabani sharding"],
     "a": "**Sharding**, veriyi birden fazla makineye **yatay bölmektir**.\n\n• Shard key seçimi kritik\n• Cross-shard sorgu zorlaşır\n• Büyüme için son çarelerden biri"},

    {"k": ["acid nedir", "acid ozellikleri", "acid db"],
     "a": "**ACID** (veritabanı işlemleri):\n\n• **A**tomicity — hep ya hiç\n• **C**onsistency — kurallar bozulmaz\n• **I**solation — eşzamanlılık ayrımı\n• **D**urability — kalıcı yazım\n\nPostgres/InnoDB klasik ACID sunar."},

    {"k": ["base nedir", "base teoremi", "base vs acid"],
     "a": "**BASE** (NoSQL dünyası):\n\n• **B**asically **A**vailable\n• **S**oft state\n• **E**ventually consistent\n\nACID kadar sıkı tutarlılık şart değilse ölçek için tercih edilir."},

    {"k": ["cap theorem nedir", "cap teoremi", "cap nedir"],
     "a": "**CAP teoremi**: dağıtık sistemde aynı anda üçünü tam garanti edemezsin:\n\n• **C**onsistency\n• **A**vailability\n• **P**artition tolerance\n\nAğ bölünmesinde C veya A seçersin; P pratikte zorunlu."},

    # ---------- Architecture ----------
    {"k": ["monolith nedir", "monolit nedir", "monolithic"],
     "a": "**Monolith**, uygulamanın tek deploy biriminde yaşamasıdır.\n\n• Başlangıçta basit, debug kolay\n• Büyüyünce deploy/ölçek paylaşımı zorlaşabilir\n• Microservices her zaman gerekmez"},

    {"k": ["microservices nedir", "mikroservis nedir"],
     "a": "**Microservices**, işi bağımsız deploy edilen küçük servislere bölmektir.\n\n• Teknoloji çeşitliliği, bağımsız ölçek\n• Ağ, gözlemlenebilirlik, veri tutarlılığı maliyeti\n• Takım/ölçek olgunluğu ister"},

    {"k": ["message queue nedir", "mesaj kuyrugu", "mq nedir"],
     "a": "**Message queue**, üretici/tüketici arasında asenkron mesaj tamponudur.\n\n• Spike'ları yumuşatır, gevşek bağ kurar\n• Örnek: RabbitMQ, SQS, Redis Streams\n• Idempotent consumer yaz"},

    {"k": ["event driven nedir", "event-driven", "olay guvenli mimari"],
     "a": "**Event-driven architecture**, bileşenlerin olay yayınlayıp dinlemesiyle konuşmasıdır.\n\n• Gevşek bağ, ölçeklenebilir tepkiler\n• Eventual consistency kabulü\n• Kafka / NATS / pub-sub sık kullanılır"},

    {"k": ["clean architecture nedir", "temiz mimari"],
     "a": "**Clean Architecture**, iş kurallarını framework/UI/DB'den ayırır.\n\n• Bağımlılık içe doğru (domain merkez)\n• Test edilebilir use-case'ler\n• Uncle Bob ile popülerleşti"},

    {"k": ["ddd nedir", "domain driven design", "alan odaklı tasarim"],
     "a": "**DDD (Domain-Driven Design)**, karmaşık iş domain'ini modelleme yaklaşımıdır.\n\n• Bounded context, aggregate, ubiquitous language\n• Teknik değil iş dili merkeze\n• Büyük ürünlerde yol haritası"},

    {"k": ["cqrs nedir", "cqrs pattern"],
     "a": "**CQRS**, okuma ve yazma modellerini ayırır (Command Query Responsibility Segregation).\n\n• Yazma: normalize / doğrulama\n• Okuma: denormalize / hızlı sorgu\n• Event sourcing ile sık birlikte"},

    {"k": ["event sourcing nedir", "olay kaynakli"],
     "a": "**Event sourcing**, durumu son snapshot değil **olay dizisi** olarak saklar.\n\n• Audit/geçmiş doğal gelir\n• Replay ile yeniden kurma\n• Karmaşıklık yüksek — bilinçli seç"},

    # ---------- Security ----------
    {"k": ["2fa nedir", "iki faktorlu", "mfa nedir", "totp nedir"],
     "a": "**2FA / MFA**, girişte ikinci kanıt ister (şifre + uygulama kodu / SMS / güvenlik anahtarı).\n\n• TOTP (Authenticator) SMS'ten daha iyi\n• Phishing'e karşı hardware key (WebAuthn) en güçlü"},

    {"k": ["rbac nedir", "role based access", "rol tabanli yetki"],
     "a": "**RBAC**, yetkileri rollere bağlar; kullanıcılara rol verir.\n\n• Admin / editor / viewer\n• ABAC'tan basit, çoğu uygulamaya yeter\n• En az yetki ilkesi"},

    {"k": ["encryption nedir", "sifreleme nedir", "encryption vs hashing"],
     "a": "**Encryption (şifreleme)**, veriyi anahtarla okunamaz hale getirir; geri çözülebilir.\n\n• Symmetric (AES) / asymmetric (RSA, ECC)\n• Hashing ≠ encryption (hash tek yön)\n• Transit: TLS; rest: disk/DB encryption"},

    {"k": ["salting nedir", "password salt", "tuzlama sifre"],
     "a": "**Salt**, şifre hash'inden önce eklenen rastgele değerdir.\n\n• Rainbow table'ı bozar\n• Her kullanıcıya unique salt\n• bcrypt/argon2 bunu yerleşik yapar"},

    {"k": ["hashing nedir", "hash nedir guvenlik", "kriptografik hash"],
     "a": "**Hashing**, girdiyi sabit uzunlukta özetler; geri döndürülemez.\n\n• Bütünlük (SHA-256), şifre (argon2/bcrypt)\n• Aynı girdi → aynı hash (salt yoksa)\n• Çakışma direnci önemli"},

    # ---------- CS fundamentals ----------
    {"k": ["bfs nedir", "breadth first search", "genislik oncelikli"],
     "a": "**BFS**, graf/ağaçta seviyeyi seviye gezer (kuyruk).\n\n• En kısa yol (ağırlıksız)\n• O(V+E)\n• DFS'ten farklı: derinlik değil genişlik"},

    {"k": ["dfs nedir", "depth first search", "derinlik oncelikli"],
     "a": "**DFS**, bir yolu sonuna kadar iner (yığın/recursion).\n\n• Topolojik sıra, çevrim tespiti, maze\n• O(V+E)\n• Backtracking ile birlikte sık"},

    {"k": ["btree nedir", "b-tree nedir", "b tree"],
     "a": "**B-tree**, disk dostu dengeli arama ağacıdır.\n\n• Veritabanı index'lerinin temeli\n• Yüksek dallanma → az I/O\n• B+tree varyantı yapraklarda sıralı liste tutar"},

    {"k": ["queue nedir", "kuyruk veri yapisi", "fifo nedir"],
     "a": "**Queue (kuyruk)**, FIFO veri yapısıdır: önce giren önce çıkar.\n\n• BFS, iş kuyrukları, buffering\n• `enqueue` / `dequeue`\n• Python: `collections.deque`"},

    {"k": ["stack nedir", "yigin veri yapisi", "lifo nedir"],
     "a": "**Stack (yığın)**, LIFO: son giren önce çıkar.\n\n• Call stack, undo, DFS, parantez eşleme\n• `push` / `pop`\n• Overflow/underflow dikkat"},

    {"k": ["heap nedir", "binary heap", "oncelik kuyrugu"],
     "a": "**Heap**, öncelik kuyruğu için kullanılan ağaçtır (genelde binary heap).\n\n• Min-heap / max-heap\n• insert & pop: O(log n)\n• Dijkstra, scheduling"},

    {"k": ["linked list nedir", "bagli liste"],
     "a": "**Linked list**, düğümlerin işaretçiyle bağlandığı listedir.\n\n• Ortaya ekleme kolay, rastgele erişim yavaş\n• Tek / çift yönlü\n• Array'e göre cache dostu değil"},

    {"k": ["big o nedir", "big o notation", "zaman karmasikligi", "o nedir algoritma"],
     "a": "**Big-O**, algoritmanın girdi büyüdükçe maliyetinin üst sınırını ifade eder.\n\n• O(1), O(log n), O(n), O(n log n), O(n²)\n• Ortalama / en kötü ayrımı yap\n• Sabitleri gizler — pratikte de ölç"},

    {"k": ["dynamic programming nedir", "dinamik programlama", "dp nedir"],
     "a": "**Dynamic programming (DP)**, alt problemleri kaydedip tekrar hesaplamamaktır.\n\n• Optimal alt yapı + örtüşen alt problemler\n• Memoization veya tabulation\n• Örn: Fibonacci, knapsack, edit distance"},

    {"k": ["greedy nedir", "greedy algorithm", "acgozlu algoritma"],
     "a": "**Greedy**, her adımda yerel en iyiyi seçer.\n\n• Hızlı ama her problemde optimal değil\n• Örn: activity selection, Dijkstra (dikkatli), Huffman\n• Kanıt veya karşı örnek şart"},

    {"k": ["mutex nedir", "mutual exclusion", "kilit mutex"],
     "a": "**Mutex**, aynı anda tek thread'in kritik bölgeye girmesini sağlar.\n\n• Lock / unlock\n• Unutulan unlock → deadlock\n• Semaphore'dan daha basit ikili kilit"},

    {"k": ["semaphore nedir", "semafor nedir"],
     "a": "**Semaphore**, sayaçlı senkronizasyon primitifidir.\n\n• N kaynağa kadar eşzamanlı erişim\n• Binary semaphore ≈ mutex benzeri\n• Producer-consumer klasik örneği"},

    {"k": ["race condition nedir", "yaris durumu"],
     "a": "**Race condition**, sonucun zamanlamaya bağlı yanlış çıkmasıdır.\n\n• Paylaşılan mutable state + eşzamanlılık\n• Kilit, atomic, immutable ile önle\n• Testte ara sıra patlar — sinsidir"},

    {"k": ["deadlock nedir", "olumcul kilitlenme"],
     "a": "**Deadlock**, süreçlerin birbirinin kilidini beklemesiyle sonsuza takılmasıdır.\n\n• Koşullar: mutual exclusion, hold&wait, no preemption, circular wait\n• Kilit sırası sabitle, timeout kullan"},

    {"k": ["garbage collection nedir", "gc nedir", "cop toplama"],
     "a": "**Garbage collection (GC)**, kullanılmayan belleği otomatik temizler.\n\n• Java, Go, JS, C# vb.\n• Pause / throughput trade-off\n• C/C++/Rust'ta manuel veya ownership"},

    {"k": ["memory leak nedir", "bellek sizintisi"],
     "a": "**Memory leak**, artık kullanılmayan belleğin bırakılmamasıdır.\n\n• GC'li dillerde: yanlış yere tutulan referanslar\n• Büyüme → OOM\n• Profiler ile bul (heap snapshot)"},

    {"k": ["pagination nedir", "sayfalama api", "cursor pagination"],
     "a": "**Pagination**, büyük sonuçları sayfa/parça halinde döndürmektir.\n\n• Offset/limit basit ama kaymalı\n• Cursor/keyset daha ölçekli\n• API'de `next` token ver"},

    {"k": ["idempotent nedir", "idempotency", "idempotent api"],
     "a": "**Idempotent**, aynı isteği tekrarlamak sonucun aynı kalmasıdır.\n\n• GET/PUT/DELETE genelde; POST dikkat\n• Ödeme/retry için idempotency-key\n• Güvenli retry'nin temeli"},

    # ---------- More practical ----------
    {"k": ["github actions nedir", "gh actions", "github actions ci"],
     "a": "**GitHub Actions**, GitHub'da CI/CD workflow çalıştırma sistemidir.\n\n• `.github/workflows/*.yml`\n• push/PR ile test, build, deploy\n• Marketplace action'ları"},

    {"k": ["gitlab ci nedir", "gitlab ci cd"],
     "a": "**GitLab CI/CD**, GitLab içi pipeline sistemidir.\n\n• `.gitlab-ci.yml`\n• Runner'larda job'lar\n• Stages: build → test → deploy"},

    {"k": ["s3 nedir", "amazon s3", "object storage s3"],
     "a": "**Amazon S3**, nesne depolama servisidir (dosya/blob).\n\n• Bucket + key\n• Statik site, yedek, media\n• Uyumlu API: MinIO, R2, birçok sağlayıcı"},

    {"k": ["dns nedir", "dns ne demek", "domain name system"],
     "a": "**DNS**, alan adını IP adresine çeviren sistemdir.\n\n• A / AAAA / CNAME / MX / TXT\n• TTL cache süresi\n• Site açılmazsa önce DNS'i kontrol et"},

    {"k": ["tls nedir", "ssl nedir", "https tls"],
     "a": "**TLS** (eski adıyla SSL), ağ trafiğini şifreleyen protokoldür.\n\n• HTTPS = HTTP + TLS\n• Sertifika (Let's Encrypt)\n• Man-in-the-middle'a karşı"},

    {"k": ["load balancer nedir", "yuk dengeleyici"],
     "a": "**Load balancer**, trafiği birden fazla sunucuya dağıtır.\n\n• L4 (TCP) / L7 (HTTP)\n• Health check + failover\n• Ölçek ve yüksek erişilebilirlik"},

    {"k": ["reverse proxy nedir", "ters proxy"],
     "a": "**Reverse proxy**, istemci ile backend arasına giren vekil sunucudur.\n\n• TLS sonlandırma, cache, routing\n• Nginx / Caddy / Traefik\n• Tek domain altında çok servis"},

    {"k": ["cdn nedir", "content delivery network"],
     "a": "**CDN**, içeriği kullanıcıya yakın edge sunuculardan sunar.\n\n• Statik asset, video, API cache\n• Gecikme ve origin yükü düşer\n• Cloudflare, Fastly, CloudFront"},

    {"k": ["http 2 nedir", "http2 nedir", "http/2"],
     "a": "**HTTP/2**, tek TCP bağlantısında çoklu stream (multiplexing) sunar.\n\n• Header compression (HPACK)\n• HTTP/1.1'e göre daha az gecikme\n• Sonraki adım: HTTP/3 (QUIC)"},

    {"k": ["graphql subscription nedir", "subscription graphql"],
     "a": "**GraphQL subscription**, gerçek zamanlı olay akışı için GraphQL operasyonudur.\n\n• WebSocket / SSE üzerinden\n• Chat, canlı skor, bildirim\n• Query/Mutation'dan ayrı kanal"},

    {"k": ["nix nedir", "nix package", "nixos"],
     "a": "**Nix**, saf (pure) ve yeniden üretilebilir paket yöneticisidir; NixOS da aynı modeldedir.\n\n• Declarative ortamlar\n• Aynı girdi → aynı çıktı\n• Öğrenme eğrisi dik, güç yüksek"},

    {"k": ["zig nedir", "zig dil", "ziglang"],
     "a": "**Zig**, C ile dost, güvenliğe ve basitliğe odaklı sistem dilidir.\n\n• Manuel bellek, net control flow\n• C interop güçlü\n• Cross-compile rahat"},

    {"k": ["vercel nedir", "vercel deploy"],
     "a": "**Vercel**, frontend/SSR uygulamalar için edge odaklı hosting'dir.\n\n• Next.js ile doğal uyum\n• Preview deploy'lar\n• Serverless / edge functions"},
]
