
from orthography import *
f = Orthography(u"[a,\u00e1],h,[i,\u00ed],k,m,n,[o,\u00f3],p,s,t,w,y,'", lowercase=False,
                initialGlottalStops=False)
af = Orthography(u"[e,\u00e9],x,[u,\u00fa],c,w,d,[oo,\u00f3\u00f3],b,sh,k,m,j,\u0294", lowercase=False,
                initialGlottalStops=True)

t = OrthographyTranslator(f, af)
result = t.translate("b")
print result
print len(result)