"""V5: choose varied but contextually supported horror scene illustrations."""
import json
import sys
from collections import Counter
from pathlib import Path

CUES = {
    'door': ('kapıyı','kapının','kapıdan','kapıya','kilit','tokmak','eşik'),
    'room': ('dolap','yatak','mutfak','masa','telefon','sandık','odam','odayı','odanın'),
    'corridor': ('koridor','duvar','ses','fısıltı','ayak','karanlık','sessiz'),
    'window': ('pencere','perde','camdan','camın','dışarı baktım'),
    'stairs': ('merdiven','basamak','bodrum'),
    'forest': ('orman','ağaç','patika'),
    'candle': ('mum','alev','kibrit'),
    'house': ('bahçe','avlu','evin ön','çatı','köy yolu'),
}


def balance(segments):
    previous=[]
    counts=Counter()
    for segment in segments:
        content=segment['text'].casefold()
        tail=content[-250:]
        scores={key:sum((3 if w in tail else 1) for w in words if w in content)
                for key,words in CUES.items()}
        active=[k for k,value in scores.items() if value]
        if not active:
            active=['room','corridor','door']
            scores.update({k:1 for k in active})
        if 'door' in active and not ({'forest','stairs'} & set(active)):
            for k in ('room','corridor'):
                if k not in active:
                    active.append(k)
                    scores[k]=.6
        def weight(k):
            return scores[k]-.65*counts[k]-(5 if previous[-2:]==[k,k] else 0)
        kind=max(active,key=lambda k:(weight(k),-counts[k]))
        segment['kind']=kind
        previous.append(kind)
        counts[kind]+=1
    return dict(counts)


if __name__=='__main__':
    directory=Path(sys.argv[1]) if len(sys.argv)>1 else Path('output')
    statefile=directory/'state.json'
    state=json.loads(statefile.read_text(encoding='utf-8'))
    counts=balance(state['segments'])
    (directory/'scene_plan.json').write_text(json.dumps(state['segments'],ensure_ascii=False,indent=2),encoding='utf-8')
    statefile.write_text(json.dumps(state,ensure_ascii=False,indent=2),encoding='utf-8')
    print('V5 gorsel sahneler:',counts,flush=True)
