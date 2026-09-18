"""Generate KAYIP FREKANS_ original Turkish adaptations grounded in a verified web story."""
from __future__ import annotations
import argparse,json,os,re,time,urllib.error,urllib.request
from pathlib import Path
import bot,cloud_v3,mpt_profile,mpt_reference_style,mpt_story_recovery,mpt_web_story
_ACTIVE_WEB_STORY=None

def _ground_prompt(prompt):
 source=_ACTIVE_WEB_STORY
 if not source:return prompt
 chapter=re.search(r"Bölüm\s+(\d+)\s*/\s*(\d+)\s+olay planı",prompt)
 if chapter:
  i,n=int(chapter.group(1))-1,int(chapter.group(2));return prompt+"\n\n"+mpt_web_story.source_excerpt(source,i,n)
 if "DÖRT ana dönüm noktasını planla" in prompt:
  return prompt+"\n\nKAYNAKTAN BAŞLANGIÇ:\n"+mpt_web_story.source_excerpt(source,0,6)+"\n\nKAYNAKTAN FİNAL:\n"+mpt_web_story.source_excerpt(source,5,6)+"\nÖzgün Türkçe uyarlama için gerçek kaynak olay sırasını koru; gerçek yaşanmış vaka diye sunma."
 return prompt

def stable_ask(prompt,structured=False):
 last=None;prompt=_ground_prompt(prompt)
 for attempt,delay in enumerate((0,8,18,30),1):
  if delay:time.sleep(delay)
  budget=3200 if attempt<=2 else 4000
  payload={"model":os.getenv("KF_STORY_MODEL","gemma3:4b"),"stream":False,"keep_alive":"30m","messages":[{"role":"system","content":cloud_v3.SYSTEM},{"role":"user","content":prompt}],"options":{"num_ctx":6144,"num_predict":budget,"num_thread":2,"temperature":0.68,"repeat_penalty":1.15}}
  if structured:payload["format"]="json"
  req=urllib.request.Request("http://127.0.0.1:11434/api/chat",data=json.dumps(payload,ensure_ascii=False).encode(),headers={"Content-Type":"application/json"})
  try:
   print(f"Model yanıtı bekleniyor ({attempt}/4, token={budget}).",flush=True)
   with urllib.request.urlopen(req,timeout=600) as r:result=json.load(r)
   if result.get("done_reason")=="length":raise ValueError("Metin token sınırında kesildi")
   text=str(result["message"]["content"]).strip()
   if not text:raise ValueError("Model boş yanıt verdi")
   return json.loads(text) if structured else text
  except (urllib.error.HTTPError,urllib.error.URLError,TimeoutError,json.JSONDecodeError,KeyError,ValueError) as exc:
   last=exc;print(f"Ollama tekrar denenecek ({attempt}/4): {type(exc).__name__}: {str(exc)[:160]}",flush=True)
 raise RuntimeError(f"Ollama dört denemede yanıt veremedi: {last}") from last

def _write(path,value):
 path.parent.mkdir(parents=True,exist_ok=True);path.write_text(value if isinstance(value,str) else json.dumps(value,ensure_ascii=False,indent=2),encoding="utf-8")

def _quality_review(story,topic,minutes,output):
 errors=[]
 for n in range(1,4):
  raw=stable_ask(mpt_reference_style.quality_prompt(story,topic,minutes),structured=True);_write(output/f"reference_style_quality_attempt_{n}.json",raw)
  try:
   q=mpt_reference_style.validate_quality(raw);_write(output/"reference_style_quality.json",{"raw":raw,"validated":q,"review_attempt":n});return q
  except ValueError as exc:
   msg=str(exc)
   if msg.startswith("Reference-style story quality gate failed:"):raise
   errors.append(msg[:300]);print(f"Kalite editörü geçersiz puan/şema döndürdü; tamamlanan hikâye korunup kontrol yeniden deneniyor ({n}/3): {msg[:180]}",flush=True)
 _write(output/"reference_style_quality.json",{"status":"reviewer_unavailable","errors":errors});raise RuntimeError("Bağımsız 8 ölçütlü kalite editörü üç denemede geçerli puan üretemedi")

