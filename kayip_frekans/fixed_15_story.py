from pathlib import Path
import json

OUT = Path('output')
OUT.mkdir(exist_ok=True)
TITLE = 'Kapının Öteki Tarafındaki Ses'
STORY = '''Polis kapıyı kırdığında evin içinde benden başka kimse yoktu. Buna rağmen telefonumun ses kaydında, benim sesimin hemen arkasından ölmüş kardeşim Emre’nin “Kapıyı açma, o ben değilim” dediği duyuluyordu. O kaydı dinleyen komiser üç kez başa sardı, sonra bana hiçbir şey sormadan salonun kapısını kapattı. Çünkü aynı cümleyi, polisler gelmeden yaklaşık bir saat önce dış kapının öteki tarafından da duymuştum.

Her şey o akşam köydeki eski aile evine tek başıma gitmemle başladı. Babam evi satmaya karar vermişti. Benim yapacağım şey basitti: dolaplardaki birkaç kutuyu ayıracak, ertesi sabah emlakçı gelmeden önce eski eşyaları toparlayacaktım. Ev çocukluğumdan beri neredeyse hiç değişmemişti. Taş duvarlar, dar koridor, mutfağa açılan ahşap kapı ve üst kata çıkan gıcırdayan merdiven aynıydı. Değişen tek şey, Emre’nin artık orada olmamasıydı. Kardeşim iki yıl önce köy yolunda yaptığı kazada ölmüştü. O günden sonra annem eve bir daha adım atmamıştı.

Hava karardığında elektrik iki kez gidip geldi. Yağmur pencereye sert vuruyordu. Salondaki kutuları dizerken mutfaktan ince bir metal sesi duydum. Önce düşen bir kaşık sandım. Fakat mutfağa girdiğimde masanın üzerinde Emre’nin eski anahtarlığını gördüm. Küçük, yuvarlak ve kenarı ezilmiş bir metal parçaydı. Onu kazadan sonra bulamamıştık. Babam, anahtarlığın araçla birlikte hurdaya gittiğini söylemişti. Elime aldığımda buz gibi değildi; tam tersine, sanki birinin avucundan yeni çıkmış gibi sıcaktı.

Anahtarlığı masaya bıraktım ve babamı aradım. Telefon bir kez çaldı, sonra hat kesildi. Tam tekrar arayacakken dış kapıdan üç yavaş vuruş geldi. Tokmak yıllardır kullanılmıyordu; paslanmıştı ve aşağı doğru sarkıyordu. Koridora çıktım. Kapının altından ışık gelmiyordu. Pencereden bahçeye baktım. Yağmur çamuru dümdüz etmişti, kapının önünde tek bir ayak izi bile yoktu. Sonra dışarıdan kardeşimin sesi geldi. Çok sakin bir şekilde, “Abi, açar mısın?” dedi.

İlk anda nefesim kesildi. Ses Emre’nindi; yalnızca benzer değildi, tam olarak oydu. Kelimelerin sonunu hafifçe uzatması, “abi” derken sesi biraz kısması bile aynıydı. Elimi kilide götürdüm ama dokunmadım. Çocukken birbirimizi korkutmak için kullandığımız bir söz vardı. Evde gece saklambaç oynadığımız zaman, biri diğerini bulursa “ışığı söndür, annemiz uyanacak” derdi. Bu cümleyi ailede kimse ciddiye almazdı. Kapının arkasındaki ses bir süre sustu, sonra fısıltıyla aynı cümleyi söyledi: “Işığı söndür, annemiz uyanacak.”

Geri çekildim. O anda aklıma, Emre’nin ölümünden birkaç hafta önce söylediği bir şey geldi. Kazadan önce bu evde tek başına kalmış, sabaha karşı kapının önünde benim sesimi duyduğunu anlatmıştı. Ben şehirdeydim ve bunu şaka sanmıştım. “Sana benzeyen bir şey kapının dışında duruyordu,” demişti. “Sesini birebir yaptı ama ayak sesi yoktu.” O gün ona güldüğüm için şimdi utandım. Çünkü dışarıdaki şey aynı yöntemi bana uyguluyordu.

Kapı yeniden üç kez vuruldu. Bu kez ses daha yakındı, sanki ağzını tahtaya dayamıştı. “Üşüdüm abi,” dedi. “Beni burada bırakma.” Kilidi açmadım. Telefonumla ses kaydı başlattım ve cihazı ayakkabılığın üzerine koydum. Kayıt açıkken kapıya, “Emre gerçekten sensen, kazadan önce bana en son ne söyledin?” diye sordum. Dışarıdaki ses hemen cevap vermedi. Yaklaşık on saniye sonra, “Kendine iyi bak demiştim,” dedi. Yanlıştı. Emre’nin bana son söylediği cümle, arabasının farlarından birinin bozuk olduğuydu. O an kapının arkasındaki şeyin yalnızca bazı anıları bildiğini anladım.

Mutfaktaki anahtarlığı almak için geri döndüm. Masanın üzerinde değildi. Zeminde, merdivenlerin başladığı yere doğru uzanan ıslak lekeler vardı. Ayak izi şeklinde değillerdi; sanki su damlayan bir bez sürüklenmişti. Lekeler ilk basamakta bitiyordu. Üst kata çıkmak istemedim ama anahtarlık tam üçüncü basamağın üzerinde duruyordu. Eğilip alırken yukarıdaki koridordan bir tahta gıcırtısı geldi. Sonra çocukluğumuzdaki odamızın kapısı yavaşça kapandı.

Evdeki bütün pencereleri ve kapıları ben kontrol etmiştim. Üst katın pencereleri içeriden mandallıydı. Yine de el fenerini açıp merdivenleri çıktım. Her basamakta dış kapıdan gelen Emre’nin sesi biraz daha uzaktan duyuluyordu. Aynı anda üst kattaki odadan da çok hafif bir nefes sesi gelmeye başladı. İki farklı yerde aynı varlığın olamayacağını düşündüm. Sonra bunun yanlış bir varsayım olduğunu fark ettim. Belki dışarıdaki ses beni kapıya çağırırken içerideki şey hareket ediyordu.

Odamızın kapısını açmadım. Kapının altından bakınca içeride karanlık dışında bir şey görünmüyordu. Tam geri dönerken telefonum aşağı katta çaldı. Babam arıyordu. Koşarak aşağı indim. Telefonu açtığımda ilk duyduğum şey babamın sesi değil, derin bir parazit oldu. Sonra babam çok hızlı konuşmaya başladı. Ona anahtarlığı anlattığımda sustu. Uzun bir sessizliğin ardından, “O şeyi neden elledin?” dedi. Babamın bu tepkiyi vereceğini beklemiyordum.

Babam, dedemin yıllar önce aynı evde yaşadığı bir olayı anlattı. Köyün arkasındaki ormanda, dere yatağının yakınında eski bir taş kuyu varmış. Dedem gençken o kuyudan başka şehirdeki kız kardeşinin sesini duymuş. Sesi takip ederken ev anahtarlarını çamura düşürünce çağrı bir anda kesilmiş. Köyün yaşlılarından biri ona, bazı varlıkların insanın sesini değil, “evine dönüş yolunu” taklit ettiğini söylemiş. Anahtar, kapı ve tanıdık ses aynı hikâyenin parçalarıymış.

Babamın anlattığına göre dedem o geceden sonra metal anahtarlığa bir işaret kazımış ve onu evde saklamış. Emre yıllar sonra anahtarlığı bulmuş. Kazadan önce evde duyduğu benim sesimden korkunca anahtarlığı yanında taşımaya başlamış. Babam, kazadan sonra anahtarlığın kaybolduğunu sandığını söyledi. “Eğer şimdi evdeyse,” dedi, “o şey seni dışarı çıkarmaya çalışmıyor olabilir. Belki içeri girmek için senden izin almaya çalışıyordur.”

Tam bu cümleyi duyduğum anda mutfaktaki lamba söndü. Koridorda yalnızca telefon ekranının ışığı kaldı. Dış kapının arkasındaki Emre sesi değişti. Ağlamaya başladı. “Abi, lütfen,” dedi. “Kapıyı açmazsan burada kalacağım.” Sonra üst kattaki odadan aynı anda başka bir Emre sesi geldi: “Sakın açma.” İki ses birbirine cevap veriyordu. Dışarıdaki yalvarıyor, içerideki uyarıyordu. Hangisinin taklit olduğunu anlamaya çalışırken babam telefonda tek bir şey söyledi: “Anahtarlıktaki işarete bak.”

Telefonun ışığını metal parçaya tuttum. Arka yüzünde üç ince çizginin ortasında küçük bir daire vardı. Çocukken bunu çizik sanmıştım. Babam, dedemin işaretinin tam olarak bu olduğunu söyledi. “Onu evin eşiğine bırak,” dedi. “Ama kapıyı açma.” Eşiğe yaklaşınca dışarıdaki ses aniden sustu. Anahtarlığı kapının hemen iç tarafına, taş zemine bıraktım. Metal değdiği anda üst kattaki odanın kapısı büyük bir gürültüyle açıldı.

Merdivenin başında bir gölge belirdi. İnsan şeklindeydi ama yüzü seçilmiyordu. El fenerini kaldırdığımda gölge geri çekilmedi; aksine bir basamak aşağı indi. O sırada dış kapıdan bu kez benim sesim geldi. Kendi sesim, dışarıdan bana “Yukarı bakma” diyordu. Merdivendeki gölge başını yana eğdi. Ben hiç hareket etmedim. Babam hâlâ telefondaydı fakat onun sesi uzaklaşmış gibi geliyordu. Sonra bağlantı koptu.

Salondaki eski dolapta mum olduğunu hatırladım. Elektrik tamamen gitmişti. Dolabı açıp yarısı yanmış kalın bir mum ve kibrit buldum. Mumu yakar yakmaz merdivendeki gölge kayboldu. Fakat odanın köşelerinde, ışığın ulaşmadığı yerlerde ince tıkırtılar başladı. Her tıkırtıdan sonra evin başka bir yerinden tanıdığım bir ses yükseliyordu. Annemin sesi mutfaktan adımı söyledi. Babamın sesi üst kattan cevap verdi. En sonunda Emre’nin sesi, tam arkamdaki koridordan, “Beni dinle,” dedi.

Dönmedim. Ses yaklaşmadı. Sadece konuşmaya devam etti. “Kazadan önce ben de kapıyı açmadım,” dedi. “Ama anahtarlığı dışarı götürdüm. Hata buydu.” Bu cümle beni durdurdu. Çünkü babam, Emre’nin anahtarlığı yanında taşıdığını söylemişti. Eğer içerideki ses sadece taklit ediyorsa, babamla yaptığım konuşmayı duymuş ve bu bilgiyi kullanmış olabilirdi. Fakat ardından söylediği şey daha özeldi. Emre, kazadan bir gün önce bana gönderip sonra sildiği bir ses mesajından bahsetti. O mesajı yalnızca ben dinlemiştim. İçinde “Bazen insanın kendi sesi en yabancı ses oluyor,” demişti.

Kapının dibindeki anahtarlık titremeye başladı. Gerçekten hareket ediyordu; taşın üzerinde küçük küçük sıçrıyordu. Dışarıdaki benim sesim öfkeli biçimde kapıyı açmamı söylüyordu. İçerideki Emre sesi ise, “Anahtarlığı pencereye götür,” dedi. Ne yapacağımı bilmiyordum. Sonunda bir karar verdim: hiçbir sese güvenmeyecektim. Anahtarlığı yerinden kaldırmadım. Mumla birlikte salonun ortasında bekledim ve polisi aradım.

Gece üç on beşi geçerken ev tamamen sessizleşti. Ben bunun iyi bir şey olduğunu düşündüm. Sonra ayakkabılığın üzerindeki telefonun kayıt yaptığını hatırladım. Cihazı aldığımda ekranda ses dalgası hâlâ hareket ediyordu. Kulaklığı takmadan kaydı birkaç saniye oynattım. Kaydın başında kapının dışındaki Emre sesi net biçimde duyuluyordu. Fakat benim ona soru sorduğum bölümde, kendi sesimin arkasında ikinci bir fısıltı vardı. O fısıltı “Kapıyı açma, o ben değilim” diyordu. Bunu olay sırasında duymamıştım.

Daha korkuncu, kayıt ilerledikçe fısıltının konumu değişiyordu. İlkinde uzaktan geliyordu. Sonraki cümlelerde giderek yaklaşıyordu. Son kayıtta ise mikrofonun hemen yanında, neredeyse telefonun üstündeydi. Kaydı durdurdum. Ayakkabılığın yanındaki aynaya bakınca arkamda kimse yoktu. Fakat mumun alevi, koridor tarafından biri nefes veriyormuş gibi bana doğru eğiliyordu.

Dışarıdan araç sesi geldiğinde polislerin geldiğini anladım. Kapıyı yine açmadım. Onlara telefondan, kapının önünde biri olup olmadığını sordum. Komiser, bahçede kimseyi görmediklerini söyledi. Kapının içindeki anahtarlığı anlatınca içeriden geri çekilmemi istedi. Sonra polisler kapıyı zorlayarak açtı. Kapı açıldığı anda anahtarlık yerinden fırlayıp koridorun sonuna kadar kaydı. Mum aynı anda söndü.

Üç polis evi aradı. Üst katı, dolapları, çatıyı ve arka bahçeyi kontrol ettiler. Kimseyi bulamadılar. Pencerelerin tamamı içeriden kapalıydı. Çamurda yalnızca polislerin yeni ayak izleri vardı. Komiser ses kaydını dinlemek istedi. “Kapıyı açma, o ben değilim” cümlesine geldiğinde yüzü değişti. Çünkü kayıtta benim arkamda başka bir ses daha vardı ve o ses artık Emre’ye benzemiyordu. Çok daha kalın, boğuk bir ses aynı cümleyi tekrar ediyordu.

Sabah babam eve geldi. Anahtarlığı gördüğü anda onu eline almadı. Bir bezle sardı ve metal bir kutuya koydu. Sonra beni köyün arkasındaki ormana götürdü. Dere yatağına vardığımızda çocukken hiç görmediğim eski taş kuyuyu bulduk. Kuyunun ağzı yıllar önce betonla kapatılmıştı. Betonun üzerinde, anahtarlıktakiyle aynı üç çizgi ve daire işareti vardı. Babam anahtarlığı kuyunun üzerine bırakmadı. Tam tersine, “Bu işaret onu hapsetmek için değil, yolu hatırlatmamak içinmiş,” dedi.

O gün anahtarlığı eritip yok etmedik. Babam, metalin zarar görmesi halinde aynı seslerin yeniden ortaya çıkacağından korktu. Onu köyden uzak bir yerde, kullanılmayan bir banka kasasına koydu. Aile evini de satmadık. Kapısının kilidini değiştirdik ve kimsenin gece içeride kalmamasına karar verdik.

Aradan aylar geçti. Bir süre hiçbir şey olmadı. Sonra geçen hafta telefonuma bilinmeyen bir numaradan on bir saniyelik bir ses mesajı geldi. Mesajda yağmur sesi vardı. Ardından eski aile evinin kapı tokmağı üç kez vuruldu. Son iki saniyede Emre’nin sesi çok sakin biçimde, “Abi, bu kez kapıyı ben açtım,” dedi.

Mesajı dinlediğim anda babamı aradım. Banka kasasını kontrol ettiklerinde kutunun yerinde olduğunu söylediler. Ancak kutunun içindeki anahtarlık kayıptı. Aynı gece köydeki komşumuz bizi aradı. Aylarca boş duran evin üst katındaki odada bir mum ışığı gördüğünü söyledi. Ben o eve tekrar gitmedim. Çünkü artık kapının hangi tarafında olduğumuzdan emin değilim.'''

report = {
    'version': 4,
    'engine_version': 'V4-fixed-15-test',
    'preview': False,
    'human_review_required': True,
    'story_words': len(STORY.split()),
    'target_minutes': 15,
    'editor_review': {'issues': [], 'pass': True, 'mode': 'curated deterministic test story'},
    'voice_name': 'Serkan Demirci - synthetic reference',
    'narration_mode': 'single-stream TTS + whole-file voice conversion',
    'audio_chunk_merge': False,
    'opening_mode': 'direct hook',
}
state = {'title': TITLE, 'parts': [STORY], 'report': report, 'minutes': 15}
(OUT / 'story.txt').write_text(STORY, encoding='utf-8')
(OUT / 'story_only.txt').write_text(STORY, encoding='utf-8')
(OUT / 'intro.txt').write_text('', encoding='utf-8')
(OUT / 'quality_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
(OUT / 'state.json').write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
print(f'15 dakikalik sabit test hikayesi hazir: {report["story_words"]} kelime')
