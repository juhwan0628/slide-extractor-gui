"""C5 conservative identity experiment; never deletes chronological occurrences."""
import hashlib
import numpy as np

def link_occurrences(frames):
    known=[];records=[]
    for occurrence,frame in enumerate(frames):
        digest=hashlib.sha256(str(frame.shape).encode()+str(frame.dtype).encode()+frame.tobytes()).hexdigest()
        exact=next((i for i,(h,a) in enumerate(known) if digest==h and np.array_equal(frame,a)),None)
        candidates=[(float(np.mean(abs(frame.astype(np.int16)-a.astype(np.int16)))/255),i) for i,(_,a) in enumerate(known) if a.shape==frame.shape]
        distance,nearest=min(candidates) if candidates else (None,None)
        if exact is None:
            identity=len(known);known.append((digest,frame.copy()));revisit=None
        else:
            identity=exact;revisit=next(r['occurrence'] for r in records if r['identity']==identity)
        records.append({'occurrence':occurrence,'identity':identity,'revisit_of':revisit,
            'similar_candidate':nearest if exact is None and distance is not None and distance<.02 else None,
            'candidate_distance':distance,'exact_hash':digest})
    return records
