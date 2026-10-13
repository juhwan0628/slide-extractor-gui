"""Research-only representative ranking; dark marks are not semantic labels."""
import numpy as np

def choose_representative(gray,valid):
    if gray.ndim!=3 or len(gray)==0 or valid.shape!=gray.shape[1:] or not valid.any():
        raise ValueError('Nonempty observations and matching valid mask required')
    # Brightest observed per-pixel reference keeps even late accumulated dark marks.
    reference=gray.max(axis=0).astype(np.int16)
    marks=((reference[None]-gray.astype(np.int16))>20)&valid
    supported=marks.sum(axis=0)>=min(2,len(gray))
    retained=(marks&supported).sum(axis=(1,2))
    transient=(marks&~supported).sum(axis=(1,2))
    # Recurrent static edges expose overlays that hide pre-existing text/diagrams.
    edges=np.zeros_like(gray,dtype=bool)
    edges[:,:,1:]|=abs(np.diff(gray.astype(np.int16),axis=2))>25
    edges[:,1:,:]|=abs(np.diff(gray.astype(np.int16),axis=1))>25
    edges&=valid
    core=edges.sum(axis=0)>=max(1,int(np.ceil(len(gray)*.6)))
    missing_edges=(core&~edges).sum(axis=(1,2))
    occluded=[]
    for i in range(len(gray)):
        tiles=set()
        lost=core&~edges[i]
        for y in range(0,gray.shape[1],20):
            for x in range(0,gray.shape[2],20):
                mask=valid[y:y+20,x:x+20]
                if mask.any() and marks[i,y:y+20,x:x+20].sum()/mask.sum()>=.25 and lost[y:y+20,x:x+20].sum()>=8:
                    tiles.add((y//20,x//20))
        # Adjacent filled regions erasing core edges are an overlay hypothesis.
        occluded.append(sum(any((y+dy,x+dx) in tiles for dy,dx in ((1,0),(-1,0),(0,1),(0,-1))) for y,x in tiles))
    eligible=np.asarray(occluded)==min(occluded)
    score=np.where(eligible,retained-.25*transient,-np.inf)
    best=max(range(len(gray)),key=lambda i:(float(score[i]),i))
    missing=int((supported&~marks[best]).sum())
    return {'index':best,'supported_pixels':int(supported.sum()),
            'retained_supported_pixels':int(retained[best]),'missing_supported_pixels':missing,
            'transient_pixels':int(transient[best]),'missing_core_edges':int(missing_edges[best]),'occlusion_tiles':int(occluded[best]),
            'missing_supported_fraction':float(missing/valid.sum()),
            'single_observation':len(gray)==1}
