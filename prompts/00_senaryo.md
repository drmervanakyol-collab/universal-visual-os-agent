ROLE:
Sen; düşük seviyeli sistem programlama, bilgisayarlı görü, olay güdümlü mimariler, yerel/yapılandırılmış yapay zeka entegrasyonu, güvenilir masaüstü otomasyonu, gözlemlenebilirlik, hata toleransı ve endüstriyel yazılım mimarisi konularında uzman bir Baş Yazılım Mimarı ve Yapay Zeka Mühendisisin.

OBJECTIVE:
Python 3.14 tabanlı, harici .exe çalıştırmaya ihtiyaç duymayan, modüler, olay güdümlü, kendini onaran (self-healing), bağlam duyarlı (context-aware), denetlenebilir (auditable), güvenli ve üretime uygun bir “Universal Visual OS-Agent” tasarla.

Bu ajan:
- Ekranı yüksek doğrulukla algılamalı,
- Arayüzü semantik olarak anlamalı,
- Görevleri alt hedeflere bölerek planlamalı,
- Tıklama/yazma gibi eylemleri doğrulama sonrası uygulamalı,
- Beklenmedik durma sonrası görev durumunu geri yükleyebilmeli,
- Hata anında güvenli geri çekilme ve yeniden planlama yapabilmeli,
- Hedef uygulamanın performansını minimum etkilemelidir,
- Varsayılan olarak güvenli modda çalışmalı ve yalnızca açık politika/onay ile gerçek aksiyon almalıdır.

NON-GOALS / SAFETY CONSTRAINTS:
- Anti-bot sistemlerini aşmaya, tespit önleme/evasion’a, stealth davranışlara, gizli etkileşime veya güvenlik mekanizmalarını atlatmaya yönelik hiçbir tasarım yapma.
- Bankacılık, parola yöneticisi, ödeme, kimlik doğrulama ekranları, güvenlik yazılımları, kurumsal SSO, yönetici yetkisi isteyen pencereler, korumalı tarayıcı akışları ve benzeri hassas hedeflerde otomatik eylem üretme; bu tür durumları algılayıp engelle.
- Kullanıcı onayı, allowlist ve kill switch olmadan gerçek eylem yürütme.
- Sabit koordinatlara güvenme; çözünürlük, DPI ve düzen değişimlerine dayanıklı tasarla.
- Serbest metin tabanlı eylem üretme; tüm kararlar şeması sabit yapılandırılmış çıktı olmalıdır.
- Gerçekte çalıştırılmayan hiçbir testi veya doğrulamayı çalıştırılmış gibi raporlama.

SYSTEM DESIGN PRINCIPLES:
- Vision-first, verify-always, act-last.
- Event-driven ve asenkron çalışma.
- Fail-safe varsayılan davranış.
- Degrade gracefully: bir alt sistem bozulursa sistem kontrollü şekilde kısıtlı moda geçmeli.
- Tüm kritik kararlar gözlemlenebilir ve sonradan incelenebilir olmalı.
- Her zaman kullanıcı güvenliği, veri gizliliği ve açık izin önce gelir.
- Observe-only ve dry-run modları varsayılan tasarımın çekirdeğinde yer almalıdır.

TARGET PLATFORM:
- Windows öncelikli tasarım.
- Python 3.14 uyumlu.
- Harici çalıştırılabilir .exe gerektirmeyen çalışma yaklaşımı.
- Gerekli Python paketleri öncelikle wheel/library olarak tercih edilmeli; kaynak derleme gerekiyorsa bu durum açıkça raporlanmalı.
- CPU-only, single-GPU, workstation ve distributed profilleri desteklenecek şekilde katmanlı tasarım yapılmalı.

ARCHITECTURE OVERVIEW:
Sistemi şu katmanlarla tasarla:
1. Perceptual Layer
2. Semantic Understanding Layer
3. Cognitive / Planning Layer
4. Memory Layer
5. Action Layer
6. Verification & Recovery Layer
7. Safety, Policy & Audit Layer
8. Deployment & Operations Layer
9. Validation & Self-Debug Layer

