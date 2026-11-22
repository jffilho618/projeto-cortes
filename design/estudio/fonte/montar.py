import re, math, pathlib
src=pathlib.Path(__file__).resolve().parent; out=src.parent
c=(src/'comum.html').read_text(encoding='utf-8')
sprite=c.split('<!--SPRITE-->')[1].split('<!--SIDE-->')[0].strip()
side=c.split('<!--SIDE-->')[1].split('<!--SCRIPT-->')[0].strip()
script=c.split('<!--SCRIPT-->')[1].strip()
cortes=[(1,'Alanzoka descobre a mecânica de banho interativo no GTA 6 e testa os limites','ouro','descoberta_detalhe','50,9 s',''),
(3,'O detalhe insano do GTA 6 que deixou o alanzoka sem acreditar','ouro','descoberta_detalhe','56,1 s','publicado · Shorts'),
(4,'A Rockstar corrigiu o erro da cerveja do trailer de GTA 6 — alanzoka conferiu','ouro','callback_oculto','22 s',''),
(6,'Alanzoka testa a IA do GTA 6 e lembra de um detalhe que Sleeping Dogs fazia melhor','ouro','callback_oculto','28,2 s',''),
(7,'Por que muita gente vai odiar o GTA 6 segundo o alanzoka','ouro','polemica_hottake','52,4 s',''),
(9,'NPC se revolta no GTA 6, taca gasolina no alanzoka e explode o próprio carro','ouro','deadpan_karma','1 min 11',''),
(10,"Alanzoka se distrai de novo no GTA 6 e elogia o 'dev do chinelo'",'ouro','descoberta_detalhe','47,1 s',''),
(13,"Alanzoka diz 'ninguém sabe quem eu sou' e foge direto pro departamento de polícia",'ouro','deadpan_karma','46,7 s',''),
(2,'GTA 6 cai pra 24 FPS no PS5 normal? Alanzoka reage à performance nos consoles','forte','polemica_hottake','1 min 28',''),
(5,'Alanzoka tenta fugir de tiroteio no GTA 6 e transforma tudo num desastre','forte','clutch_fail','1 min 27',''),
(8,'Chat manda o alanzoka parar de ler celular no GTA 6 e toma invertida','forte','chat_trolagem','18,9 s',''),
(11,'Alanzoka capota o carro e surta com a mira no controle no GTA 6','forte','rage_tilt','1 min 25','publicado · Shorts'),
(12,'Chat reclama do brilho no GTA 6 e alanzoka manda a real sobre o PS5 Pro','forte','chat_trolagem','46,8 s',''),
(15,'O chat tentou convencer o alanzoka de que a roupa sumiu no GTA 6','exp','chat_trolagem','50,9 s',''),
(14,'Alanzoka tenta zerar GTA 6 no modo pacifista e já perde o fôlego correndo','exp','deadpan_karma','1 min 02','descartado · desfazer')]
nome={'ouro':'Ouro','forte':'Forte','exp':'Experimental'}
itens=[]
for i,(n,t,tier,arq,dur,extra) in enumerate(cortes):
    cls='item'+(' desc' if 'descartado' in extra else '')
    cur=' aria-current="true"' if i==0 else ''
    rot='<span class="est ok"><svg class="ic s"><use href="#i-polegar"/></svg>rotulado</span>' if n==3 else ''
    ex=f'<span>{extra}</span>' if extra else ''
    star=''
    itens.append(f'<article class="{cls}"{cur}><span class="plaq num">Nº {n:02d}</span><div><h3>{t}</h3><div class="lin"><span class="tier {tier}">{star}{nome[tier]}</span><span>{arq}</span><span class="num">{dur}</span>{ex}{rot}</div></div></article>')
bars=[]; W=600; N=150
for k in range(N):
    x=k*W/N; a=0.35+0.3*math.sin(k*0.37)+0.25*math.sin(k*1.7+1)+0.2*math.sin(k*0.11)
    if 52<k<62: a+=0.45
    h=max(4,min(70,a*52)); y=(74-h)/2
    sel=24<=k<=118
    bars.append(f'<rect x="{x:.1f}" y="{y:.1f}" width="2.4" height="{h:.1f}" rx="1.2" fill="{"var(--acao-texto)" if sel else "var(--fio-forte)"}"/>')
onda=f'<svg viewBox="0 0 {W} 74" preserveAspectRatio="none" aria-label="Forma de onda do trecho">{"".join(bars)}</svg><span class="alca" style="left:calc(12px + (100% - 24px)*0.16)"></span><span class="alca" style="left:calc(12px + (100% - 24px)*0.787)"></span>'
import sys
sys.path.insert(0, str(src))
import dados
for nm in ['lives','sala','revisao']:
    s=(src/f'{nm}.html').read_text(encoding='utf-8')
    m=re.search(r'<!--@SIDE:(\w+)-->',s); k=m.group(1)
    sd=side.replace(f'data-k="{k}"',f'data-k="{k}" aria-current="page"')
    s=s.replace(m.group(0),sd).replace('<!--@SPRITE-->',sprite).replace('<!--@SCRIPT-->',script)
    for k_,v_ in dados.TRECHOS.items(): s=s.replace(k_,v_)
    (out/f'{nm}.html').write_text(s,encoding='utf-8'); print(nm, len(s.splitlines()))