def compose(topic,minutes,output):
 global _ACTIVE_WEB_STORY
 if not 15<=minutes<=20:raise ValueError("Serious long test target must be 15-20 minutes")
 output.mkdir(parents=True,exist_ok=True);_ACTIVE_WEB_STORY=mpt_web_story.fetch_story(topic);source=_ACTIVE_WEB_STORY
 source_meta={k:v for k,v in source.items() if k!="story_text"} if source else {"retrieved":False,"mode":"original_fiction_fallback","reason":"No verified public-domain story was available"};_write(output/"story_source.json",source_meta)
 if source:_write(output/"story_source_credit.txt","Kamu malı özgün eser uyarlaması: "+source["author"]+" — "+source["title"]+"\nKaynak: "+source["url"]+"\nBu video kaynak eserin özgün Türkçe korku uyarlamasıdır; gerçek yaşanmış olay olarak sunulmaz.\n")
 else:_write(output/"story_source_credit.txt","Özgün kurmaca; doğrulanabilir kamu malı tam hikâye bulunamadı.\n")
 research=mpt_reference_style.gather_research(topic);_write(output/"research_sources.json",research);context=mpt_reference_style.research_prompt(research);cloud_v3.SYSTEM += "\n\n"+mpt_reference_style.STYLE_BRIEF+"\n\nARAŞTIRMA BAĞLAMI:\n"+context[:3200]+("\n\nBu bir kaynak eser UYARLAMASIDIR; gerçek yaşanmış olay diye sunma." if source else "")
 failures=[]
 for attempt in range(1,3):
  revised=topic+(("\nÖnceki taslakta düzeltilecek sorun: "+failures[-1][-350:]) if failures else "")
  try:
   title,parts,report=mpt_story_recovery.generate_story(revised,minutes,stable_ask,output,research_context=context,max_story_attempts=1)
   if len(parts)<2:raise ValueError("Uzun hikâyede bölüm yok")
   intro=parts[0].strip();chapters=[p.strip() for p in parts[1:] if p.strip()];story_only="\n\n".join(chapters);story_check=mpt_profile.check_story(story_only,minutes,preview=False);quality=_quality_review(story_only,topic,minutes,output)
   first=bot.sentences(chapters[0])
   if len(first)<3:raise ValueError("Açılışta yeterince cümle yok")
   hook=[];hook_words=0;split_at=0
   for i,s in enumerate(first):
    hook.append(s);hook_words+=len(s.split());split_at=i+1
    if hook_words>=38 and i>=1:break
   if hook_words<25:raise ValueError("Açılış kancası çok kısa")
   rest=" ".join(first[split_at:]).strip();np=[" ".join(hook),intro]+([rest] if rest else [])+chapters[1:];narration="\n\n".join(np).strip()
   if narration.casefold().startswith("merhaba"):raise ValueError("Kanal açılışı korku kancasından önce yerleştirilmiş")
   if "Kayıp Frekans" not in intro:raise ValueError("Kanal tanıtımı eksik")
   break
  except (ValueError,RuntimeError,KeyError,TypeError) as exc:
   failure=f"Baştan üretim {attempt}/2: {type(exc).__name__}: {str(exc)[:750]}";failures.append(failure);_write(output/"recovery_failures.json",failures);print("Hikâye kalite/üretim hatası; baştan yazılacak: "+failure,flush=True)
   if attempt==2:raise RuntimeError("Hikâye iki tam taslak ve bölüm onarımlarından sonra da kaliteyi sağlayamadı; eksik/kötü hikâye seslendirmeye gönderilmedi. "+failure) from exc
   time.sleep(5)
 _write(output/"story.txt",story_only+"\n");_write(output/"narration_script.txt",narration+"\n");state={"title":title,"topic":topic,"target_minutes":minutes,"story_words":len(story_only.split()),"narration_words":len(narration.split()),"hook_words":hook_words,"intro":intro,"story_check":story_check,"reference_style_quality":quality,"research":research,"editor_report":report,"recovery_failures":failures,"full_story_attempt":attempt,"hook_first":True,"channel_intro_after_hook":True,"internet_research_used":bool(research.get("items")),"internet_story_used":bool(source),"story_source":source_meta,"source_story_copied":False,"source_story_adapted":bool(source),"youtube_uploaded":False};_write(output/"story_state.json",state);print(json.dumps({"title":title,"story_words":state["story_words"],"reference_style_score":quality["total"],"internet_story_used":bool(source)},ensure_ascii=False),flush=True);return state

if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("--topic",required=True);p.add_argument("--minutes",type=int,default=15);p.add_argument("--output",type=Path,default=Path("output/long-test"));a=p.parse_args();compose(a.topic,a.minutes,a.output)