1) PERCEPTUAL LAYER (ULTRA-PRECISION VISION):
- DXCAM ile yüksek hızlı ekran yakalama tasarla; hedef 60+ FPS, ancak performans profiline göre dinamik düşürülebilir olmalı.
- Kare farklarını SSIM, MS-SSIM ve MSE ile analiz et.
- 1 piksellik değişimleri event olarak işleyebilen bir fark algılama hattı kur.
- Optical Flow için OpenCV Farneback ve/veya Lucas-Kanade kullan; hareketli UI öğeleri için yön/hız tahmini yap.
- Mümkünse sub-pixel düzeyinde hareket yorumu için anti-aliasing ve kenar geçişlerinden faydalan.
- Görüntüleri işlem öncesinde normalize et: parlaklık, kontrast, doygunluk, gamma, gece modu etkileri.
- L*a*b* uzayında Delta E analizi ile renk farklılıklarını hesapla.
- Mümkün olan yerlerde alpha/transparency ve katman etkilerini hesaba kat; overlay/popup ayırt etmeye çalış.
- Sabit koordinat kullanma; tüm iç temsiller normalized koordinat sistemi (0.0–1.0) ile tutulmalı.
- YOLO tabanlı nesne tespiti ile buton, ikon, alan, popup, pencere elemanları algılansın.
- EasyOCR ile dinamik metin okuma yapılsın.
- CLIP veya benzeri zero-shot görsel-semantik model ile nesneleri yalnız şekle göre değil işlevsel/anlamsal olarak da sınıflandır.
- Çok aşamalı hedef bulma zinciri kur:
  YOLO -> OCR -> CLIP -> renk/şekil ipuçları -> piksel/şablon benzerliği
- Bu katman, çıktı olarak “semantic layout candidates” üretmelidir.

2) SEMANTIC UNDERSTANDING LAYER:
- Ekranı yalnız görüntü değil, mantıksal bir ağaç olarak modelle.
- Örnek üst düğümler: form, diyalog, liste, sekme, araç çubuğu, modal pencere, uyarı, hata, bilgi paneli.
- Input-label ilişkileri, buton-amaç ilişkileri, pencere-üst pencere ilişkileri ve modal engelleme durumlarını çıkarmaya çalış.
- Semantic Layout Tree şu alanları içersin:
  - node_id
  - type
  - role
  - label/text
  - bbox_normalized
  - confidence
  - parent/children
  - visibility
  - enabled/disabled estimate
  - occlusion estimate
  - z-order hints
  - actionable flag
- Element “görüldü” ile “eyleme uygun” ayrımını yap.
- Gerekirse “semantic_layout_version” mantığıyla değişen arayüz varyasyonlarını sürümlendir.

3) COGNITIVE / PLANNING LAYER:
- Yerel reasoning engine olarak llama-cpp-python üzerinden çalışan GGUF tabanlı bir LLM planla.
- LLM yalnızca karar verme, hata analizi, alt hedef üretimi ve yeniden planlama için kullanılmalı; ham ekran görüntüsünü sürekli besleme yerine, yapılandırılmış arayüz özeti ve kısa geçmiş ile çalışmalı.
- Orkestrasyon için LangGraph benzeri durum makinesi yaklaşımı kullan:
  THINK -> PLAN -> SELECT -> ACT -> VERIFY -> RECOVER -> RESUME
- Event-driven çalış: sadece ekran durumu anlamlı biçimde değiştiğinde veya görev mantığı yeni karar gerektirdiğinde reasoning tetiklensin.
- Structured Decision Contract zorunlu olsun. LLM çıktısı serbest metin değil şu şemada JSON olsun:
  {
    "goal": "...",
    "subgoal": "...",
    "screen_state_id": "...",
    "candidate_targets": [
      {"node_id": "...", "reason": "...", "confidence": 0.0}
    ],
    "selected_target": {"node_id": "...", "action": "click|double_click|type|scroll|wait|abort"},
    "preconditions": ["..."],
    "verification_rule": {"type": "ssim|text|object|layout_change", "expected": "..."},
    "fallback_plan": ["..."],
    "risk_flags": ["..."],
    "overall_confidence": 0.0
  }
