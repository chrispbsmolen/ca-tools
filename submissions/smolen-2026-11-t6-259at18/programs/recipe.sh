#!/bin/sh
# Recipe for CA(259;6,18,2). Needs python 3.13 and python-sat 1.9.dev22 (CaDiCaL 1.5.3). Deterministic, no seeds.
OUT=CA_259_6_18_2_replay.txt python3 eager.py 8 100000 2 2 4 4 8 8 8
sha256sum CA_259_6_18_2_replay.txt   # b3d1da58e030b02ef5f38bc0cbbb4c7aa54241807048d9add72a894d9c0318a5 (rows written without spaces)
sed 's/./& /g; s/ $//' CA_259_6_18_2_replay.txt > CA_259_6_18_2.txt
sha256sum CA_259_6_18_2.txt          # 0895a51ad5ab45a5425cccac68a701e237f408cc63d4503549942247efdf6e84 (the submitted file)
