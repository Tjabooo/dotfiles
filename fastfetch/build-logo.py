#!/usr/bin/env python3
# Builds unit01.ans (truecolor half-block logo) from unit01.pix.
# unit01.pix is the LEFT half of the pixel map; it is mirrored. Letters = palette below, . = empty.
# Usage: ./build-logo.py   (then fastfetch picks up unit01.ans)
import sys, os
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.argv=[sys.argv[0],"unit01.pix","unit01.ans"]
PAL={'K':(30,20,56),'V':(155,93,229),'D':(94,53,168),'L':(200,160,255),'G':(158,240,26),'g':(95,160,16),'Y':(232,255,106),'P':(241,91,181),'p':(150,50,120)}
L=[l.rstrip('\n') for l in open(sys.argv[1]) if not l.startswith('#')]
HW=max(len(l) for l in L); rows=[]
for l in L:
    l=l.ljust(HW,".")[:HW]; rows.append(l+l[::-1])
H=len(rows); W=2*HW
grid=[list(r) for r in rows]
if H%2: grid.append(['.']*W); H+=1
out=[]
for y in range(0,H,2):
    s=''
    for x in range(W):
        a,b=grid[y][x],grid[y+1][x]
        if a=='.' and b=='.': s+='\x1b[0m '
        elif a=='.': s+='\x1b[0m\x1b[38;2;%d;%d;%dm▄'%PAL[b]
        elif b=='.': s+='\x1b[0m\x1b[38;2;%d;%d;%dm▀'%PAL[a]
        elif a==b: s+='\x1b[0m\x1b[38;2;%d;%d;%dm█'%PAL[a]
        else: s+='\x1b[38;2;%d;%d;%dm\x1b[48;2;%d;%d;%dm▀'%(PAL[a]+PAL[b])
    out.append(s+'\x1b[0m')
open(sys.argv[2],'w').write('\n'.join(out)+'\n')