- LLM yalnızca sistemin verdiği candidate target listesinden seçim yapabilsin; yeni hedef uyduramasın.
- Maksimum adım sayısı, maksimum tekrar sayısı ve zaman aşımı sınırları zorunlu olsun.
- LLM devre dışı kaldığında rule-based limited planner ile kısıtlı devam edilebilsin.

4) MEMORY LAYER:
- Temporal memory: son ekran durumları, aksiyonlar ve sonuçlar tutulmalı.
- Layout history: arayüzlerin geçmiş varyasyonları saklanmalı; bir buton yer değiştirirse benzer yerleşimlerden destek alınmalı.
- Failure memory: başarısız denemeler ve nedenleri ayrı tutulmalı.
- Memory backend olarak ChromaDB veya FAISS semantik arama için; SQLite ise görev durumu, audit ve recovery için kullanılmalı.
- Son 100–1000 aksiyonu yapılandırılmış biçimde tut.
- Her screen_state için benzersiz bir hash/kimlik üret.
- “Benzer ekran” aramasıyla yeniden planlamada önceki başarılı stratejileri kullan.
- Task, subgoal, pending verification ve recovery checkpoint’leri SQLite’da sürdürülmeli.

5) ACTION LAYER:
- Öncelik: güvenli ve izinli uygulamalarda OS-native input dispatch yaklaşımı.
- ctypes ile Windows API üzerinden giriş enjekte eden bir soyutlama katmanı tasarla; ancak bu katman yalnızca policy engine onayıyla çalışsın.
- Fallback olarak pynput benzeri bir ikincil kontrol hattı düşünülebilir.
- Tüm hareketler normalized koordinattan gerçek piksele dinamik çevrilsin.
- DPI awareness zorunlu olsun; süreç açılışında uygun DPI ayarlarını yap.
- İnsan-benzeri hız profili istenirse bunu sadece doğal etkileşim simülasyonu ve kullanıcı deneyimi amacıyla yap; anti-detection veya güvenlik atlatma amacı gütme.
- Pointer hareketi için eğrisel trajectory engine tasarla:
  - Bezier tabanlı ara yol
  - hafif mikrovaryasyon
  - hızlanma/yavaşlama profili
- Ancak hareket, doğruluk ve erişilebilirlik önceliği ile sınırlanmalı; görünmezlik/evasion amaçlı tasarlanmasın.
- Varsayılan gerçek aksiyon modu kapalı olmalı; observe_only veya dry_run varsayılan olsun.

6) VERIFICATION & RECOVERY LAYER:
- Her eylem sonrası ekran yeniden taranmalı.
- Beklenen state change şu kombinasyonlarla doğrulanmalı:
  - SSIM/MS-SSIM farkı
  - beklenen metnin görünmesi/değişmesi
  - beklenen nesnenin görünmesi/kaybolması
  - semantic layout tree değişimi
- Doğrulama başarısızsa şu akış çalışsın:
  1. kısa bekle ve yeniden tara
  2. alternatif hedef adayını dene
  3. semantic fallback zincirine geç
  4. LLM ile yeniden planla
  5. güvenli şekilde abort et ve nedenini logla
- Adaptive backoff kullan:
  - sistem yükü
  - FPS düşüşü
  - hedef uygulama yanıt gecikmesi
  - önceki benzer durumların başarı süresi
- Graceful Shutdown & State Recovery zorunlu olsun:
  - süreç beklenmedik şekilde durursa aktif task, subgoal, last_screen_state_id, pending_verification, retry_count, open_context ve plan checkpoint bilgileri SQLite’a yazılsın
  - ajan yeniden açıldığında saniyeler içinde bu checkpoint’i okuyup bulunduğu yerden devam etmeyi denesin
  - ekrana körlemesine devam etmek yerine önce state reconciliation yapsın: mevcut ekran, kaydedilmiş screen_state ile yeterince benzer mi kontrol etsin; değilse recovery planner devreye girsin
- Recovery başarısızsa güvenli abort, audit log ve kullanıcıya açıklayıcı durum üret.

7) SAFETY, POLICY & AUDIT LAYER:
- Policy engine ekle:
  - allowlist uygulamalar
  - denylist uygulamalar
  - hassas pencere algılama
  - maksimum aksiyon hızı
  - izin verilen eylem tipleri
  - yasak ROI bölgeleri
- Global kill switch zorunlu olsun.
- Manuel pause/resume desteklensin.
- Protected-context detection ekle:
  - parola alanları
  - ödeme ekranları
  - yönetici yetki istemleri
  - güvenlik yazılımları
  - kimlik doğrulama pencereleri
  Tespit edilirse ajan eylem yapmadan durmalı ve durumu loglamalı.
- Forensic audit:
  - her aksiyonun zamanı
  - hedef düğüm
  - seçilme nedeni
  - confidence
  - öncesi/sonrası ekran özeti
  - doğrulama sonucu
  - recovery akışı
  - policy kararları
  kaydedilmeli.
- SQLite veya HDF5 tabanlı denetlenebilir kayıt planı oluştur.
- Gizlilik:
  - OCR ve loglarda hassas verileri maskele
  - ekran görüntülerini mümkünse tam yerine ROI/metaveri düzeyinde tut
  - veri saklama süresi ve temizleme politikası tanımla

8) Z-ORDER, WINDOW & OCCLUSION INTELLIGENCE:
- Pencerelerin üst/alt ilişkisini anlamak için pencere bilgilerini topla.
- Tıklanacak öğenin üstünde modal, popup, toast, tooltip veya başka pencere varsa doğrudan tıklama yapma.
- Önce engeli semantik olarak sınıflandır:
  - kapatılabilir popup
  - hata diyalogu
  - izin istemi
  - sistem bildirimi
  - engelleyici modal
- Güvenli ise engeli kaldıracak plan üret; güvenli değilse abort et.
- Occlusion score tahmini semantic layout tree’ye dahil edilsin.

9) NON-INTRUSIVE OBSERVATION / PERFORMANCE BUDGET:
- Ajanın gözlem ve analiz katmanları hedef uygulamanın performansını mümkün olduğunca düşük etkilemeli; tasarım hedefi normal koşullarda %5 civarında veya altında ek yük olmalıdır.
- Bunun için:
  - capture ve inference ayrık async görevler olarak çalışsın
  - SharedMemory / zero-copy benzeri veri akışı tercih edilsin
  - tam ekran yerine event/ROI öncelikli analiz yapılsın
  - ağır modeller her karede değil, olay temelli veya düşük frekansta çağrılsın
  - CPU-only modda otomatik kalite düşürme politikası olsun
- Runtime scheduler şu sinyallere bakarak kalite/frekans ayarı yapsın:
  - CPU kullanımı
  - RAM baskısı
  - GPU kullanımı
  - capture FPS
  - inference latency
  - hedef uygulamanın foreground yanıt verme davranışı

10) CAPABILITY DEGRADATION POLICY:
- Alt sistemlerden biri bozulursa ajan tamamen çökmemeli.
- Örnek degrade modları:
  - YOLO yok -> OCR + CLIP + layout heuristics
  - OCR yok -> detection + icon semantics + color cues
  - CLIP yok -> YOLO + OCR + geçmiş layout memory
  - LLM yok -> rule-based limited planner
  - GPU yok -> düşük FPS ve daha seyrek reasoning
- Sistem aktif modunu her zaman loglamalı:
  full, reduced, safe-only, observe-only
- Degrade modda doğruluk/latency etkisi audit kayıtlarına işlenmeli.

11) DEPLOYMENT & ENVIRONMENT DESIGN:
- Tasarımı şu çalışma profilleri için ayrı düşün:
  a) CPU-only laptop
  b) single-GPU desktop
  c) high-RAM workstation
  d) distributed node + remote memory
- Her profil için:
  - minimum RAM
  - önerilen VRAM
  - hedef capture FPS
  - önerilen model boyutu
  - beklenen inference latency
  - kapatılması önerilen modüller
  belirtilsin.
- Python ortamı izolasyonu için venv/uv/pip tabanlı kurulum tasarla.
- Bağımlılıklar için wheel-first, source-build-second yaklaşımı kullan.
- Harici çalıştırılabilir bağımlılık gerektiren bileşenleri varsayılan mimariye koyma.
- Model dosyaları, eşikler, prompt şablonları ve politika kuralları versiyonlu bir registry altında tutulmalı.
- AI bileşenlerinin nereye kurulacağı açıkça tanımlansın:
  - LLM: yerel makine veya ayrı inference node
  - vision modelleri: aynı host veya GPU host
  - memory DB: yerel veya ayrı servis
  - audit DB: yerel SQLite varsayılan, ölçeklenirse merkezi DB opsiyonu

12) COMPATIBILITY MATRIX:
- Tasarım, Python 3.14 ile uyumlu olacak şekilde hazırlanmalı.
- Her önemli bağımlılık için şu alanları içeren bir compatibility matrisi iste:
  - package name
  - tested version
  - Python 3.14 status
  - wheel availability
  - CPU/GPU support
  - optional/fallback alternative
- Eğer belirli paketlerde 3.14 sürtünmesi varsa alternatif öner:
  - FAISS yerine ChromaDB veya saf SQLite+embedding cache
  - ağır vision modeli yerine daha hafif varyant
  - LLM modeli için daha küçük GGUF seçenekleri
- Kod üretirken “uyumsuzluk halinde graceful fallback” tasarımını dahil et.

13) COORDINATE SYSTEM & DPI:
- Tüm iç temsiller normalized olsun.
- Şu yardımcıları tasarla:
  - normalized_to_screen(nx, ny, screen_metrics) -> (x_px, y_px)
  - bbox_normalized_to_screen(bbox, screen_metrics)
  - screen_to_normalized(x_px, y_px, screen_metrics)
  - dpi_aware_screen_metrics()
- Çoklu monitör, negatif koordinatlar, ölçeklendirme farkları ve sanal masaüstü alanı hesaba katılsın.
- Gerçek tıklama öncesi hedef noktanın o anki geçerli pencere/ROI içinde kalıp kalmadığı doğrulansın.

14) MAIN LOOP REQUIREMENTS:
- asyncio tabanlı event-driven ana döngü tasarla.
- Örnek mantık:
  observe -> diff -> semantic rebuild -> policy check -> plan -> select -> verify preconditions -> act -> verify postconditions -> commit memory
- Gereksiz polling’den kaçın.
- Sadece anlamlı değişimlerde ağır pipeline tetiklensin.
- Zamanlayıcılar, kuyruklar ve cancellation mantığı temiz tanımlansın.

15) TESTABILITY & OBSERVABILITY:
- Her modül bağımsız test edilebilir olsun.
- Replay mode tasarla:
  kayıtlı ekran akışı üzerinden offline test yapılabilsin.
- Deterministic test mode ekle:
  rastgelelik ve gürültü devre dışı bırakılabilsin.
- Metrikler:
  - click precision
  - false click rate
  - recovery time
  - state-change detection latency
  - average planning latency
  - CPU/GPU usage
  - target app impact
- Kabul kriterleri sayısal olarak raporlanmalı.
- Observe-only, dry-run, replay-mode ve recovery-mode için ayrı test senaryoları oluşturulmalı.

16) DELIVERABLES TO PRODUCE:
Bu promptu uygulayan sistem için şu çıktıları üret:
1. Python 3.14 ile uyumlu modüler proje yapısı
2. Katmanlara ayrılmış mimari açıklaması
3. asyncio tabanlı ana döngü iskeleti
4. Normalized koordinat ve DPI çevirici yardımcıları
5. Policy engine ve kill switch tasarımı
6. Graceful shutdown / state recovery veri modeli
7. Verification ve self-correction akışı
8. Compatibility matrix şablonu
9. requirements.txt taslağı (yalnız Python paketleri; gerekirse opsiyonel bölümlerle)
10. CPU-only / GPU / degraded mode çalışma profilleri
11. SQLite audit şeması
12. Replay/test planı
13. Validation report formatı
14. Dry-run ve observe-only örnek akışları

17) PRE-DELIVERY VALIDATION & SELF-DEBUG LOOP:
Kod üretimi tamamlandıktan sonra, kodu kullanıcıyla paylaşmadan önce zorunlu bir “ön teslim doğrulama döngüsü” çalıştır.

Amaç:
- Yazılan kodun sözdizimsel olarak geçerli olup olmadığını kontrol etmek,
- Bağımlılık, import, tip, async akış, veri modeli ve platform uyumluluğu hatalarını erken bulmak,
- Bulunan hataları kodu paylaşmadan önce düzeltmek,
- Düzeltme sonrası yeniden test etmek,
- Yalnızca doğrulanmış veya dürüstçe sınırları belirtilmiş çıktı paylaşmak.

Kurallar:
- Gerçekte çalıştırılmayan hiçbir testi “çalıştırıldı” diye raporlama.
- Mock, replay, dry-run, static analysis ve gerçek runtime testlerini birbirinden açıkça ayır.
- Test sonucu belirsizse bunu dürüstçe belirt ve riskli kısımları işaretle.
- Kod paylaşılmadan önce en az bir self-debug döngüsü zorunludur.
- Hata bulunduysa önce düzelt, sonra yeniden doğrula, en son paylaş.

Validation Pipeline:
1. Syntax Validation
   - Tüm Python dosyalarında sözdizimi kontrolü yap.
   - Kırık import, eksik parantez, yanlış indentation, bozuk async/await kullanımı, geçersiz type hint ve isim çakışmalarını bul.

2. Dependency & Compatibility Validation
   - requirements içindeki paketlerin Python 3.14 ile uyum risklerini kontrol et.
   - Her kritik bağımlılık için:
     import edilebilirlik,
     wheel availability riski,
     opsiyonel fallback,
     CPU/GPU modu davranışı
     değerlendirilmelidir.
   - Yüksek riskli bağımlılık varsa alternatif öner veya fallback modunu aktive et.

3. Static Analysis
   - Kullanılmayan değişkenler, erişilemeyen kod, potansiyel race condition, yanlış shared state kullanımı, asyncio deadlock riski, yanlış cancellation akışı ve exception swallowing problemlerini tespit et.
   - ctypes, shared memory, multiprocessing ve async queue kullanımlarını özellikle incele.

4. Type & Interface Validation
   - Modüller arası arayüzlerin tutarlı olup olmadığını doğrula.
   - Protocol / interface / dataclass / veri modellerinin alan eşleşmelerini kontrol et.
   - Semantic layout tree, action contract, memory record ve audit schema alanları eksiksiz mi doğrula.

5. Unit-Level Sanity Checks
   - Aşağıdaki kritik fonksiyonlar için test veya en azından doğrulama senaryosu üret:
     normalized_to_screen
     screen_to_normalized
     dpi_aware_screen_metrics
     semantic tree builder
     target selector
     verification evaluator
     recovery planner
     SQLite checkpoint read/write
   - Sınır durumlarını kontrol et:
     tek monitör,
     çoklu monitör,
     negatif koordinat,
     yüksek DPI,
     boş OCR sonucu,
     detection failure,
     modal occlusion,
     timeout,
     interrupted recovery.

6. Async / Event-Loop Validation
   - Main loop, cancellation, timeout, retry ve recovery akışlarını dry-run olarak simüle et.
   - Sonsuz döngü, kilitlenme, event storm, duplicate event processing ve task leak risklerini bul.
   - Graceful shutdown sırasında hangi task’lerin kapanacağı ve state’in ne zaman flush edileceği açık olmalı.

7. Safe Runtime Simulation
   - Varsayılan olarak observe-only veya dry-run modunda çalıştırılabilecek bir doğrulama senaryosu oluştur.
   - Gerçek tıklama yapmadan:
     capture,
     diff,
     semantic parse,
     planning,
     candidate selection,
     verification rule generation,
     recovery path
     zincirini test et.
   - Replay mode varsa kayıtlı frame akışıyla entegrasyon akışını sınamalısın.

8. Recovery Validation
   - Süreç beklenmedik şekilde durdu varsayımıyla:
     checkpoint yaz,
     yeniden başlat,
     state reconciliation yap,
     task/subgoal geri yükle,
     gerekiyorsa recovery planner çağır.
   - Recovery başarısızsa güvenli abort ve audit log beklenmelidir.

9. Performance Sanity Check
   - Tasarlanan pipeline’ın hangi modüllerinin pahalı olduğunu işaretle.
   - Non-intrusive observation hedefi için darboğaz analizi yap:
     capture latency,
     OCR latency,
     detector latency,
     LLM latency,
     DB write latency.
   - Gerekirse kalite düşürme / ROI-first / lower-frequency inference öner.

10. Error Discovery & Auto-Fix Loop
   - Hata bulunduğunda aşağıdaki döngüyü uygula:
     detect -> classify -> locate root cause -> patch -> retest -> compare
   - Aynı hata tekrar ediyorsa yüzeysel yama yapma; kök neden çözülmelidir.
   - Her düzeltme sonrası ilgili testler yeniden çalıştırılmalıdır.

11. Pre-Delivery Gate
   - Kod ancak şu koşullarda paylaşılabilir:
     a) syntax hatası yok
     b) ana modül arayüzleri tutarlı
     c) en az dry-run/replay seviyesinde akış doğrulanmış
     d) recovery/checkpoint mantığı gözden geçirilmiş
     e) kritik riskler açıkça raporlanmış
   - Bu koşullar sağlanmıyorsa önce sorunları düzelt, sonra paylaş.

12. Delivery Report Format
   Kod paylaşmadan hemen önce kısa bir “Validation Report” üret:
   - Executed Checks
   - Fixed Issues
   - Remaining Risks
   - Simulated vs Actually Executed
   - Recommended Next Tests
   - Safe/Unsafe Modules
   Bu rapor dürüst olmalı; kesin doğrulanmayan kısımlar kesin çalışıyor gibi sunulmamalıdır.

13. Implementation Discipline
   - Kod üretirken test edilebilir yaz.
   - Önce interface ve veri modellerini tanımla.
   - Sonra modülleri küçük parçalarda uygula.
   - Her kritik modül tamamlandığında mini self-check uygula.
   - Büyük dosya yazıp en sonda debug etmeye çalışma; artımlı doğrulama yap.

14. Mandatory Modes
   Sistem şu modları desteklemeli ve doğrulama bunlar üzerinden yapılmalıdır:
   - observe_only
   - dry_run
   - replay_mode
   - safe_action_mode
   - recovery_mode
   Varsayılan mod observe_only olmalıdır.

15. Honesty Constraint
   - Eğer gerçek Windows ortamı, GPU, çoklu monitör veya belirli kütüphane sürümleri mevcut değilse bu eksikliği açıkça belirt.
   - Eksik ortam yüzünden doğrulanamayan kısımlar için “teorik olarak doğru” ile “pratikte test edildi” ayrımını koru.

IMPLEMENTATION STYLE:
- Kod üretirken modüler, type-hinted, test edilebilir, açık log üreten ve güvenli varsayılanlara sahip bir yapı kullan.
- Her kritik modül için arayüz (interface/protocol) ve fallback stratejisi tanımla.
- Üretilecek örnek kod gerçek eylem çalıştırmadan önce observe-only ve dry-run modlarını desteklesin.
- Varsayılan mod observe-only olsun; gerçek eylem için açık yapılandırma ve kullanıcı onayı gereksin.
- Büyük monolitler yerine küçük, bağımsız ve birim test edilebilir modüller tasarla.

FINAL DESIGN GOAL:
Amaç; rastgele piksellere tıklayan kırılgan bir makro değil, yüksek doğruluklu görsel algı, semantik arayüz anlama, yapılandırılmış karar verme, güvenli eylem yürütme, geri kazanım, denetim, kontrollü bozunma, artımlı kendini doğrulama ve kontrollü teslim süreçlerine sahip, meşru masaüstü otomasyonu ve erişilebilirlik senaryolarında kullanılabilecek endüstriyel bir görsel ajan iskeleti üretmektir.
