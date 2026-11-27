#!/usr/bin/env python3
import argparse
import collections
import csv
import datetime
import html
import json
import os
import re
import subprocess
import sys
import unicodedata

E = html.escape
BASE = "https://coveringarraytools.org/"
DOI = "10.5281/zenodo.24168008"
REPO_URL = "https://github.com/chrispbsmolen/ca-tools"
RAW = "https://raw.githubusercontent.com/chrispbsmolen/ca-tools/main/"
CONTACT = "contact@coveringarraytools.org"
SNAPSHOT_DATE = "2026-08-23"
SERIF = "Charter,'Bitstream Charter','Iowan Old Style',Georgia,serif"
NAV = [("Table", ""), ("Lower bounds", "bounds/"), ("Methods", "methods/"), ("Library", "library/"),
       ("Contributors", "contributors/"), ("Updates", "changelog/"), ("Learn", "learn/")]

METHOD_TITLES = {'KSK': 'Kleitman-Spencer and Katona', 'PALEY': 'Paley matrices', 'CAEX': 'CA Extender', 'CYCLOTOMY': 'Cyclotomy', 'CKRS': 'Colbourn, Kéri, Rivas Soriano and Schlage-Puchta', 'RMScopiesCA': 'Raaphorst, Moura and Stevens, strength 3 from finite fields', 'miscCA': 'Single stored arrays', 'recBoseCA_PCA': 'Recursive Bose, partitioned', 'recBoseCA_CA': 'Recursive Bose', 'SCA_Busht': 'Orthogonal arrays of index one (Bush, Bose)', 'fuseBoseCA': 'Fused Bose orthogonal arrays', 'fuseBushtCA': 'Fused Bush orthogonal arrays', 'projBoseCA': 'Projected Bose orthogonal arrays', 'compositCA': 'Composition of alphabets', 'WKS': 'Wagner, Kampel and Simos, strength 6', 'CS_MS': 'Cover starters of Meagher and Stevens', 'CS_LCDST': 'Cover starters of Lobb, Colbourn, Danziger, Stevens and Torres-Jimenez', 'CS_CK': 'Cyclic binary arrays of Colbourn and Kéri', 'powerCT': 'Power construction (Colbourn and Torres-Jimenez)', 'DWYER': "Dwyer's CA_Database", 'NIST': 'NIST covering array library (IPOG-F)', 'TJ': 'Torres-Jimenez binary arrays', 'CK_doublingCA': 'Chateauneuf-Kreher doubling', 'CK_NRB': 'Chateauneuf, Colbourn and Kreher group construction', 'FullFactorial': 'Full factorial', 'CS_CMMSSY': 'Cover starters of Colbourn, Martirosyan, Mullen, Shasha, Sherwood and Yucas', 'ODbasedCA': 'Ordered designs', 'pcaCA': 'Product of partitioned covering arrays', 'dpCA': 'Direct product', 'scphfCA': 'Sherwood covering perfect hash families', 'cphfCA': 'Covering perfect hash families', 'dpGeneralized': 'Generalized direct product', 'profileProduct': 'Product from profiles', 'powerNCT': 'Power N-CT', 'powerCZ': 'Power construction with quilted arrays (Colbourn and Zhou)', 'PHF': 'Perfect hash families', 'CMTW': 'Roux-type, Colbourn, Martirosyan, Trung and Walker', 'MTVT': 'Roux-type, Martirosyan and Tran Van Trung', 'MC': 'Martirosyan and Colbourn', 'CCL': 'Strength 3 from two strength 2 arrays (Cohen, Colbourn and Ling)', 'add1': 'Add factors', 'addFactor': 'Add a factor, other forms', 'addSymbol': 'Add a symbol', 'derive': 'Derive from higher strength', 'augmentOA': 'Augmented orthogonal arrays', 'projection': 'Projection', 'transversalDesign': 'Transversal designs and difference matrices', 'density': 'Density algorithms', 'groupOrbit': 'Arrays invariant under a group', 'ShokriMoura': 'Constructions of Shokri and Moura', 'polynomial': 'Polynomial constructions', 'weightClass': 'Weight classes', 'CIJSSS': 'Orthogoval affine planes', 'rouxDoubling': 'Roux doubling', 'annealing': 'Simulated annealing', 'tabu': 'Tabu search', 'SAT': 'SAT solver', 'IPO': 'IPO family algorithms', 'twoStage': 'Two-stage methods', 'columnExtension': 'Column extension', 'postop': 'Post-optimization', 'other': 'Other'}

CSS = """
:root{--side:56px;color-scheme:light;--fg:#1d1d1f;--bg:#fdfdfc;--mute:#5f6368;--line:#dcdcd8;--ver:#0b6e3a;--soft:#f2f2ee;--acc:#1f4e8c;--opt:#5b2a86}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:16px/1.5 system-ui,-apple-system,"Segoe UI",sans-serif}
a{color:inherit}.mute{color:var(--mute)}.num{font-variant-numeric:tabular-nums}.mono{font-family:ui-monospace,SFMono-Regular,Menlo,monospace;font-size:.82rem}
.tag{display:inline-block;font-size:.72rem;font-weight:600;border-radius:4px;padding:0 .35rem;border:1px solid currentColor;line-height:1.45}
.ver{color:var(--ver)}.lit{color:var(--mute)}.opt{color:var(--opt)}.dis{color:#9a4400}a.tag.dis{text-decoration:none;margin-left:4px}
.top{border-bottom:1px solid var(--line);background:#fff}
.top .in{max-width:88rem;margin:0 auto;padding:0 var(--side);height:52px;display:flex;align-items:center;gap:26px;font-size:.9rem}
.top b a{text-decoration:none;font-size:1rem}.top nav{display:flex;gap:20px;color:var(--mute)}.top nav a{text-decoration:none}.top nav a.on{color:var(--fg);font-weight:600}
.top .sp{flex:1}.top .doi{font-size:.78rem;color:var(--mute);border:1px solid var(--line);border-radius:4px;padding:2px 8px;text-decoration:none}
.top .gh{color:var(--mute);text-decoration:none}
.crumb{font-size:.82rem;color:var(--mute);margin:0 0 6px}.crumb a{text-decoration:none}
.foot{border-top:1px solid var(--line);margin-top:48px}
.foot .in{max-width:88rem;margin:0 auto;padding:18px var(--side);font-size:.8rem;color:var(--mute);display:flex;gap:6px 18px;flex-wrap:wrap}
.f4{background:#1f6b45;color:#fff}.f3{background:#5fa77d;color:#1d1d1f}.f2{background:#b9dcc6}.f1{background:#e4efe7}.f0{background:#f1f1ec}
.wrapw{max-width:88rem;margin:0 auto;padding:26px var(--side)}
.key{display:flex;gap:18px;font-size:.78rem;color:var(--mute);margin-top:14px;align-items:center;flex-wrap:wrap}.key i{display:inline-block;width:14px;height:14px;border-radius:3px;vertical-align:-2px;margin-right:6px}
.hero{background:#fff;border-bottom:1px solid var(--line)}.hero .in{max-width:88rem;margin:0 auto;padding:44px var(--side) 36px;display:grid;grid-template-columns:1fr 470px;gap:48px;align-items:center}
.hero h1{font-size:2.5rem;line-height:1.05;margin:0 0 14px;letter-spacing:-.02em}.hero p{margin:0;color:#333;max-width:36rem}
.look{border:1px solid var(--fg);border-radius:10px;padding:20px;background:#fff}.look h2{margin:0 0 12px;font-size:1rem}
.lf{display:grid;grid-template-columns:repeat(3,1fr) 110px;gap:10px;align-items:end}.lf label{font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;color:var(--mute);display:block}
.lf input{width:100%;border:1px solid var(--line);border-radius:6px;padding:8px 10px;font:600 1.1rem system-ui;margin-top:4px}
.lf button{background:var(--fg);color:#fff;border:0;border-radius:6px;padding:12px;font:600 1rem system-ui;cursor:pointer}
.ans{margin-top:14px;background:var(--soft);border-radius:6px;padding:12px 14px;font-size:.9rem;min-height:48px}.ans b{font-size:1.4rem}
.stats{max-width:88rem;margin:0 auto;padding:22px var(--side) 0;display:flex}
.stats div{flex:1;border-left:1px solid var(--line);padding:0 16px}.stats div:first-child{border-left:0;padding-left:0}.stats b{display:block;font-size:1.6rem}.stats span{font-size:.75rem;color:var(--mute);text-transform:uppercase;letter-spacing:.05em}
.blk{display:grid;grid-template-columns:36px repeat(12,minmax(0,1fr));gap:6px;margin-bottom:30px}
.blk .h{font-size:.72rem;color:var(--mute);text-align:center;align-self:end}.blk .r{font-size:1rem;font-weight:700;align-self:center}
.bl{font-size:.72rem;text-transform:uppercase;letter-spacing:.06em;color:var(--mute);margin:0 0 8px 42px}
.el{border-radius:5px;padding:7px 9px 8px;display:grid;grid-template-rows:auto 1fr auto;min-height:104px;cursor:pointer;text-decoration:none;color:inherit}
.el .tp{font-size:.66rem;opacity:.88}.el .n{font-size:1.7rem;font-weight:800;line-height:1;align-self:center;font-variant-numeric:tabular-nums}
.el .n small{font-size:.7rem;font-weight:600;opacity:.88;margin-left:4px}.el .ft{display:flex;flex-direction:column;align-items:flex-start;gap:1px}
.el .st{display:flex;flex-direction:column;font-size:.7rem;line-height:1.35;font-variant-numeric:tabular-nums}.el .st span{white-space:nowrap}
.el .dt{font-size:.64rem;opacity:.88;white-space:nowrap}.el.sel{outline:3px solid var(--fg);outline-offset:2px}.el.none{cursor:default;background:transparent}
.panel{position:fixed;top:120px;right:32px;width:340px;border:2px solid var(--fg);border-radius:10px;background:#fff;padding:18px 20px;box-shadow:0 18px 48px rgba(0,0,0,.18);transform:translateX(130%);transition:transform .25s ease;z-index:10}
.panel.open{transform:none}.panel .hd{display:flex;justify-content:space-between;font-size:.8rem;color:var(--mute)}.panel .x{font-size:1.2rem;color:var(--fg);cursor:pointer;background:none;border:0;line-height:1}
.panel .big{font-size:2.6rem;font-weight:800;line-height:1;letter-spacing:-.02em;margin:10px 0 4px}.panel .nm{font-size:.92rem;margin:0 0 14px;color:#444}
.panel dl{display:grid;grid-template-columns:1fr auto;margin:0;font-size:.88rem}.panel dt,.panel dd{border-top:1px solid var(--line);padding:7px 0;margin:0}.panel dd{text-align:right;font-weight:600;font-variant-numeric:tabular-nums}
.go{display:block;text-align:center;background:var(--fg);color:#fff;border-radius:6px;padding:9px;margin-top:14px;font-weight:600;text-decoration:none}
.pageh{background:#fff;border-bottom:1px solid var(--line)}.pageh .in{max-width:88rem;margin:0 auto;padding:30px var(--side) 24px;display:flex;justify-content:space-between;align-items:end;gap:30px}
.pageh h1{font-size:2.4rem;margin:0;line-height:1.05;letter-spacing:-.02em}.pageh p{margin:6px 0 0;color:#444;max-width:46rem}
.btns{display:flex;gap:8px}.btns a{border:1px solid var(--fg);border-radius:6px;padding:7px 14px;font-size:.85rem;font-weight:600;text-decoration:none;white-space:nowrap}.btns a.d{background:var(--fg);color:#fff}
table.lg{border-collapse:collapse;width:100%;font-size:.88rem}
table.lg th{font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;color:var(--mute);font-weight:600;text-align:left;border-bottom:1px solid var(--fg);padding:8px 10px;position:sticky;top:0;background:var(--bg)}
table.lg td{border-bottom:1px solid var(--line);padding:9px 10px;vertical-align:top}table.lg td.n,table.lg th.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
table.lg td.big{font-weight:800;font-size:1rem}table.lg td.a{white-space:nowrap}table.lg td.rb{min-width:9em}table.lg tr[hidden]{display:none}table.lg a.ck{color:inherit;text-decoration:underline dotted;text-underline-offset:3px}table.lg a.ck{display:inline-block;padding:4px 0}table.lg td.rb .rbi{display:inline-block;padding:4px 0}table.lg td.a a{display:inline-block;padding:4px 0}table.lg tr.closed td{background:#eef6f0}table.lg tr:target td{background:#fff6d6}
.sub{display:block;color:var(--mute);font-size:.78rem}
.lib{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:28px 24px}
.pg{background:#fff;aspect-ratio:1/1.3;box-shadow:0 1px 2px rgba(0,0,0,.08),0 6px 16px rgba(0,0,0,.07);padding:26px 22px 18px;display:flex;flex-direction:column;font-family:@SERIF@;text-decoration:none;color:inherit}
.pg .j{font-family:system-ui,sans-serif;font-size:.62rem;letter-spacing:.06em;text-transform:uppercase;color:var(--mute);border-bottom:1px solid var(--line);padding-bottom:8px;margin-bottom:18px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.pg h2{font-weight:400;font-size:1.15rem;line-height:1.25;text-align:center;margin:0 0 12px}.pg .au{font-size:.85rem;text-align:center;margin:0}
.pg .ln{margin:16px 0 0;display:flex;flex-direction:column;gap:5px}.pg .ln i{display:block;height:4px;background:#d7eadf;border-radius:2px}.pg .ln i:nth-child(3n){width:82%}
.pg .y{margin-top:auto;font-family:system-ui,sans-serif;font-size:.72rem;color:var(--mute);display:flex;gap:12px;justify-content:space-between;border-top:1px solid var(--line);padding-top:8px;white-space:nowrap;overflow:hidden}
.cap{font-size:.8rem;color:var(--mute);margin:8px 2px 0}
.serifh h1{font-family:@SERIF@;font-weight:400;font-size:2.6rem;margin:0 0 8px}.serifh p{font-family:@SERIF@;font-size:1.05rem}
.paper{max-width:none;margin:0}.paper .hd{padding:40px 0 28px;text-align:center;border-bottom:1px solid var(--line)}
.paper .hd .j{font-size:.75rem;letter-spacing:.08em;text-transform:uppercase;color:var(--mute)}
.paper .hd h1{font-family:@SERIF@;font-weight:400;font-size:2.4rem;line-height:1.15;margin:14px 0 12px}.paper .hd .au{font-family:@SERIF@;font-size:1.15rem;margin:0}
.paper .hd .btns{justify-content:center;margin-top:18px}
.paper h2{font-family:@SERIF@;font-weight:400;font-size:1.4rem;margin:30px 0 4px}.paper .lede{font-family:@SERIF@;color:#444;margin:0 0 10px}
.pr{display:grid;grid-template-columns:200px 1fr 170px;gap:16px;padding:9px 0;border-bottom:1px solid var(--line);font-size:.92rem;align-items:baseline}
.pr a{font-weight:700;font-variant-numeric:tabular-nums}.pr .c{color:var(--mute);font-size:.82rem;text-align:right}.pr .k{font-size:.8rem;color:var(--mute);display:block}
.fl{font-family:@SERIF@;font-size:1rem;padding:8px 0;border-bottom:1px solid var(--line)}
.arr{display:grid;grid-template-columns:1fr 360px;gap:40px}
.arr dl{display:grid;grid-template-columns:150px 1fr;margin:0;font-size:.9rem;border-top:1px solid var(--line)}.arr dt,.arr dd{border-bottom:1px solid var(--line);padding:9px 0;margin:0}.arr dt{color:var(--mute)}
.arr h2{font-size:.75rem;letter-spacing:.06em;text-transform:uppercase;color:var(--mute);margin:28px 0 8px}
.grid{background:#fff;border:1px solid var(--line);border-radius:8px;padding:14px 16px;font-family:ui-monospace,Menlo,monospace;font-size:.78rem;line-height:1.35;white-space:pre;overflow:auto;max-height:640px}
.dlb{display:block;text-align:center;background:var(--fg);color:#fff;border-radius:6px;padding:10px;text-decoration:none;font-weight:600;margin-bottom:8px}
.dls{display:flex;gap:8px}.dls a{flex:1;text-align:center;border:1px solid var(--line);border-radius:6px;padding:7px;font-size:.85rem;text-decoration:none}
.sha{font-family:ui-monospace,Menlo,monospace;font-size:.72rem;word-break:break-all;color:var(--mute);margin-top:12px}
.prose{max-width:88rem;margin:0 auto;padding:10px var(--side) 20px}.prose h2{font-family:@SERIF@;font-weight:400;font-size:1.8rem;margin:42px 0 12px}
.two{display:grid;grid-template-columns:1fr 1fr;gap:40px}.two p{font-family:@SERIF@;font-size:1.05rem;line-height:1.6;color:#333;margin:0 0 12px}
.statc{display:grid;grid-template-columns:1fr 1fr;gap:10px}.statc div{background:#fff;border:1px solid var(--line);border-radius:8px;padding:16px}.statc b{display:block;font-size:2.2rem;line-height:1}.statc span{font-size:.85rem;color:var(--mute)}
.lv{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}.lv div{background:#fff;border:1px solid var(--line);border-radius:8px;padding:14px 16px}.lv b{display:block}.lv span{font-size:.82rem;color:var(--mute)}
.gl{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:0 36px;margin:0}.gl div{border-top:1px solid var(--line);padding:14px 0}.gl dt{font-weight:700;margin:0 0 4px}.gl dd{margin:0;font-family:@SERIF@;line-height:1.5;color:#333}
.board{display:grid;grid-template-columns:auto 1fr;gap:22px;align-items:start}
.bg{display:grid;grid-template-columns:repeat(3,52px);gap:4px}.bg .h{font-size:.72rem;color:var(--mute);text-align:center}
.bg button{height:52px;border-radius:6px;border:0;font:700 1.2rem system-ui;cursor:pointer}.bg .z{background:#f1f1ec;color:#1d1d1f}.bg .o{background:#1f6b45;color:#fff}
.pairs{font-size:.88rem}.pairs div{display:flex;justify-content:space-between;gap:14px;border-bottom:1px solid var(--line);padding:7px 0}.ok{color:var(--ver);font-weight:700}.miss{color:#a8321e;font-weight:700}
.doc{max-width:88rem;margin:0 auto;padding:30px var(--side);display:grid;grid-template-columns:220px 1fr;gap:48px}
.doc nav.side{position:sticky;top:20px;align-self:start;font-size:.88rem}.doc nav.side a{display:block;padding:5px 0;color:var(--mute);text-decoration:none}
.doc h1{font-size:2rem;margin:0 0 8px}.doc .lede{color:#333;max-width:46rem;margin:0 0 18px}.doc h2{font-size:1.15rem;margin:30px 0 8px;padding-top:6px;border-top:1px solid var(--line)}
.doc p,.doc li{max-width:46rem}.doc pre{background:#1d1d1f;color:#e8e8e3;border-radius:8px;padding:14px 16px;font-size:.82rem;line-height:1.5;overflow:auto}
.doc table{border-collapse:collapse;width:100%;font-size:.86rem}.doc th{text-align:left;color:var(--mute);border-bottom:1px solid var(--fg);padding:7px 8px}.doc td{border-bottom:1px solid var(--line);padding:7px 8px;vertical-align:top}
.cl{border-collapse:collapse;width:100%;font-size:.88rem}.cl th{font-size:.72rem;text-transform:uppercase;letter-spacing:.05em;color:var(--mute);text-align:left;border-bottom:1px solid var(--fg);padding:8px 10px}.cl td{border-bottom:1px solid var(--line);padding:10px;vertical-align:top}
.cl td.d{white-space:nowrap;font-variant-numeric:tabular-nums}.cl s{color:var(--mute)}
.rule{display:grid;grid-template-columns:1fr 120px 340px;gap:24px;padding:16px 0;border-top:1px solid var(--line);align-items:baseline}
.rule b{font-size:1rem}.rule h2{font-size:1rem;margin:0;font-weight:700}table.lg tr.hit td{box-shadow:inset 0 2px 0 #1f6b45,inset 0 -2px 0 #1f6b45}.rule p{margin:4px 0 0;color:#444;max-width:44rem}.rule .cnt{font-size:.88rem;color:var(--mute)}.rule .cnt b{color:var(--fg);font-size:1.3rem}.rule .refs{font-size:.85rem;text-align:right}
.sech{font-size:.75rem;letter-spacing:.06em;text-transform:uppercase;color:var(--mute);margin:34px 0 12px}
.two2{display:grid;grid-template-columns:1fr 1fr;gap:24px}
.card{background:#fff;border:1px solid var(--line);border-radius:12px;padding:30px var(--side);display:flex;flex-direction:column}
.card .lab{font-size:.72rem;letter-spacing:.06em;text-transform:uppercase;color:var(--mute)}
.card h2{font-size:1.7rem;margin:6px 0 6px;letter-spacing:-.01em}.card .lead{color:#444;margin:0 0 22px;min-height:3em}
.step{display:grid;grid-template-columns:44px 1fr;gap:14px;padding:14px 0;border-top:1px solid var(--line)}
.step .no{width:34px;height:34px;border-radius:50%;background:#1f6b45;color:#fff;font-weight:700;display:flex;align-items:center;justify-content:center}
.step b{display:block}.step span{color:#555;font-size:.92rem}
.cta{margin-top:auto;padding-top:22px;display:flex;gap:10px;align-items:center}
.cta a{background:var(--fg);color:#fff;border-radius:8px;padding:12px 18px;font-weight:600;text-decoration:none}.cta .s{color:var(--mute);font-size:.85rem}
.strip{margin-top:24px;background:#e4efe7;border-radius:12px;padding:22px var(--side);display:flex;justify-content:space-between;align-items:center}
.strip b{font-size:1.1rem}.strip a{font-weight:600}
.flow{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:0 0 30px}
.fl4{border-radius:10px;padding:20px 20px 18px;min-height:150px;display:flex;flex-direction:column;text-decoration:none}
.fl4 .no{font-size:2.4rem;font-weight:800;line-height:1}.fl4 b{font-size:1.1rem;margin-top:auto}.fl4 span{font-size:.85rem;opacity:.88;margin-top:4px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:24px}
.ft{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.ftl{background:#fff;border:1px solid var(--line);border-radius:8px;padding:14px 16px;text-decoration:none;display:block}.ftl .fmt{font-size:.68rem;font-weight:700;color:#1f6b45;letter-spacing:.05em}
.ftl b{display:block;font-family:ui-monospace,Menlo,monospace;font-size:.85rem;margin:4px 0}.ftl span{font-size:.8rem;color:var(--mute)}
.code{background:#1d1d1f;color:#e8e8e3;border-radius:10px;padding:18px 20px;font-family:ui-monospace,Menlo,monospace;font-size:.82rem;line-height:1.7;margin:0 0 10px;white-space:pre;overflow:auto}
.code .c{color:#8fd0a8}
.rules{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px}
.rules div{border-top:3px solid #1f6b45;background:#fff;border-radius:0 0 8px 8px;padding:14px 14px 16px;font-size:.88rem}.rules b{display:block;margin-bottom:4px}
a,button,.el,.pg,.ftl,.fl4,.card,.rules div,.lv div,.statc div,.btns a,.cta a,.go,.dlb,.dls a,.top nav a,table.lg tr,.cl tr,.pr,.rule{transition:transform .15s ease,box-shadow .15s ease,background-color .15s ease,color .15s ease,border-color .15s ease,filter .15s ease}
a:hover{color:#1f6b45}
.top nav a:hover{color:var(--fg)}.bsc{position:relative}.top nav a{position:relative}.top nav a:not(.po){display:inline-block}.top nav a:hover,.top nav a:focus-visible,.top .ai:hover,.top .ai:focus-visible{color:#1f6b45;transform:translateY(-2px)}.top .ai{position:relative;transition:transform .15s ease,color .15s ease}.top .in b a span,.top .in nav a,.top .in .ai,.top .in .sbm{text-transform:uppercase;letter-spacing:.06em}.top .in nav a,.top .in .ai,.top .in .sbm{font-size:14px}.top .in b a span{font-size:17px}@media (max-width:400px){.top .in b a span{font-size:15px;letter-spacing:.04em}}.top .in .srch{position:relative;flex:none;order:initial;margin-left:6px;width:38px;height:38px;box-sizing:border-box;border:1px solid var(--line);border-radius:6px;background:#fbfbf9;transition:width .22s ease,border-color .15s ease,background-color .15s ease}.top .in .srch:hover{border-color:#5fa77d}.top .in .srch.open{width:300px;border-color:#5fa77d;background:#fff}.top .in .srch.open:focus-within{box-shadow:0 0 0 2px #cfe5d7}.top .in .qb{position:absolute;left:0;top:0;width:36px;height:36px;border:0;background:none;padding:0;margin:0;display:flex;align-items:center;justify-content:center;color:var(--fg);cursor:pointer;z-index:2;border-radius:5px}.top .in .srch:hover .qb,.top .in .srch.open .qb{color:#1f6b45}.top .in .qb:focus-visible{outline:2px solid #1d1d1f;outline-offset:2px}.top .in .srch input{position:absolute;left:0;top:0;width:100%;height:100%;border:0;background:transparent;padding:0 12px 0 38px;opacity:0;visibility:hidden;transition:opacity .15s ease}.top .in .srch.open input{opacity:1;visibility:visible}.top .in .srch input{cursor:pointer}.top .in .srch.pin input{cursor:text}.top .in .srch .qr{top:44px}@media (max-width:560px){.top .in{position:relative}.top .in b{flex:0 0 calc(100% - 66px);min-width:0;min-height:38px;display:flex;align-items:center}.top .in .srch{order:2;margin-left:auto}.top .in .sbm{order:5}.top .in nav{order:6;width:auto;flex:1 1 0;min-width:0}.top .in .srch.open{position:absolute;left:var(--side);right:var(--side);top:10px;width:auto;z-index:6}.top .in .srch .qr{left:-1px;right:-1px}}@media (max-width:360px){.top .in .logo{width:50px;height:18px}.top .in b a span{font-size:13px;letter-spacing:.03em}.top .in .brand{gap:9px}}
.ftl:hover,.pg:hover{color:inherit}.el:hover,.fl4:hover{color:var(--fg)}
.f4,.f4:hover{color:#fff}.f3,.f3:hover{color:#1d1d1f}
.el[data-tv]:hover,.el[href]:hover{transform:translateY(-3px);box-shadow:0 8px 18px rgba(0,0,0,.14);filter:brightness(1.05)}
.pg:hover{transform:translateY(-4px) rotate(-.4deg);box-shadow:0 2px 4px rgba(0,0,0,.1),0 16px 30px rgba(0,0,0,.14)}
.ftl:hover,.lv div:hover,.statc div:hover{border-color:#5fa77d;transform:translateY(-2px);box-shadow:0 6px 14px rgba(0,0,0,.08)}
.fl4:hover{transform:translateY(-3px);box-shadow:0 10px 22px rgba(0,0,0,.14);filter:brightness(1.05)}
.card:hover{border-color:#5fa77d;box-shadow:0 10px 28px rgba(0,0,0,.08)}
.rules div:hover{background:#eef6f0}
.btns a:hover,.dls a:hover{background:var(--fg);color:#fff !important}.btns a.d:hover,.cta a:hover,.go:hover,.dlb:hover,.lf button:hover{background:#1f6b45;color:#fff !important}
.top .doi:hover,.top .gh:hover{color:var(--fg);border-color:var(--fg)}
table.lg tbody tr:hover td,.cl tbody tr:hover td{background:#f3f8f4}
.pr:hover,.rule:hover{background:#f3f8f4}
.bg button:hover{filter:brightness(1.12);transform:scale(1.05)}
.tumble i{transition:transform .3s ease}.tumble:hover i{transform:none}
.brand{display:flex;align-items:center;gap:10px}.logo{display:block}.logo{overflow:visible}.logo rect{transform-box:fill-box;transform-origin:center;animation-duration:50s;animation-delay:8s;animation-iteration-count:infinite}@keyframes lg0{0%,0.000%{transform:translateY(0.00px) rotate(0.0deg);animation-timing-function:cubic-bezier(.5,0,.2,1)}1.360%,6.200%{transform:translateY(4.00px) rotate(0.0deg);animation-timing-function:cubic-bezier(.2,.9,.3,1)}6.680%{transform:translateY(-1.80px) rotate(9.0deg);animation-timing-function:cubic-bezier(.35,0,.35,1)}7.120%{transform:translateY(0.63px) rotate(-3.1deg);animation-timing-function:cubic-bezier(.35,0,.35,1)}7.480%{transform:translateY(-0.22px) rotate(1.1deg);animation-timing-function:cubic-bezier(.35,0,.35,1)}7.800%,100%{transform:translateY(0.00px) rotate(0.0deg)}}@keyframes lg1{0%,0.220%{transform:translateY(0.00px) rotate(14.0deg);animation-timing-function:cubic-bezier(.5,0,.2,1)}1.580%,6.040%{transform:translateY(1.00px) rotate(0.0deg);animation-timing-function:cubic-bezier(.2,.9,.3,1)}6.520%{transform:translateY(-0.45px) rotate(23.8deg);animation-timing-function:cubic-bezier(.35,0,.35,1)}6.960%{transform:translateY(0.16px) rotate(10.6deg);animation-timing-function:cubic-bezier(.35,0,.35,1)}7.320%{transform:translateY(-0.05px) rotate(15.2deg);animation-timing-function:cubic-bezier(.35,0,.35,1)}7.640%,100%{transform:translateY(0.00px) rotate(14.0deg)}}@keyframes lg2{0%,0.440%{transform:translateY(0.00px) rotate(-22.0deg);animation-timing-function:cubic-bezier(.5,0,.2,1)}1.800%,5.880%{transform:translateY(-4.00px) rotate(0.0deg);animation-timing-function:cubic-bezier(.2,.9,.3,1)}6.360%{transform:translateY(1.80px) rotate(-37.4deg);animation-timing-function:cubic-bezier(.35,0,.35,1)}6.800%{transform:translateY(-0.63px) rotate(-16.6deg);animation-timing-function:cubic-bezier(.35,0,.35,1)}7.160%{transform:translateY(0.22px) rotate(-23.8deg);animation-timing-function:cubic-bezier(.35,0,.35,1)}7.480%,100%{transform:translateY(0.00px) rotate(-22.0deg)}}@keyframes lg3{0%,0.660%{transform:translateY(0.00px) rotate(14.0deg);animation-timing-function:cubic-bezier(.5,0,.2,1)}2.020%,5.720%{transform:translateY(1.00px) rotate(0.0deg);animation-timing-function:cubic-bezier(.2,.9,.3,1)}6.200%{transform:translateY(-0.45px) rotate(23.8deg);animation-timing-function:cubic-bezier(.35,0,.35,1)}6.640%{transform:translateY(0.16px) rotate(10.6deg);animation-timing-function:cubic-bezier(.35,0,.35,1)}7.000%{transform:translateY(-0.05px) rotate(15.2deg);animation-timing-function:cubic-bezier(.35,0,.35,1)}7.320%,100%{transform:translateY(0.00px) rotate(14.0deg)}}@keyframes lg4{0%,0.880%{transform:translateY(0.00px) rotate(0.0deg);animation-timing-function:cubic-bezier(.5,0,.2,1)}2.240%,5.560%{transform:translateY(4.00px) rotate(0.0deg);animation-timing-function:cubic-bezier(.2,.9,.3,1)}6.040%{transform:translateY(-1.80px) rotate(9.0deg);animation-timing-function:cubic-bezier(.35,0,.35,1)}6.480%{transform:translateY(0.63px) rotate(-3.1deg);animation-timing-function:cubic-bezier(.35,0,.35,1)}6.840%{transform:translateY(-0.22px) rotate(1.1deg);animation-timing-function:cubic-bezier(.35,0,.35,1)}7.160%,100%{transform:translateY(0.00px) rotate(0.0deg)}}@keyframes lg5{0%,1.100%{transform:translateY(0.00px) rotate(-22.0deg);animation-timing-function:cubic-bezier(.5,0,.2,1)}2.460%,5.400%{transform:translateY(-4.00px) rotate(0.0deg);animation-timing-function:cubic-bezier(.2,.9,.3,1)}5.880%{transform:translateY(1.80px) rotate(-37.4deg);animation-timing-function:cubic-bezier(.35,0,.35,1)}6.320%{transform:translateY(-0.63px) rotate(-16.6deg);animation-timing-function:cubic-bezier(.35,0,.35,1)}6.680%{transform:translateY(0.22px) rotate(-23.8deg);animation-timing-function:cubic-bezier(.35,0,.35,1)}7.000%,100%{transform:translateY(0.00px) rotate(-22.0deg)}}.brand:hover{color:var(--fg)}.citebox{margin-top:30px;display:grid;grid-template-columns:1fr 1fr;gap:32px;background:#e4efe7;border-radius:12px;padding:24px 28px}.citebox h2{font-size:1.3rem;margin:0 0 8px}.citebox p{margin:0;color:#333}.citebox .code{margin:0 0 8px}.doil{font-weight:600}
.srch{position:relative;flex:none;margin-left:6px}.top .ai{color:var(--mute);text-decoration:none;white-space:nowrap}.top .ai.on{color:var(--fg)}.top .ai:hover,.top .ai:focus-visible{color:#1f6b45}.top .ai.on{font-weight:600}.top .sbm{background:var(--fg);color:#fff;border-radius:6px;padding:7px 16px;font-weight:600;text-decoration:none;white-space:nowrap}.top .sbm:hover,.top .sbm.on{background:#1f6b45;color:#fff}.top b,.top nav a,.top .doi,.top .gh{white-space:nowrap}.top .in{gap:22px}.srch input{width:280px;border:1px solid var(--line);border-radius:6px;padding:6px 10px;font:.85rem system-ui;background:#fbfbf9}
.srch input:focus{outline:none;border-color:#5fa77d;background:#fff}.srch input{transition:width .2s ease,border-color .15s ease}
.qr{display:none;position:absolute;right:0;top:40px;width:480px;max-height:70vh;overflow:auto;background:#fff;border:1px solid var(--line);border-radius:10px;box-shadow:0 18px 48px rgba(0,0,0,.16);z-index:20;padding:6px 0}
.qr.on{display:block}.qr .g{font-size:.68rem;letter-spacing:.06em;text-transform:uppercase;color:var(--mute);padding:10px 16px 4px}
.qr a{display:block;padding:7px 16px;text-decoration:none;color:var(--fg)}.qr a b{display:block;font-size:.92rem}.qr a span{font-size:.78rem;color:var(--mute)}
.qr a.act,.qr a:hover{background:#eef6f0;color:var(--fg)}.qr .none{padding:12px 16px;color:var(--mute);font-size:.88rem}
.chk{margin-top:36px;display:grid;grid-template-columns:1fr 1fr;gap:32px;background:#fff;border:1px solid var(--line);border-radius:12px;padding:24px 28px}.chk h2{font-size:1.3rem;margin:0 0 8px}.chk p{margin:0 0 8px;color:#444}.chk .code{margin:0 0 10px}
.skip{position:absolute;left:8px;top:-60px;background:var(--fg);color:#fff;padding:8px 14px;border-radius:6px;z-index:50;text-decoration:none}.skip:focus{top:8px;color:#fff}
#main:focus{outline:none}
:focus-visible{outline:3px solid #1f6b45;outline-offset:2px;border-radius:4px}
.f4:focus-visible,.f3:focus-visible,.sbm:focus-visible,.cta a:focus-visible,.go:focus-visible,.dlb:focus-visible{outline-color:#1d1d1f}
.panel{visibility:hidden}.panel.open{visibility:visible}.panel .big:focus{outline:none}
.chips{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:0 0 16px}.chips .l{color:var(--mute);margin-right:6px;font-size:.9rem}
.chips button{font:inherit;font-size:.9rem;padding:7px 15px;border-radius:999px;border:1px solid var(--line);background:#fff;color:var(--fg);cursor:pointer}.chips button[aria-pressed=true]{background:var(--fg);color:#fff;border-color:var(--fg)}
.pf{display:flex;flex-wrap:wrap;gap:12px;align-items:center;margin:0 0 10px}.pf input{font:inherit;font-size:.95rem;padding:8px 12px;border:1px solid #8a8a84;border-radius:8px;width:18rem;max-width:100%}
.pn{font-size:.88rem;color:var(--mute);margin:0 0 20px}
.az{display:flex;flex-wrap:wrap;gap:6px;margin:0 0 8px}.az button,.az span{min-width:30px;height:30px;padding:0 6px;display:inline-flex;align-items:center;justify-content:center;border-radius:6px;font:inherit;font-size:.88rem}
.az button{border:1px solid var(--line);background:#fff;color:var(--fg);cursor:pointer}.az button:hover,.az button:focus-visible{border-color:#1f6b45;color:#1f6b45}.az button[aria-pressed=true]{background:#1f6b45;border-color:#1f6b45;color:#fff}.az span{color:#767670}
.pp{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:14px}.pp .pc[hidden]{display:none}
.pc{display:flex;gap:14px;align-items:center;background:#fff;border:1px solid var(--line);border-radius:12px;padding:16px 18px;text-decoration:none;color:var(--fg);scroll-margin-top:16px}
.pc:hover,.pc:focus-visible{border-color:#1f6b45;transform:translateY(-2px);box-shadow:0 6px 18px rgba(0,0,0,.06)}
.top nav a,.top .ai,.el,.pg,.ftl,.lv div,.statc div,.fl4,.pc{position:relative}.top nav a:after,.top .ai:after,.el:after,.pg:after,.ftl:after,.lv div:after,.statc div:after,.fl4:after,.pc:after{content:"";position:absolute;left:0;right:0;top:100%;height:5px}
.pc i,.ph i{flex:none;border-radius:50%;background:#b9dcc6;display:flex;align-items:center;justify-content:center;font-style:normal;font-weight:700}
.pc i{width:46px;height:46px;font-size:.95rem}.pc b{display:block;font-size:1.02rem}.pc span span{display:block;color:var(--mute);font-size:.86rem;margin-top:3px;line-height:1.35}
.ph{display:flex;gap:22px;align-items:center}.ph i{width:76px;height:76px;font-size:1.5rem}
.two3{display:grid;grid-template-columns:1fr 1fr;gap:20px 48px}.two3 h2{font-size:1.1rem;margin:0 0 10px}.two3 ul{list-style:none;margin:0 0 26px;padding:0}
.two3 li{display:flex;gap:12px;align-items:baseline;border-bottom:1px solid var(--line);padding:8px 0}.two3 ul.cnt{display:grid;grid-template-columns:1fr 1fr;column-gap:28px}.cnt li{justify-content:space-between}.cnt .num{color:var(--mute);font-size:.88rem}
.ent .d{color:var(--mute);font-size:.82rem;font-variant-numeric:tabular-nums;flex:none}.ent .tag{margin-left:auto}
.pap li{flex-direction:column;gap:2px}.pap span{color:var(--mute);font-size:.85rem}
.ab{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:22px 40px}.ab section{background:#fff;border:1px solid var(--line);border-radius:12px;padding:22px 24px}.ab h2{font-size:1.15rem;margin:0 0 8px}.ab p{margin:0;line-height:1.55}
@media (max-width:1100px){.pp{grid-template-columns:repeat(2,minmax(0,1fr))}}
@media (max-width:760px){.two3,.ab{grid-template-columns:1fr}}
@media (max-width:560px){.pp{grid-template-columns:1fr}.ph{gap:14px}.ph i{width:56px;height:56px;font-size:1.1rem}}
.lfind{position:relative;flex:none;width:340px;align-self:end;display:flex;flex-direction:column;margin-bottom:2px}.lfind svg{position:absolute;left:13px;bottom:14px;color:var(--mute)}
.lfind input{width:100%;border:1px solid var(--line);border-radius:8px;padding:11px 14px 11px 38px;font:1rem system-ui,-apple-system,"Segoe UI",sans-serif;background:#fff;color:var(--fg)}
.lfind input:focus{outline:2px solid #1f6b45;outline-offset:1px;border-color:#1f6b45}.lfind span{order:-1;display:block;font-size:.8rem;margin:0 0 6px;text-align:right}
#lib>div[hidden]{display:none}.lnone{margin:10px 0 0;color:var(--mute)}
@media (max-width:900px){.lfind{width:100%}}
.mopts{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:14px;margin:6px 0 10px}.mopt{display:flex;flex-direction:column;gap:8px;background:#fff;border:1px solid var(--line);border-radius:12px;padding:20px 20px 18px;text-decoration:none;color:var(--fg);min-height:190px;position:relative}.mopt:after{content:"";position:absolute;left:0;right:0;top:100%;height:5px}
.mopt:hover,.mopt:focus-visible{border-color:#1f6b45;box-shadow:0 6px 18px rgba(0,0,0,.08);transform:translateY(-2px)}.mopt b{font-size:1.08rem;line-height:1.3}.mopt p{margin:0;color:var(--mute);font-size:.88rem;line-height:1.45}.mopt .ft{margin-top:auto;display:flex;justify-content:space-between;align-items:baseline;border-top:1px solid var(--line);padding-top:12px;font-size:.84rem}.mopt .go{color:#1f6b45;font-weight:600;background:none;padding:0}.mopt .ct{color:var(--fg);font-weight:600}
@media (max-width:1100px){.mopts{grid-template-columns:repeat(3,minmax(0,1fr))}}@media (max-width:700px){.mopts{grid-template-columns:repeat(2,minmax(0,1fr))}.mopt{min-height:0}}@media (max-width:440px){.mopts{grid-template-columns:1fr}}
.gmw{overflow-x:auto}table.gm{width:100%;border-collapse:collapse;font-size:.92rem}table.gm th{text-align:left;font-size:.72rem;letter-spacing:.06em;text-transform:uppercase;color:var(--mute);font-weight:600;border-bottom:1px solid var(--fg);padding:10px}table.gm th.n,table.gm td.n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}
table.gm td{border-bottom:1px solid var(--line);padding:14px 10px;vertical-align:top}table.gm td a{font-weight:600;font-size:1rem;display:inline-block;padding:2px 0}table.gm td span{display:block;color:var(--mute);font-size:.84rem;margin-top:3px;line-height:1.4}table.gm tr:hover td{background:#fff}@media (max-width:560px){table.gm thead{display:none}table.gm tr{display:flex;flex-wrap:wrap;gap:4px 16px;border-bottom:1px solid var(--line);padding:12px 0}table.gm td{display:block;border:0;padding:0}table.gm td:first-child{width:100%}table.gm td.n{text-align:left;font-size:.84rem}table.gm td.n:before{content:attr(data-l) " ";color:var(--mute)}}
table.mt{width:100%;border-collapse:collapse;margin:0 0 26px}table.mt th{text-align:left;font-size:.74rem;letter-spacing:.06em;text-transform:uppercase;color:var(--mute);font-weight:600;border-bottom:1px solid var(--fg);padding:6px 8px}
table.mt td{border-bottom:1px solid var(--line);padding:7px 8px}table.mt .n{text-align:right;font-variant-numeric:tabular-nums;white-space:nowrap}table.mt td a{display:inline-block;padding:3px 0}
@media (min-width:561px){.top .in .srch{z-index:6;transition:width .22s ease,margin-left .22s ease,border-color .15s ease,background-color .15s ease}.top .in .srch.open{margin-left:-256px}.top .in .srch.open:before{content:"";position:absolute;right:100%;top:-2px;bottom:-2px;width:56px;background:linear-gradient(to right,rgba(255,255,255,0),#fff 70%);pointer-events:none}}
@media (min-width:561px) and (max-width:1310px){.top .in .srch.open{margin-left:auto}.top .in .srch.open:before{display:none}}
.ctw{overflow-x:auto;margin:18px 0}table.ctg{border-collapse:separate;border-spacing:6px}table.ctg th{font-size:.8rem;color:var(--mute);font-weight:600;padding:2px 6px;text-align:center;white-space:nowrap}
table.ctg td{padding:0;min-width:92px}a.ct{display:flex;flex-direction:column;align-items:flex-start;gap:2px;background:#b9dcc6;border-radius:6px;padding:8px 10px;text-decoration:none;color:var(--fg);position:relative}
a.ct:hover,a.ct:focus-visible{background:#8fc5a4}a.ct b{font-size:1.25rem}a.ct span{font-size:.75rem}
.sztop{display:grid;grid-template-columns:1fr 560px;gap:24px 48px;align-items:end;margin:0 0 8px}.szf{margin:0}.szh h1{font-size:2.4rem;margin:4px 0 8px}.szh p{max-width:46rem}.szg{display:grid;grid-template-columns:3fr 2fr;gap:20px 48px;margin-top:22px}
dl.szd{display:grid;grid-template-columns:11em 1fr;gap:0;margin:0}dl.szd dt{color:var(--mute);font-size:.8rem;letter-spacing:.06em;text-transform:uppercase;padding:10px 0;border-bottom:1px solid var(--line)}dl.szd dd{margin:0;padding:10px 0;border-bottom:1px solid var(--line);line-height:1.5}
.szg h2{font-size:1rem;margin:0 0 10px}.nb{display:grid;grid-template-columns:1fr 1fr;gap:10px}.nb a{display:flex;flex-direction:column;gap:2px;background:#fff;border:1px solid var(--line);border-radius:10px;padding:12px 14px;text-decoration:none;color:var(--fg)}
.nb a:hover,.nb a:focus-visible{border-color:#1f6b45}.nb span{font-size:.75rem;color:var(--mute);letter-spacing:.06em;text-transform:uppercase}.nb b{font-size:.98rem}.nb i{font-style:normal;color:#1f6b45;font-weight:700}
@media (max-width:1100px){.sztop{grid-template-columns:1fr}}
@media (max-width:760px){.szg{grid-template-columns:1fr}dl.szd{grid-template-columns:1fr}dl.szd dt{border:0;padding-bottom:0}}
@media (prefers-reduced-motion:reduce){*,*:before,*:after{transition:none !important;animation:none !important;scroll-behavior:auto !important}.el:hover,.pg:hover,.pc:hover,.mi:hover,.hub a:hover,.fl4:hover,.ftl:hover,.lv div:hover,.statc div:hover,.bg button:hover{transform:none !important}.tumble i{transform:none !important}}
.top .in{height:64px;gap:26px}.top b,.top b a,.top nav a,.top .ai,.top .sbm,.srch input{font-size:16px;line-height:1}
.top b a{font-size:18px;font-weight:700}.top nav{gap:22px}.brand{gap:12px}.logo{width:66px;height:24px}
.top .sbm{height:38px;box-sizing:border-box;display:inline-flex;align-items:center;padding:0 18px;border:1px solid var(--fg);border-radius:6px}
.srch input{height:38px;box-sizing:border-box;padding:0 12px;border:1px solid var(--line);border-radius:6px;font-family:system-ui,-apple-system,"Segoe UI",sans-serif}
.hstats{max-width:88rem;margin:0 auto;padding:26px var(--side) 4px;display:grid;grid-template-columns:36px repeat(12,minmax(0,1fr));gap:6px}
.hstats div{grid-column:span 2;border-left:1px solid var(--line);padding:2px 9px 0}
.hstats b{display:block;font-size:1.6rem;line-height:1.15}.hstats span{display:block;font-size:.75rem;color:var(--mute);text-transform:uppercase;letter-spacing:.05em;margin-top:6px;white-space:nowrap}
#lookup .in{grid-template-columns:36px repeat(12,minmax(0,1fr));gap:0 6px}
#lookup .in>div{grid-column:2/span 8;padding-left:9px}#lookup .in>form{grid-column:10/span 4}
.hstats{grid-template-columns:repeat(12,minmax(0,1fr))}.hstats>span:first-child{display:none}
#lookup .in{grid-template-columns:repeat(12,minmax(0,1fr))}#lookup .in>div{grid-column:1/span 8;padding-left:0}#lookup .in>form{grid-column:9/span 4}
@media (min-width:901px){.wrapw .blk{margin-left:-42px}.wrapw .bl{margin-left:0}}
@media (max-width:900px){:root{--side:16px}}
.ans.hit{animation:hit 1.1s ease}@keyframes hit{0%{background:#9fcdb1;box-shadow:0 0 0 3px #5fa77d}100%{background:var(--soft);box-shadow:0 0 0 0 transparent}}
.vh{position:absolute;width:1px;height:1px;overflow:hidden;clip:rect(0 0 0 0);white-space:nowrap}
.nf{max-width:60rem;margin:0 auto;padding:60px var(--side);text-align:center}.nf h1{font-size:3rem;margin:0 0 10px}
.tumble{display:flex;justify-content:center;gap:4px;margin:0 0 30px}.tumble i{display:block;width:34px;height:34px;border-radius:5px;background:#b9dcc6}
.tumble i:nth-child(2n){background:#5fa77d;transform:translateY(14px) rotate(14deg)}.tumble i:nth-child(3n){background:#1f6b45;transform:translateY(34px) rotate(-22deg)}

.strip,.citebox,.chk,.doc section,.card,.pg h2,.pg .au,.paper .hd h1{overflow-wrap:anywhere}.po{display:none}
.lib>div,.grid2>div,.two2>div,.arr>section,.arr>aside,.doc>section,.hero .in>div{min-width:0}
@media (max-width:1280px){.el{min-height:96px;padding:6px 7px}.el .n{font-size:clamp(1.05rem,1.6vw,1.7rem)}.el .n small{font-size:.62rem;margin-left:2px}.el .tp{font-size:.6rem}.el .st{font-size:.62rem}.el .dt{font-size:.58rem}.el .ft{flex-direction:column;align-items:flex-start;gap:1px}}
@media (max-width:1520px){.top nav{gap:17px}.top .in{gap:22px}}
@media (max-width:1310px){.top .in{flex-wrap:wrap;height:auto;padding-top:10px;padding-bottom:10px;row-gap:10px}.top nav{order:6;width:100%;overflow-x:auto;gap:18px;padding-top:4px;margin-top:-4px;padding-bottom:2px}.top .sp{display:none}.top .in .srch{margin-left:auto}}
@media (max-width:900px){
body{overflow-x:hidden}
.hero .in,.arr,.two,.doc,.two2,.grid2,.chk,.citebox{grid-template-columns:1fr !important}
.hero .in{gap:24px;padding-top:28px;padding-bottom:24px}.hero h1{font-size:1.9rem}
#lookup .in>div,#lookup .in>form{grid-column:1/-1}
.lf{grid-template-columns:repeat(3,minmax(0,1fr))}.lf button{grid-column:1/-1}
.hstats{grid-template-columns:repeat(2,minmax(0,1fr));row-gap:16px}.hstats div{grid-column:span 1}
.stats{flex-wrap:wrap;row-gap:14px}.stats div{flex:1 1 45%}
.bsc{overflow-x:auto;margin:0 calc(-1*var(--side));padding:0 var(--side)}
.wrapw .blk{min-width:1100px;margin-left:0}.blk .r,.blk>span:first-child{position:sticky;left:0;background:var(--bg);z-index:2;align-self:stretch;display:flex;align-items:center;justify-content:center;box-shadow:calc(-1*var(--side)) 0 0 var(--bg),6px 0 0 var(--bg),7px 0 0 var(--line)}
.pageh .in{flex-wrap:wrap}.pageh h1{font-size:1.9rem}
.lib{grid-template-columns:repeat(2,minmax(0,1fr));gap:20px 14px}
.flow{grid-template-columns:repeat(2,minmax(0,1fr))}.ft{grid-template-columns:1fr}
.rules{grid-template-columns:1fr}.lv{grid-template-columns:repeat(2,minmax(0,1fr))}.gl{grid-template-columns:1fr}
.rule{grid-template-columns:1fr;gap:6px}.rule .refs{text-align:left}
.pr{grid-template-columns:1fr;gap:2px}.pr .c{text-align:left}
table.lg,.cl,.doc table{display:block;overflow-x:auto;white-space:normal}
.doc nav.side{position:static;display:flex;flex-wrap:wrap;gap:4px 14px}
.code{white-space:pre-wrap;word-break:break-all}
.srch{flex:1 1 100%;order:4;margin-left:0}.srch input{width:100%}.qr{width:auto;left:0;right:0}
.panel{right:12px;left:12px;width:auto;top:auto;bottom:12px}
.foot .in{flex-direction:column;gap:8px}
.board{grid-template-columns:1fr}
.paper .hd h1{font-size:1.8rem}
}
@media (max-width:560px){.lib{grid-template-columns:1fr}.flow{grid-template-columns:1fr}.lv{grid-template-columns:1fr}.top .ai{display:none}.po{display:inline}.top b{flex:1 1 100%}.srch{order:4;flex:1 1 0;min-width:0}.top .sbm{order:5}.strip{flex-direction:column;align-items:flex-start;gap:10px}.citebox,.chk,.card{padding:20px}}
@media (min-width:1311px){.top .in nav{gap:0;align-self:stretch;align-items:stretch}.top .in nav a{display:flex;align-items:center;padding:0 11px}.top .in nav a:first-child{padding-left:0}}
.mb,.qbt,.top .in nav a.ns{display:none}
@media (max-width:1310px){:root{--bh:40px;--bw:var(--bh);--sw:86px;--nf:26px;--lh:calc(var(--nf)*.955);--ic:calc(var(--nf)*.9);--ly:calc(var(--nf)*-.06)}
.top .in{display:grid;grid-template-columns:minmax(0,1fr) auto minmax(0,1fr);align-items:center;column-gap:16px;row-gap:12px;height:auto;padding-top:12px;padding-bottom:12px;position:relative}
.top .sp,.top .ai{display:none}
.top .in>b{grid-column:2;grid-row:1;justify-self:center;min-width:0;order:0;flex:none;height:var(--bh);display:flex;align-items:center}.top .in>b .brand{height:var(--bh);align-items:center;line-height:1}.top .in>b .brand span{line-height:1;white-space:nowrap}
.top .in .mb{grid-column:1;grid-row:1;justify-self:start;margin-left:calc((var(--ic)*16/14 - var(--bw))/2) !important}
.top .in .srch{display:contents}
.top .in .qb{grid-column:3;grid-row:1;justify-self:end;margin:0 calc(var(--sw) + 8px) 0 0;position:static;z-index:auto}
.top .in .sbm{grid-column:3;grid-row:1;justify-self:end;margin:0;order:0}
.top .in .mb,.top .in .qb{width:var(--bw);padding:0 !important}.top .in .sbm{width:var(--sw);height:32px;padding:0;font-size:14px;letter-spacing:.06em;border-radius:6px}.top .in .mbt,.top .in .qbt{display:none !important}.top .in .mb svg{height:var(--ic);width:calc(var(--ic)*18/14);position:relative;top:var(--ly)}.top .in .qb svg{height:calc(var(--ic)*1.06);width:calc(var(--ic)*1.06);position:relative;top:var(--ly)}.top .in .mb,.top .in .qb{border-color:transparent !important;background:transparent !important}.top .in .mb:hover,.top .in .qb:hover,.top .in .mb[aria-expanded=true],.top .in .qb[aria-expanded=true]{color:#1f6b45;background:#eef6f0 !important}.top .in .mb:focus-visible,.top .in .qb:focus-visible{outline:2px solid #1d1d1f;outline-offset:2px}
.top .in>b .brand,.top .in>b .brand span{font-size:var(--nf);letter-spacing:.06em}.top .in>b .brand{gap:calc(var(--nf)*.6)}.top .in>b .logo{height:var(--lh);width:calc(var(--lh)*61/22);position:relative;top:var(--ly)}
.top .in .mb,.top .in .qb,.top .in .sbm{height:var(--bh);box-sizing:border-box;padding:0 10px;display:inline-flex;align-items:center;justify-content:center;gap:8px;font:inherit;font-size:14px;font-weight:600;text-transform:uppercase;letter-spacing:.06em;line-height:1;border-radius:8px;cursor:pointer}
.top .in .mb,.top .in .qb{background:#fff;color:var(--fg);border:1px solid #c9c9c4}
.top .in .mb:hover,.top .in .qb:hover,.top .in .mb:focus-visible,.top .in .qb:focus-visible,.top .in .mb[aria-expanded=true],.top .in .qb[aria-expanded=true]{border-color:#1f6b45;color:#1f6b45;background:#f3f8f5}
.top .in .sbm{border:1px solid var(--fg)}.qbt{display:inline}
.top .in .srch input,.top .in .srch.open input{display:none;grid-column:1/-1;grid-row:2;position:static;width:100%;height:44px;margin:0;padding:0 14px;font-size:16px;border:1px solid #1f6b45;border-radius:8px;background:#fff;opacity:1;visibility:visible;transform:none;cursor:text}
.top .in .srch.pin input{display:block}
.top .in .srch .qr{left:var(--side);right:var(--side);width:auto;top:100%;margin-top:4px;max-height:65vh}
.top .in nav{display:none;position:absolute;left:var(--side);right:auto;top:100%;margin:6px 0 0;width:auto;min-width:320px;max-width:calc(100% - 2*var(--side));z-index:20;background:#fff;border:1px solid var(--line);border-radius:12px;box-shadow:0 12px 32px rgba(0,0,0,.14);padding:8px;grid-template-columns:1fr 1fr;gap:4px;overflow:visible;order:0}
.top .in nav.open{display:grid}
.top nav a,.top nav a:not(.po){display:block;padding:12px;border:0;border-radius:8px;font-size:14px;color:var(--fg);transform:none !important}
.top nav a.on{background:#eef6f0;color:#1f6b45}.top nav a:hover,.top nav a:focus-visible{background:#f4f4f1}.top .in nav a.ns{display:none}}
@media (max-width:1100px){:root{--bh:40px;--nf:24px}}
@media (max-width:800px){:root{--bh:40px;--nf:21px}.top .in .mb,.top .in .qb{padding:0}.mbt,.qbt{display:none}
.top .in .sbm{display:none}.top .in .qb{margin-right:calc((var(--ic)*.96 - var(--bw))/2)}.top .in{column-gap:12px}
.top .in nav{right:var(--side);min-width:0;max-width:none}
.top .in nav a.ns{display:block;grid-column:1/-1;margin-top:4px;background:var(--fg);color:#fff;text-align:center;font-weight:600}.top .in nav a.ns:hover,.top .in nav a.ns:focus-visible{background:#1f6b45;color:#fff}}
@media (max-width:520px){:root{--bh:38px;--nf:18px}}
@media (max-width:440px){:root{--bh:38px;--nf:16px}.top .in>b .brand,.top .in>b .brand span{letter-spacing:.04em}}
@media (max-width:400px){:root{--nf:15px}}
@media (max-width:374px){:root{--bh:36px;--nf:14px}.top .in>b .brand,.top .in>b .brand span{letter-spacing:.02em}}
@media (max-width:340px){:root{--bh:34px;--nf:12px}.top .in{column-gap:8px}}
""".replace("@SERIF@", SERIF)


class Site:
    def __init__(self, out, preview):
        self.out = out
        self.preview = preview
        self.urls = []

    def href(self, depth, path):
        frag = ""
        if "#" in path:
            path, frag = path.split("#", 1)
            frag = "#" + frag
        if path == "" or path.endswith("/"):
            path = path + ("index.html" if self.preview else "")
        return "../" * depth + path + frag

    def write(self, path, text, sitemap=True):
        full = os.path.join(self.out, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, "w", encoding="utf-8") as f:
            f.write(text)
        if sitemap and path.endswith(".html"):
            self.urls.append(path[:-len("index.html")] if path.endswith("index.html") else path)

    def page(self, path, title, desc, body, active="", jsonld=None, script=""):
        depth = path.count("/")
        absolute = path == "404.html" and not self.preview
        h = (lambda p: "/" + p) if absolute else (lambda p: self.href(depth, p))
        root = "/" if absolute else "../" * depth
        nav = "".join('<a href="%s"%s>%s</a>' % (h(p), ' class=on' if n == active else "", n) for n, p in NAV)
        nav += '<a class=ns href="%s">Submit</a>' % h("submit/")
        canon = ('<meta name="robots" content="noindex">' if path == "404.html" else
                 '<link rel="canonical" href="%s">' % (BASE + (path[:-len("index.html")] if path.endswith("index.html") else path)))
        ld = '<script type="application/ld+json">%s</script>' % jsonld if jsonld else ""
        doc = ('<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">'
               '<title>%s</title><meta name="description" content="%s">%s'
               '<link rel="stylesheet" href="%s"><link rel="alternate" type="text/plain" title="llms.txt" href="%s">%s</head><body><a class=skip href="#main">Skip to content</a>'
               '<header class=top><div class=in><b><a class=brand href="%s"><svg class=logo viewBox="0 0 61 22" aria-hidden="true"><rect x="1.0" y="3.0" width="8" height="8" rx="1.6" fill="#b9dcc6" style="transform:rotate(0deg);animation-name:lg0"/><rect x="11.0" y="6.0" width="8" height="8" rx="1.6" fill="#5fa77d" style="transform:rotate(14deg);animation-name:lg1"/><rect x="21.0" y="11.0" width="8" height="8" rx="1.6" fill="#1f6b45" style="transform:rotate(-22deg);animation-name:lg2"/><rect x="31.0" y="6.0" width="8" height="8" rx="1.6" fill="#5fa77d" style="transform:rotate(14deg);animation-name:lg3"/><rect x="41.0" y="3.0" width="8" height="8" rx="1.6" fill="#b9dcc6" style="transform:rotate(0deg);animation-name:lg4"/><rect x="51.0" y="11.0" width="8" height="8" rx="1.6" fill="#1f6b45" style="transform:rotate(-22deg);animation-name:lg5"/></svg><span>Covering Array Tools</span></a></b><button type=button class=mb aria-label="Menu" aria-expanded="false" aria-controls="nv"><svg width="18" height="14" viewBox="0 0 18 14" aria-hidden="true"><path d="M1 1h16M1 7h16M1 13h16" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg><span class=mbt>Menu</span></button><nav id=nv aria-label="Main">%s</nav><span class=sp></span>'
               '<div class=srch><button type=button class=qb aria-label="Search" aria-expanded="false" aria-controls="q"><svg width="17" height="17" viewBox="0 0 17 17" aria-hidden="true"><circle cx="7" cy="7" r="5.5" fill="none" stroke="currentColor" stroke-width="1.9"/><path d="M11.2 11.2l4.3 4.3" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/></svg><span class=qbt>Search</span></button><input id=q type=search placeholder="Search sizes, arrays, papers, people" autocomplete=off aria-label="Search" role=combobox aria-autocomplete=list aria-controls=qr aria-expanded=false><div id=qr class=qr role=listbox aria-label="Search results"></div><span id=qn class=vh aria-live=polite></span></div><a class="sbm%s" href="%s">Submit</a></div></header><div id=main tabindex=-1>%s</div>'
               '<div class=foot><div class=in><span><a href="%s">Source data on GitHub</a>, with the full history of the table. This build: commit <span class=mono>%s</span>, %s</span>'
               '<span>Cite: DOI <a href="https://doi.org/%s">%s</a></span><span>Data CC BY 4.0</span><span><a href="%s">About</a></span><span><a href="%s">For AI</a></span><span><a href="mailto:%s">%s</a></span></div></div>'
               '<script src="%s" data-root="%s" data-preview="%s" defer></script>%s%s</body></html>') % (
            E(title), E(desc), canon, h("assets/site.css"), h("llms.txt"), ld, h(""), nav, " on" if active == "Submit" else "", h("submit/"), body,
            REPO_URL, self.commit, self.date, DOI, DOI, h("about/"), h("for-ai/"), CONTACT, CONTACT, h("assets/search.js"), root, "1" if self.preview else "", script, "" if self.preview else COUNTER)
        self.write(path, doc)


SEARCH_JS = r"""(function(){var b=document.querySelector('.mb'),n=document.getElementById('nv');if(!b||!n)return;function sh(o){n.classList.toggle('open',o);b.setAttribute('aria-expanded',o?'true':'false')}b.addEventListener('click',function(){sh(!n.classList.contains('open'))});document.addEventListener('keydown',function(e){if(e.key=='Escape'&&n.classList.contains('open')){sh(false);b.focus()}});document.addEventListener('click',function(e){if(n.classList.contains('open')&&!n.contains(e.target)&&!b.contains(e.target))sh(false)})})();(function(){var me=document.currentScript,root=me.getAttribute('data-root')||'',pv=me.getAttribute('data-preview')=='1',q=document.getElementById('q'),box=document.getElementById('qr'),loaded=false,act=-1,items=[];
function load(cb){if(loaded){cb();return}var s=document.createElement('script');s.src=root+'assets/sindex.js';s.onload=function(){loaded=true;cb()};document.head.appendChild(s)}
function norm(x){return x.toLowerCase().replace(/[^a-z0-9]+/g,' ').trim()}
function url(p){if(pv&&(p===''||p.slice(-1)=='/'))p+='index.html';return root+p}
var G={x:'Size',c:'Cells',a:'Arrays',p:'Papers',u:'People',m:'Methods'};
function close(){box.classList.remove('on');q.setAttribute('aria-expanded','false');q.removeAttribute('aria-activedescendant')}
function sizes(raw,res){var m=raw.match(/^\s*can\s*\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)\s*$/i),c,e,i,t,k,vv,n;if(m){t=+m[1];k=+m[2];vv=+m[3]}else{m=raw.match(/^\s*ca\s*\(\s*(\d+)\s*;\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)\s*$/i);if(!m)return false;n=+m[1];t=+m[2];k=+m[3];vv=+m[4];for(i=0;i<SI.length;i++){e=SI[i];if(e[0]=='a'&&e[3].indexOf('ca/'+n+'/'+t+'/'+k+'/'+vv+'/')==0)res.x.push([0,e])}}c='t'+t+'/v'+vv+'/';for(i=0;i<SI.length;i++){e=SI[i];if(e[0]=='c'&&e[3]==c){res.x.push([1,['x','CAN('+t+', '+k+', '+vv+')','best known size, lower bound, credit and array','size/?t='+t+'&k='+k+'&v='+vv,'',0]]);break}}return res.x.length>0}
function run(){var v=norm(q.value);if(!v){close();return}var tk=v.split(' '),res={x:[],c:[],a:[],p:[],u:[],m:[]};if(!sizes(q.value,res)){
for(var i=0;i<SI.length;i++){var e=SI[i],k=e[4],ok=true;for(var j=0;j<tk.length;j++){var t=tk[j];if(/^\d+$/.test(t)){if((' '+k+' ').indexOf(' '+t+' ')<0){ok=false;break}}else if(k.indexOf(t)<0){ok=false;break}}
if(ok){var sc=(k.indexOf(v)>=0?0:1)*1000+e[1].length;res[e[0]].push([sc,e])}}}
var h='',n=0;items=[];['x','c','u','m','a','p'].forEach(function(g){var r=res[g].sort(function(x,y){return x[0]-y[0]});if(!r.length)return;h+='<div class=g role=presentation>'+G[g]+(r.length>6?' ('+r.length+')':'')+'</div>';
r.slice(0,6).forEach(function(x){var e=x[1],u=url(e[3])+(e[5]?'#k='+e[5]:'');h+='<a href="'+u+'" data-i='+n+' id=qo'+n+' role=option aria-selected=false><b>'+e[1]+'</b><span>'+e[2]+'</span></a>';items.push(u);n++})});
box.innerHTML=n?h:'<div class=none>Nothing found for '+q.value.replace(/</g,'&lt;')+'</div>';box.classList.add('on');q.setAttribute('aria-expanded','true');act=n?0:-1;mark();document.getElementById('qn').textContent=n?n+(n==1?' result':' results'):'Nothing found'}
function mark(){var a=box.querySelectorAll('a');for(var i=0;i<a.length;i++){a[i].classList.toggle('act',i==act);a[i].setAttribute('aria-selected',i==act?'true':'false')}if(act>=0&&a[act])q.setAttribute('aria-activedescendant',a[act].id);else q.removeAttribute('aria-activedescendant')}
var st=null,sent='';function track(){var t=q.value.trim().toLowerCase().replace(/\s+/g,' ').slice(0,80);if(t.length<2||t==sent||!window.goatcounter||!goatcounter.count)return;sent=t;goatcounter.count({path:'search: '+t,title:document.getElementById('qn').textContent,event:true})}
q.addEventListener('focus',function(){load(function(){})});q.addEventListener('input',function(){load(run);clearTimeout(st);st=setTimeout(track,1500)});q.addEventListener('blur',function(){clearTimeout(st);track()});
q.addEventListener('keydown',function(ev){if(ev.key=='ArrowDown'){act=Math.min(act+1,items.length-1);mark();ev.preventDefault()}else if(ev.key=='ArrowUp'){act=Math.max(act-1,0);mark();ev.preventDefault()}
else if(ev.key=='Enter'){clearTimeout(st);track();if(act>=0&&items[act])location.href=items[act];ev.preventDefault()}else if(ev.key=='Escape'){close();q.blur()}});
document.addEventListener('keydown',function(ev){if(ev.key=='/'&&document.activeElement!==q&&!/input|textarea/i.test(document.activeElement.tagName)){q.focus();ev.preventDefault()}});
document.addEventListener('click',function(ev){if(!ev.target.closest('.srch'))close()})})();
document.addEventListener('click',function(e){var a=e.target.closest&&e.target.closest('a[href]');if(!a||!window.goatcounter||!goatcounter.count)return;var h=a.href,m=h.match(/^https:\/\/(raw\.githubusercontent\.com|zenodo\.org\/records)\/.*?([^\/?#]+)(?:[?#].*)?$/)||h.match(/^[^?#]*?([^\/?#]+\.(?:csv|json|txt|gz|zip|rda|R))(?:[?#].*)?$/);if(!m)return;goatcounter.count({path:'download: '+(m[2]||(a.host==location.host?a.pathname.replace(/^\//,''):m[1])),title:location.pathname,event:true})});
(function(){var w=document.querySelector('.srch'),bt=w&&w.querySelector('.qb'),q=document.getElementById('q'),r=document.getElementById('qr');if(!bt||!q)return;var pin=false,hov=false;
function op(){w.classList.add('open');bt.setAttribute('aria-expanded','true')}
function cl(){pin=false;w.classList.remove('open','pin');bt.setAttribute('aria-expanded','false');if(r)r.classList.remove('on')}
function hold(){pin=true;w.classList.add('pin');op();setTimeout(function(){q.focus()},30)}
w.addEventListener('mouseenter',function(){hov=true;op()});
w.addEventListener('mouseleave',function(){hov=false;if(!pin)cl()});
bt.addEventListener('click',function(){if(pin&&matchMedia('(max-width:1310px)').matches){cl();return}hold()});
q.addEventListener('focus',function(){pin=true;w.classList.add('pin');op();if(q.value)q.dispatchEvent(new Event('input'))});
q.addEventListener('keydown',function(e){if(e.key=='Escape'){cl();bt.focus()}});
w.addEventListener('focusout',function(e){if(!e.relatedTarget||!w.contains(e.relatedTarget)){if(!hov)cl();else{pin=false;w.classList.remove('pin')}}});
document.addEventListener('keydown',function(e){if(e.key=='/'&&!pin&&!/input|textarea/i.test(document.activeElement.tagName)){e.preventDefault();hold()}});
document.addEventListener('mousedown',function(e){if(!w.contains(e.target)&&w.classList.contains('open')){cl();if(document.activeElement===q)q.blur()}})})();
(function(){var b=document.querySelector('.brand');if(!b||!b.animate)return;var rs=b.querySelectorAll('.logo rect'),R=[0,14,-22,14,0,-22],D=[4,1,-4,1,4,-4],busy=false;
function tf(y,r){return 'translateY('+y+'px) rotate('+r+'deg)'}
b.addEventListener('mouseenter',function(){if(busy||matchMedia('(prefers-reduced-motion: reduce)').matches)return;
for(var i=0;i<rs.length;i++){var a=rs[i].getAnimations().filter(function(x){return x.animationName});if(a.length){var t=(a[0].currentTime||0)-8000;if(t>=0&&t%50000<4700)return}}
busy=true;setTimeout(function(){busy=false},1240);
for(var i=0;i<rs.length;i++){var r=R[i],d=D[i],rr=r?r:(i%2?-9:9),ox=-d*0.45-(d?0:1),orr=(r?rr*1.7:rr)-r;
rs[i].animate([{transform:tf(0,r)},{transform:tf(ox,r+orr),offset:.3,easing:'cubic-bezier(.35,0,.35,1)'},{transform:tf(-ox*.35,r-orr*.35),offset:.58,easing:'cubic-bezier(.35,0,.35,1)'},{transform:tf(ox*.12,r+orr*.12),offset:.8,easing:'cubic-bezier(.35,0,.35,1)'},{transform:tf(0,r)}],{duration:820,delay:(rs.length-1-i)*80,easing:'linear',composite:'replace'})}
})})();
"""


def git_commit(repo):
    g = os.path.join(repo, ".git")
    try:
        head = open(os.path.join(g, "HEAD")).read().strip()
        if head.startswith("ref: "):
            ref = head[5:]
            p = os.path.join(g, ref)
            if os.path.exists(p):
                return open(p).read().strip()[:7]
            for line in open(os.path.join(g, "packed-refs")):
                if line.strip().endswith(ref):
                    return line.split()[0][:7]
        return head[:7]
    except OSError:
        return "unknown"


def split_ref(r):
    m = re.match(r"^((?:[^,]+, )*?[^,]+ and [^,]+?), (.*)$", r)
    if m and all(re.match(r"^(?:[A-Z][a-z]*\.?[ -]?)*[A-Z][\w'-]+(?: II| Jr\.?)?$", fold(p.strip())) for p in re.split(r", | and ", m.group(1))):
        return m.group(1), m.group(2)
    if ", " in r:
        return tuple(r.split(", ", 1))
    return "", r


def fold(s):
    return "".join(c for c in unicodedata.normalize("NFKD", s) if not unicodedata.combining(c))


NAME_ORDER = {"Bai XunDi": ("Bai", "XunDi"), "Tran Van Trung": ("Tran Van Trung", "")}


def name_parts(n):
    n = re.sub(r"\s+", " ", n).strip()
    if n in NAME_ORDER:
        return NAME_ORDER[n]
    tk = re.sub(r" (II|Jr\.?)$", "", n).split(" ")
    dot = [i for i, x in enumerate(tk) if x.endswith(".")]
    if dot:
        return " ".join(tk[dot[-1] + 1:]), " ".join(tk[:dot[-1] + 1])
    if len(tk) == 1:
        return tk[0], ""
    return tk[-1], " ".join(tk[:-1])


def person_key(sur, given):
    return fold(sur).lower(), fold(given)[:1].lower()


def outside_parens(s):
    o, d = [], 0
    for ch in s:
        if ch == "(":
            d += 1
        elif ch == ")":
            d = max(0, d - 1)
        elif not d:
            o.append(ch)
    return "".join(o)


def credit_names(c):
    c = re.sub(r"\b(19|20)\d\d\b", "", outside_parens(pub(c)))
    return [x.strip() for x in re.split(r",|\band\b|\bwith\b|\bor\b", c) if x.strip() and not re.search(r"\d", x)]


def title_of(rest):
    m = re.search(r", (?=in:|Zenodo|arXiv|PhD|Ph\.D|https?:|[A-Z][^,]*\d)", rest)
    return rest[:m.start()] if m else rest


def year_of(r, rid=""):
    if rid.startswith("web-"):
        return ""
    m = re.search(r"(\d{4})[a-z]?$", rid)
    if m:
        return m.group(1)
    m = re.findall(r"\((\d{4})\)", r) or re.findall(r"\b(19\d\d|20\d\d)\b", r)
    return m[-1] if m else ""


KHASH = ("<script>(function(){var m=location.hash.match(/^#k=(\\d+)$/);if(!m)return;var k=+m[1],rs=document.querySelectorAll('table.lg tbody tr[id^=k]');"
         "for(var i=0;i<rs.length;i++){var p=rs[i].cells[0].textContent.replace(/,/g,'').split(' to '),a=+p[0],b=+(p[1]||p[0]);if(k>=a&&k<=b){rs[i].classList.add('hit');rs[i].scrollIntoView({block:'center'});break}}})()</script>"
         "<script>(function(){var bs=document.querySelectorAll('.chips button'),rs=document.querySelectorAll('table.lg tbody tr'),n=document.getElementById('fn');if(!n)return;"
         "bs.forEach(function(b){b.addEventListener('click',function(){var f=b.getAttribute('data-f'),c=0;bs.forEach(function(x){x.setAttribute('aria-pressed',x===b?'true':'false')});"
         "rs.forEach(function(r){var on=(' '+r.getAttribute('data-f')+' ').indexOf(' '+f+' ')>=0;r.hidden=!on;if(on)c++});n.textContent=f=='all'?'':c+(c==1?' size':' sizes')})})})()</script>")
COUNTER = '<script data-goatcounter="https://coveringarraytools.goatcounter.com/count" async src="//gc.zgo.at/count.js"></script>'
TIER_WORD = {"VERIFIED": "verified", "CITED": "cited", "SCREENED": "screened", "DISPUTED": "disputed", "FAILED_PENDING_RECHECK": "failed, pending recheck"}
SOURCE_NAME = {"S1": "Colbourn's tables", "S4": "NIST covering array library", "S5": "Dwyer CA_Database", "S6": "CAs R package data"}


PUBLIC_TEXT = [
    (r"\s*\(tools/own_arrays/[\w.-]*\)", ""),
    (r"\(tools/own_arrays/[\w.-]+[,:;]\s*", "("),
    (r",\s*tools/own_arrays/[\w.-]+(?=[,)])", ""),
    (r"\s*\btools/own_arrays/[\w.-]+", ""),
    (r"\bthe first version of [\w.-]+:\s*", "first version: "),
    (r",\s*formerly published on his site \(no longer online\)", ""),
    (r"\bpostop ?NCK\b", "post-optimization (Nayeri, Colbourn and Konjevod)"),
    (r"\bthis project's\b", "the table's"),
    (r"\bext2\.c\s+", ""),
    (r" \(the search\)", " (search)"),
    (r",?\s*entered by [a-z][a-z0-9.-]*-20\d\d-[a-z0-9.-]+", ""),
    (r"\barray_sha256 ", "sha256 "),
]


def pub(c):
    for a, b in PUBLIC_TEXT:
        c = re.sub(a, b, c)
    return c


def credit_or_source(R, r):
    c = R.credit_of(r) if r else ""
    if c:
        return pub(c)
    return source_name(r) if r else ""


CAS_DATA = {"TJ2level_CAs": "J. Torres-Jimenez, via the CAs R package",
            "CAEX_CAs": "Torres-Jimenez, Acevedo-Juarez and Avila-George 2021, via the CAs R package"}


def source_name(r):
    if r.get("source_id") == "S6":
        m = re.match(r"CAs data (\w+)", r.get("source_detail") or "")
        if m and m.group(1) in CAS_DATA:
            return CAS_DATA[m.group(1)]
    return SOURCE_NAME.get(r.get("source_id", ""), "source not named")


def segments(c):
    out, d, cur = [], 0, ""
    i = 0
    while i < len(c):
        ch = c[i]
        if ch == "(":
            d += 1
        elif ch == ")":
            d = max(0, d - 1)
        if not d and ch == ")" and c[i + 1:i + 3] == ", ":
            out.append(cur + ch)
            cur = ""
            i += 3
            continue
        cur += ch
        i += 1
    if cur.strip():
        out.append(cur)
    segs = []
    for x in out:
        x = x.strip()
        m = re.match(r"^(.*?)\s*\((.*)\)$", x, re.S)
        name, role = (m.group(1), m.group(2)) if m else (x, "")
        r = role.lower()
        if re.match(r"^(19|20)\d\d$", role):
            name, role, r = name + " " + role, "", ""
        if r.startswith(("the derivation", "the array", "the search", "this project's", "the post-optimisation")):
            kind = "builder"
        elif "function" in r and "package" in r:
            kind = "tool"
        elif re.match(r"^(the method|the doubling|the product|the direct product|corollary|lemma|theorem|construction)", r):
            kind = "method"
        elif "ingredient" in r or "starting array" in r or r.startswith("the construction of the"):
            kind = "ingredient"
        elif re.search(r"\bsearch\b", r):
            kind = "builder"
        elif "the size" in r:
            kind = "size"
        elif re.match(r"^(the method|the doubling|the product|the direct product|corollary|lemma|theorem|construction)", r):
            kind = "method"
        else:
            kind = "author" if re.search(r"\b(19|20)\d\d\b", name) else "plain"
        segs.append(dict(name=pub(name).strip(), kind=kind))
    return segs


def names(segs, kinds):
    return "; ".join(s["name"] for s in segs if s["kind"] in kinds)


def builders_of(c):
    segs = segments(c)
    b = names(segs, ("builder",))
    if not b and all(s["kind"] == "plain" for s in segs):
        b = names(segs, ("plain",))
    return b


SOURCE_PEOPLE = {"TJ2level_CAs": ["J. Torres-Jimenez"], "CAEX_CAs": ["J. Torres-Jimenez", "B. Acevedo-Juarez", "H. Avila-George"]}
KEEPERS = {"S5": "Aaron Dwyer"}


def source_people(r):
    m = re.match(r"CAs data (\w+)", r.get("source_detail") or "") if r.get("source_id") == "S6" else None
    return SOURCE_PEOPLE.get(m.group(1), []) if m else []


def builder_segs(segs):
    b = [s for s in segs if s["kind"] == "builder"]
    return b or ([s for s in segs if s["kind"] == "plain"] if all(s["kind"] == "plain" for s in segs) else [])


def reach_segs(c):
    segs = segments(c)
    for ks in (("size",), None, ("author", "method", "plain"), ("ingredient",), ("tool",)):
        got = builder_segs(segs) if ks is None else [s for s in segs if s["kind"] in ks]
        if got:
            return got
    return []


def array_by_text(R, r):
    c = R.credit_of(r) if r else ""
    if not c:
        return ("from " + source_name(r)) if r else ""
    b = builders_of(c)
    return ("built by " + b) if b else ("credit: " + names(segments(c), ("size", "author", "ingredient", "method", "plain")))


def row_who(R, r):
    c = R.credit_of(r)
    if not c:
        return source_name(r)
    return builders_of(c) or names(segments(c), ("size", "author", "ingredient", "method", "plain"))


def reached_by(R, r):
    c = R.credit_of(r)
    if c:
        segs = segments(c)
        return (names(segs, ("size",)) or builders_of(c) or names(segs, ("author", "method", "plain")) or names(segs, ("ingredient",)) or names(segs, ("tool",))), []
    refs = [i for i in (r.get("builds_on") or "").split(";") if i in R.REFS]
    if refs:
        return "", refs
    src = source_name(r)
    lab = pub(R.page_text(R.construction_of(r) or ""))
    return ("%s (%s)" % (src, lab) if lab and r.get("source_id") == "S1" else src), []


def fam(ver, rungs):
    s = ver / rungs if rungs else 0
    return "f4" if s >= .9 else "f3" if s >= .5 else "f2" if s > .1 else "f1" if ver else "f0"


PREVIEW_CELLS = 200000


def previewable(m):
    return not m["file"].endswith(".gz") and int(m["N"]) * int(m["k"]) <= PREVIEW_CELLS and not (m.get("location") or "").startswith("http")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--preview", action="store_true")
    ap.add_argument("--sparse-list", action="store_true")
    a = ap.parse_args()
    tools = os.path.join(a.repo, "tools")
    tdir = os.path.join(a.repo, "table")
    if a.sparse_list:
        for m in csv.DictReader(open(os.path.join(tdir, "MANIFEST.csv"), newline="", encoding="utf-8")):
            if previewable(m):
                print("/table/arrays/" + m["file"])
        print("/table/certificates/CERTIFICATES.csv")
        print("/table/constructions/CONSTRUCTIONS.csv")
        return
    sys.path.insert(0, tools)
    sys.path.insert(0, tdir)
    import render_table as R
    import builds_on
    import lower_bounds
    sys.setrecursionlimit(100000)
    rows, manifest = R.load(tdir)
    import build_frame
    by_id = dict(zip(build_frame.row_ids(rows), rows))
    first = {}
    with open(os.path.join(tdir, "ca_frame.csv"), newline="", encoding="utf-8") as f:
        for fr in csv.DictReader(f):
            if fr["basis"] == "row" and fr["first_reached"] in by_id:
                first[(int(fr["t"]), int(fr["v"]), int(fr["k"]), int(fr["N"]))] = by_id[fr["first_reached"]]
    R.REFS.update(builds_on.load(tdir))
    certs = {}
    cfile0 = os.path.join(tdir, "certificates", "CERTIFICATES.csv")
    if os.path.exists(cfile0):
        for x in csv.DictReader(open(cfile0, newline="", encoding="utf-8")):
            m = re.match(r"CPHF\((\d+); (\d+), (\d+), (\d+)\)", x["family"])
            if m:
                cf = dict(family="CPHF(%s; %s, %s, %s)" % m.groups(), t=int(m.group(4)), q=int(m.group(3)), file=x["file"])
                certs.setdefault(x["array_sha256"], cf)
                certs.setdefault("f:" + x["family_sha256"], cf)

    def cert_of(r):
        if not r:
            return None
        return certs.get(r.get("array_sha256") or "-") or certs.get("f:" + (r.get("family_sha256") or "-"))
    _, lb = lower_bounds.load(os.path.join(tdir, "lower_bounds.csv"))
    for r in lb:
        R.LB.setdefault((r[0], r[1]), []).append(r)
    R.LB_CLOSED.update(lower_bounds.closed_steps(lb, os.path.join(tdir, "ca_frame.csv"), os.path.join(tdir, "ca_table.csv")))
    ext = {}
    xp = os.path.join(tdir, "EXTERNAL.csv")
    if os.path.exists(xp):
        for e in csv.DictReader(open(xp, newline="", encoding="utf-8")):
            ext[e["sha256"]] = e["location"]
    arrays = list(manifest)
    seen_sha = {m["sha256"] for m in manifest}
    if os.path.exists(xp):
        for e in csv.DictReader(open(xp, newline="", encoding="utf-8")):
            if e["sha256"] in seen_sha:
                continue
            seen_sha.add(e["sha256"])
            member = e["location"].split("::")[1] if "::" in e["location"] else ""
            arrays.append(dict(file=os.path.basename(member or e["location"].split("?")[0]), member=member, t=e["t"], v=e["v"], k=e["k"], N=e["N"],
                               sha256=e["sha256"], verify_stamp=e.get("verify_stamp", ""), location=e["location"]))
    site = Site(a.out, a.preview)
    site.commit = git_commit(a.repo)
    site.date = max(r["entered"] for r in rows)
    os.makedirs(os.path.join(a.out, "assets"), exist_ok=True)
    open(os.path.join(a.out, "assets", "site.css"), "w").write(CSS)

    tv = collections.defaultdict(list)
    for r in rows:
        tv[(r["t"], r["v"])].append(r)
    by_sha = collections.defaultdict(list)
    for r in rows:
        if r["array_sha256"]:
            by_sha[r["array_sha256"]].append(r)
    man = {m["sha256"]: m for m in arrays}

    def ca(n, t, k, v):
        return "CA(%s; %d, %s, %d)" % (format(n, ","), t, format(k, ","), v)

    array_path = {}
    stc = collections.Counter()
    groups = collections.defaultdict(list)
    for m in arrays:
        groups[(int(m["N"]), int(m["t"]), int(m["k"]), int(m["v"]))].append(m["sha256"])
    for key, shas in groups.items():
        base = "ca/%d/%d/%d/%d/" % key
        if len(shas) == 1:
            array_path[shas[0]] = base
        else:
            for s in shas:
                array_path[s] = base + s[:8] + "/"

    import priority
    known = priority.known_slugs(a.repo)
    try:
        ls = subprocess.run(["git", "-C", a.repo, "ls-tree", "-d", "--name-only", "HEAD", "submissions/", "table/constructions/"], capture_output=True, text=True).stdout
        known |= {os.path.basename(x) for x in ls.split()}
    except OSError:
        pass
    prio = priority.row_dates(rows, tdir, known)
    gpos, fsnap = {}, {}
    for i, r in enumerate(rows):
        key = (r.get("snapshot_id") or "", r.get("entered") or "")
        gpos[id(r)] = (prio[i], fsnap.setdefault(key, i) if key[0] else i, i)

    def reach_pieces(rs, n, k0, k1):
        cand = [r for r in R.counted(rs) if r["N"] <= n and r["k"] >= k0]
        out, k = [], k0
        while k <= k1:
            live = [r for r in cand if r["k"] >= k]
            w = min(live, key=lambda r: gpos[id(r)])
            hi = min([r["k"] for r in live] + [k1])
            rb = reached_by(R, w)
            same = sorted(re.findall(r"[^\W\d]+|\d{4}", (rb[0] or " ".join(R.ref_label(i) for i in rb[1])).replace(" and ", " ")))
            if out and out[-1][4] == same:
                out[-1][1] = hi
                if rb[0] and not out[-1][3][0]:
                    out[-1][2:4] = [w, (rb[0], tuple(rb[1]))]
            else:
                out.append([k, hi, w, (rb[0], tuple(rb[1])), same])
            k = hi + 1
        return out

    cons_sha = {}
    cfile1 = os.path.join(tdir, "constructions", "CONSTRUCTIONS.csv")
    if os.path.exists(cfile1):
        for x in csv.DictReader(open(cfile1, newline="", encoding="utf-8")):
            if x.get("array_sha256"):
                cons_sha.setdefault(x["array_sha256"], x["file"])
    wfile = os.path.join(tdir, "withdrawn_files.csv")
    withdrawn = {x["sha256"] for x in csv.DictReader(open(wfile, newline="", encoding="utf-8"))} if os.path.exists(wfile) else set()
    fdrv = collections.defaultdict(list)
    with open(os.path.join(tdir, "ca_frame.csv"), newline="", encoding="utf-8") as f:
        for fr in csv.DictReader(f):
            if fr["basis"] == "derived":
                fdrv[(int(fr["t"]), int(fr["v"]))].append((int(fr["k"]), int(fr["N"])))

    cells = {}
    for (t, v), rs in sorted(tv.items()):
        st = R.stair(rs)
        dis = {(r["k"], r["N"]) for r in rs if r["tier"] == "DISPUTED"}
        rungs = []
        for n, k0, k1, ev in st:
            ver = [e for e in ev if e["tier"] == "VERIFIED"]
            sha = next((e["array_sha256"] for e in sorted(ver, key=lambda e: e["source_id"] != "S8") if e["array_sha256"] in array_path), "")
            best = next((e for e in sorted(ver, key=lambda e: e["source_id"] != "S8") if sha and e["array_sha256"] == sha), None) or (sorted(ver, key=lambda e: e["source_id"] != "S8") + list(ev))[0]
            f = R.floor_at(t, v, k0)
            f0 = lower_bounds.lower_bound(t, k0, v)[0]
            f1 = lower_bounds.lower_bound(t, k1, v)[0]
            of = R.optimal_from(t, v, k0, k1, n) if (t, v, k1, n) in R.LB_CLOSED else None
            rungs.append(dict(N=n, k0=k0, k1=k1, floor=f0, floor_k_to=f1, floor_row=f, closed=of == k0, opt_from=of,
                              verified=bool(ver), credit=credit_or_source(R, best), construction=pub(R.page_text(R.construction_of(best) or "")),
                              builds_on=[i for i in (best.get("builds_on") or "").split(";") if i in R.REFS], sha=sha,
                              entered=best["entered"], row=best, cert=next((cert_of(e) for e in ev if cert_of(e)), None), cert_row=next((e for e in ev if cert_of(e)), None), first=first.get((t, v, k1, n)) or min(ev, key=lambda e: e["entered"]), pieces=reach_pieces(rs, n, k0, k1), disputed=not ver and (k1, n) in dis,
                              ccert=next((cons_sha[e["array_sha256"]] for e in ver if e["array_sha256"] in cons_sha), "") if not sha else "",
                              gone=not sha and any(e["array_sha256"] in withdrawn for e in ver), new=all(e["entered"] > SNAPSHOT_DATE for e in ev)))
        cells[(t, v)] = dict(t=t, v=v, rungs=rungs, kmax=max(r["k"] for r in rs), kmin=min(r["k"] for r in rs), last=max(r["entered"] for r in rs),
                             nver=sum(1 for x in rungs if x["verified"]), nopt=sum(1 for x in rungs if x["opt_from"] is not None),
                             nnew=sum(1 for x in rungs if x["new"]))

    def cell_path(t, v):
        return "t%d/v%d/" % (t, v)

    def row_path(t, v, k):
        rs = cells[(t, v)]["rungs"] if (t, v) in cells else []
        x = next((x for x in rs if x["k0"] <= k <= x["k1"]), rs[-1] if rs and k > rs[-1]["k1"] else None)
        return cell_path(t, v) + ("#k%d" % x["k1"] if x else "")

    def ref_path(rid):
        return "library/%s/" % re.sub(r"[^A-Za-z0-9._-]", "-", rid)

    def tile(c, d, h):
        cls = fam(c["nver"], len(c["rungs"]))
        return ('<a class="el %s" href="%s" data-tv="%d-%d"><span class=vh>t=%d v=%d: </span><div class=tp>k to %s</div><div class=n>%d<small>sizes</small></div>'
                '<div class=ft><div class=st><span><b>%d</b> verified</span><span><b>%d</b> optimal</span></div><span class=dt>%s</span></div></a>') % (
            cls, h(cell_path(c["t"], c["v"])), c["t"], c["v"], c["t"], c["v"], format(c["kmax"], ","), len(c["rungs"]), c["nver"], c["nopt"], datetime.date.fromisoformat(c["last"][:10]).strftime("%b %Y"))

    h0 = lambda p: site.href(0, p)

    def block(ts, vs, label):
        s = '<p class=bl>%s</p><div class=bsc><div class=blk><span></span>' % label + "".join('<span class=h>v%d</span>' % v for v in vs) + "".join("<span></span>" for _ in range(12 - len(vs)))
        for t in ts:
            s += '<span class=r>t%d</span>' % t
            for v in vs:
                c = cells.get((t, v))
                s += tile(c, 0, h0) if c else '<span class="el none"></span>'
            s += "".join("<span></span>" for _ in range(12 - len(vs)))
        return s + "</div></div>"

    main_ts = [t for t in range(2, 7)]
    hi_ts = sorted(t for (t, v) in cells if t >= 7)
    nrows = len(rows)
    nver = sum(1 for r in rows if r["tier"] == "VERIFIED")
    narr = len(arrays)
    nopt = sum(c["nopt"] for c in cells.values())
    look = {}
    for (t, v), c in cells.items():
        look["%d-%d" % (t, v)] = dict(r=[[x["k1"], x["N"], x["opt_from"] or 0, 1 if x["verified"] else 0] for x in c["rungs"]],
                                      f=[[r[2], r[3], r[4]] for r in R.LB.get((t, v), ())],
                                      s=[len(c["rungs"]), c["nver"], c["nopt"], c["nnew"], c["kmax"], c["rungs"][0]["N"], c["rungs"][0]["k1"], c["last"], c["kmin"]],
                                      p=h0(cell_path(t, v)))
    jsonld = json.dumps({"@context": "https://schema.org", "@type": "Dataset", "@id": BASE + "#dataset",
                         "name": "Covering Array Tools: best known covering arrays CA(N; t, k, v)",
                         "alternateName": ["covering array table", "ca-tools table"],
                         "description": "Best known sizes of covering arrays CA(N; t, k, v) for strengths 2 to 6 with up to 25 symbols and binary arrays at strengths 7 to 10, with proven lower bounds, credit, construction, published sources and checked arrays to download. %d entries and %d arrays to download." % (nrows, narr),
                         "url": BASE, "sameAs": REPO_URL, "identifier": "https://doi.org/" + DOI,
                         "keywords": ["covering arrays", "covering array number", "CAN(t,k,v)", "covering array table", "combinatorial testing"],
                         "creator": {"@type": "Person", "name": "Christopher Smolen"},
                         "license": "https://creativecommons.org/licenses/by/4.0/", "isAccessibleForFree": True, "dateModified": site.date,
                         "distribution": [{"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": RAW + "table/ca_table.csv"}]},
                        ensure_ascii=False).replace("</", "<\\/")
    home = ('<div class=hero id=lookup><div class=in><div><h1>Best known covering arrays, with evidence.</h1>'
            '<p>Every entry names who built it or where it comes from and how it was built, and most name the published work they build on. Verified entries say where to get the checked array (a file to download, a public deposit, or the certificate that builds it) or that its file is no longer stored. '
            'Proven lower bounds sit beside every size. The table grows by pull request and rebuilds on every merge.</p></div>'
            '<form class=look onsubmit="return look()"><h2>Look up a size</h2><div class=lf><span><label for=lt>strength t</label><input id=lt value=3 inputmode=numeric></span>'
            '<span><label for=lv>symbols v</label><input id=lv value=3 inputmode=numeric></span><span><label for=lk>columns k</label><input id=lk value=6 inputmode=numeric></span>'
            '<button>Find</button></div><div class=ans id=ans role=status aria-live=polite><span class=mute>Enter t, v and k, then Find.</span></div></form></div></div>'
            '<div class=hstats><span></span><div><b class=num>%s</b><span>entries</span></div><div><b class=num>%s</b><span>verified entries</span></div>'
            '<div><b class=num>%s</b><span>arrays to download</span></div><div><b class=num>%s</b><span>optimal sizes</span></div>'
            '<div><b>2 to 6</b><span>strengths, v to 25</span></div><div><b>7 to 10</b><span>strengths, binary</span></div></div>'
            '<main class=wrapw>%s%s%s<div class=key>%s<span>tile: k reached, sizes, verified sizes, optimal sizes, month of last change</span></div></main>'
            '<aside class=panel id=panel role=dialog aria-labelledby=pt><div class=hd><span id=pl></span><button class=x id=px onclick="closeP()" aria-label="Close summary">&times;</button></div>'
            '<h2 class=big id=pt tabindex=-1></h2><p class=nm id=pn></p><dl><dt>sizes</dt><dd id=p0></dd><dt>verified</dt><dd id=p1></dd><dt>optimal</dt><dd id=p2></dd>'
            '<dt><a href="%s#new-since-the-first-release">new since the first release</a></dt><dd id=p3></dd><dt>columns covered</dt><dd id=p4></dd><dt>first size</dt><dd id=p5></dd></dl><a class=go id=pgo></a></aside>') % (
        format(nrows, ","), format(nver, ","), format(narr, ","), format(nopt, ","),
        block(main_ts, list(range(2, 14)), "alphabets 2 to 13"), block(main_ts, list(range(14, 26)), "alphabets 14 to 25"),
        block(hi_ts, [2], "binary, strengths 7 to 10") if hi_ts else "",
        "".join('<span><i class=%s></i>%s</span>' % kv for kv in [("f4", "all sizes verified"), ("f3", "mostly verified"), ("f2", "partly verified"), ("f1", "a few verified"), ("f0", "cited only")]), h0("learn/"))
    script = ("<script>var D=%s;var cur=null;function fmt(n){return n.toLocaleString('en-US')}"
              "function openP(id){var c=D[id];if(!c)return;var p=id.split('-');document.querySelectorAll('.el.sel').forEach(function(e){e.classList.remove('sel')});"
              "if(cur===id){closeP();return}cur=id;document.querySelector('[data-tv=\"'+id+'\"]').classList.add('sel');var s=c.s;"
              "document.getElementById('pl').textContent='last change '+s[7];document.getElementById('pt').textContent='t='+p[0]+' v='+p[1];"
              "document.getElementById('pn').textContent='Strength '+p[0]+' covering arrays on '+p[1]+' symbols';"
              "document.getElementById('p0').textContent=fmt(s[0]);document.getElementById('p1').textContent=fmt(s[1]);document.getElementById('p2').textContent=fmt(s[2]);"
              "document.getElementById('p3').textContent=fmt(s[3]);document.getElementById('p4').textContent=s[8]+' to '+fmt(s[4]);"
              "document.getElementById('p5').textContent='CA('+fmt(s[5])+'; '+p[0]+', '+s[6]+', '+p[1]+')';var g=document.getElementById('pgo');g.href=c.p;g.textContent='Open t='+p[0]+' v='+p[1];"
              "document.getElementById('panel').classList.add('open');document.getElementById('pt').focus()}"
              "var last=null;function closeP(){if(last)last.focus();cur=null;document.getElementById('panel').classList.remove('open');document.querySelectorAll('.el.sel').forEach(function(e){e.classList.remove('sel')})}"
              "document.querySelectorAll('.el[data-tv]').forEach(function(e){e.addEventListener('click',function(ev){ev.preventDefault();last=e;openP(e.dataset.tv)})});"
              "document.addEventListener('keydown',function(ev){if(ev.key=='Escape'&&cur)closeP()});"
              "document.addEventListener('click',function(ev){if(cur&&!ev.target.closest('#panel')&&!ev.target.closest('.el[data-tv]')){last=null;closeP()}});"
              "function flash(a){a.classList.remove('hit');void a.offsetWidth;a.classList.add('hit')}"
              "function say(a,m){a.innerHTML='<span class=mute>'+m+'</span>';flash(a);return false}"
              "function look(){var tv=document.getElementById('lt').value.trim(),vv=document.getElementById('lv').value.trim(),kv=document.getElementById('lk').value.trim(),a=document.getElementById('ans');"
              "if(!/^\\d+$/.test(tv)||!/^\\d+$/.test(vv)||!/^\\d+$/.test(kv))return say(a,'Enter whole numbers for t, v and k.');"
              "var t=+tv,v=+vv,k=+kv;if(k<t)return say(a,'k must be at least t: an array of strength '+t+' needs at least '+t+' columns.');"
              "var c=D[t+'-'+v];if(!c)return say(a,'The table has no entries for t = '+t+' and v = '+v+'.');"
              "var r=null;for(var i=0;i<c.r.length;i++){if(c.r[i][0]>=k){r=c.r[i];break}}"
              "if(!r)return say(a,'The table covers k up to '+fmt(c.s[4])+' for t = '+t+' and v = '+v+'.');"
              "var f=null;for(var j=0;j<c.f.length;j++){if(c.f[j][0]<=k&&k<=c.f[j][1]){f=c.f[j][2]}}"
              "var op=r[2]&&k>=r[2];if(op)f=r[1];a.innerHTML='CAN('+t+', '+fmt(k)+', '+v+') '+(op?'= ':'&le; ')+'<b>'+fmt(r[1])+'</b> '+(op?'<span class=\"tag opt\">optimal</span>':(r[3]?'<span class=\"tag ver\">verified</span>':'<span class=\"tag lit\">cited</span>'))"
              "+'<br><span class=mute>'+(f?'Lower bound '+fmt(f)+'. ':'')+'</span><a href=\"size/?t='+t+'&k='+k+'&v='+v+'\">Open this size</a>';flash(a);return false}</script>") % json.dumps(look, separators=(",", ":"))
    lbmap = {key: val["f"] for key, val in look.items()}
    site.write("assets/lb.json", json.dumps(lbmap, separators=(",", ":")), False)
    sjs = r"""<script>(function(){var R='../',P=new URLSearchParams(location.search),t=+P.get('t'),k=+P.get('k'),v=+P.get('v'),out=document.getElementById('sz'),lb=null;
['st','sk','sv'].forEach(function(id,i){var x=[t,k,v][i];if(x)document.getElementById(id).value=x});
function F(n){return n==null?'':(+n).toLocaleString('en-US')}
function E(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]})}
function U(a,b,c){return '?t='+a+'&k='+b+'&v='+c}
function J(u){return fetch(R+u).then(function(r){if(!r.ok)throw 0;return r.json()})}
function rung(d,kk){for(var i=0;i<d.rungs.length;i++){var x=d.rungs[i];if(x.k_from<=kk&&kk<=x.k_to)return x}return null}
function floorAt(tt,vv,kk,x){var f=lb&&lb[tt+'-'+vv],b=null;if(f)for(var i=0;i<f.length;i++)if(f[i][0]<=kk&&kk<=f[i][1])b=f[i][2];var a=x&&x.floor;return b!=null&&(a==null||b>=a)?[b,1]:[a,0]}
function say(h){out.innerHTML='<p class=mute>'+h+'</p>'}
if(!t||!k||!v){say('Enter t, k and v above, then Find.');return}
if(k<t){say('k must be at least t: an array of strength '+t+' needs at least '+t+' columns.');return}
document.title='CAN('+t+', '+F(k)+', '+v+'): best known covering array size';
J('assets/lb.json').catch(function(){return null}).then(function(l){lb=l;return J('t'+t+'/v'+v+'.json')}).then(function(d){
var x=rung(d,k);if(!x){say('The table has t = '+t+' and v = '+v+' for k up to '+F(d.rungs[d.rungs.length-1].k_to)+'. <a href="'+R+'t'+t+'/v'+v+'/">Open the table for t='+t+' v='+v+'</a>.');return}
var fl=floorAt(t,v,k,x),op=x.optimal_from&&k>=x.optimal_from,gap=fl[0]!=null?x.N-fl[0]:null;
var tag=op?'<span class="tag opt">optimal</span>':(x.status=='cited'?'<span class="tag lit">cited</span>':'<span class="tag ver">verified</span>');
var bo=(x.builds_on||[]).map(function(id,i){return '<a href="'+R+'library/'+id+'/">'+E((x.builds_on_names||[])[i]||id)+'</a>'}).join(', ');
var arr=x.array_page?'<a href="'+x.array_page+'">CA('+F(x.N)+'; '+t+', '+F(x.k_to)+', '+v+')</a>'+(x.k_to>k?' <span class=mute>(take any '+F(k)+' of its columns)</span>':''):(x.family?'<a href="'+R+x.family_page+'">'+E(x.family)+'</a> <span class=mute>(family on file, expands to the array)</span>':'<span class=mute>none on file</span>');
var h='<div class=szh><div><p class=crumb><a href="'+R+'t'+t+'/v'+v+'/">t='+t+' v='+v+'</a> / k = '+F(k)+'</p><h1>CAN('+t+', '+F(k)+', '+v+') '+(op?'=':'&le;')+' '+F(x.N)+'</h1>'
+'<p>'+tag+' The smallest known covering array of strength '+t+' on '+F(k)+' columns with '+v+' symbols has '+F(x.N)+' rows.</p></div></div>'
+'<div class=szg><dl class=szd><dt>best known size</dt><dd>'+F(x.N)+' rows, for every k from '+F(x.k_from)+' to '+F(x.k_to)+'</dd>'
+'<dt>lower bound</dt><dd>'+(fl[0]!=null?(fl[1]?'':'at least ')+F(fl[0])+(gap!=null?', gap '+F(gap):''):'not on record')+'</dd>'
+'<dt>first reached by</dt><dd>'+E(x.first_reached_by||'')+'</dd><dt>construction</dt><dd>'+E(x.construction||'')+(bo?'<br><span class=mute>builds on</span> '+bo:'')+'</dd>'
+'<dt>array</dt><dd>'+arr+(x.array_by?'<br><span class=mute>'+E(x.array_by)+'</span>':'')+'</dd></dl>'
+'<div><h2>Neighbouring sizes</h2><div class=nb id=nb></div><p class=mute style="font-size:.85rem;margin-top:14px"><a href="'+R+'t'+t+'/v'+v+'/#k'+x.k_to+'">See this size in the table</a></p></div></div>';
var cut=h.indexOf('<div class=szg>');document.getElementById('szhead').innerHTML=h.slice(0,cut);out.innerHTML=h.slice(cut);
var nb=[['k - 1',t,k-1,v],['k + 1',t,k+1,v],['t - 1',t-1,k,v],['t + 1',t+1,k,v],['v - 1',t,k,v-1],['v + 1',t,k,v+1]].filter(function(n){return n[1]>=2&&n[3]>=2&&n[2]>=n[1]});
var box=document.getElementById('nb');box.innerHTML=nb.map(function(n,i){return '<a id=nb'+i+' href="'+U(n[1],n[2],n[3])+'"><span>'+n[0]+'</span><b>CAN('+n[1]+', '+F(n[2])+', '+n[3]+')</b><i>&nbsp;</i></a>'}).join('');
nb.forEach(function(n,i){J('t'+n[1]+'/v'+n[3]+'.json').then(function(dd){var y=rung(dd,n[2]);document.querySelector('#nb'+i+' i').textContent=y?'≤ '+F(y.N):'not in the table'}).catch(function(){document.querySelector('#nb'+i+' i').textContent='not in the table'})})
}).catch(function(){say('The table has no entries for t = '+t+' and v = '+v+'.')})})()</script>"""
    sbody = ('<main class=wrapw><div class=sztop><div id=szhead></div><form class="look szf" action="./" method=get><h2>Look up a size</h2><div class=lf><span><label for=st>strength t</label><input id=st name=t inputmode=numeric></span>'
             '<span><label for=sk>columns k</label><input id=sk name=k inputmode=numeric></span><span><label for=sv>symbols v</label><input id=sv name=v inputmode=numeric></span><button>Find</button></div></form></div>'
             '<div id=sz aria-live=polite></div></main>')
    site.page("size/index.html", "Look up a covering array size CAN(t, k, v)", "The best known size, lower bound, credit and array for any strength t, columns k and symbols v in the covering array table.", sbody, "Table", None, sjs)

    site.page("index.html", "Covering Array Tools: best known covering arrays, with evidence",
              "Best known covering array sizes CA(N; t, k, v) with proven lower bounds, credit, construction and checked arrays to download.",
              home, "Table", jsonld, script)

    def rule_p(t, v, c, h):
        nd = sum(1 for k, _ in fdrv.get((t, v), []) if k <= c["kmax"])
        return ('<p class=mute style="font-size:.88rem">Sizes follow the table\'s <a href="%s#counting-rule">Colbourn rule</a>: cited and verified rows count.%s</p>' % (
            h("learn/"), (' The <a href="%stable/ca_frame.csv">frame file</a>, which also counts proven derived sizes, has a smaller N at %s of its steps in this range.' % (
                RAW, format(nd, ","))) if nd else ""))

    for (t, v), c in cells.items():
        path = cell_path(t, v) + "index.html"
        d = 2
        h = lambda p, d=d: site.href(d, p)
        trs = []
        for x in c["rungs"]:
            gap = x["N"] - x["floor"] if x["floor"] is not None else None
            lbt = format(x["floor"], ",") if x["floor"] is not None else ""
            gpt = format(gap, ",") if gap is not None else ""
            if x["floor"] is not None and x["floor_k_to"] is not None and x["floor_k_to"] != x["floor"]:
                lbt = "%s to %s" % (format(x["floor"], ","), format(x["floor_k_to"], ","))
                gpt = "%s to %s" % (format(x["N"] - x["floor_k_to"], ","), format(gap, ","))
            if x["closed"]:
                status = '<span class="tag opt">optimal</span>'
            elif x["opt_from"] is not None:
                status = '<span class="tag opt">optimal at k = %s</span>' % (format(x["k1"], ",") if x["opt_from"] == x["k1"] else "%s to %s" % (format(x["opt_from"], ","), format(x["k1"], ",")))
            elif x["verified"]:
                status = '<span class="tag ver">verified</span>'
            else:
                status = '<span class="tag lit">cited</span>'
            if x["disputed"]:
                status += '<a class="tag dis" href="%s#disputed">disputed</a>' % h("learn/")
            bo = ", ".join('<a href="%s">%s</a>' % (h(ref_path(i)), E(R.ref_label(i))) for i in x["builds_on"])
            arr = ('<a href="%s">%s</a>' % (h(array_path[x["sha"]]), ca(x["N"], t, x["k1"], v))) if x["sha"] else (
                ('<a href="%s/tree/main/table/constructions/%s">construction certificate</a><span class=sub>builds the array; checked exactly</span>' % (REPO_URL, x["ccert"])) if x["ccert"] else
                ('<span class=mute>checked; file no longer stored</span><span class=sub><a href="%stable/withdrawn_files.csv">why</a></span>' % RAW) if x["gone"] else '<span class=mute>none on file</span>')
            also = sorted((int(m["k"]), m["sha256"]) for m in arrays if int(m["t"]) == t and int(m["v"]) == v and int(m["N"]) == x["N"]
                          and x["k0"] <= int(m["k"]) <= x["k1"] and m["sha256"] != x["sha"] and m["sha256"] in array_path)
            if also:
                arr += '<span class=sub>also on file: %s</span>' % ", ".join('<a href="%s">%s</a>' % (h(array_path[s2]), ca(x["N"], t, k2, v)) for k2, s2 in also)
            kr = format(x["k1"], ",") if x["k0"] == x["k1"] else "%s to %s" % (format(x["k0"], ","), format(x["k1"], ","))
            con = x["construction"]
            key = h("learn/") + "#colbourn-labels"
            if x["row"].get("source_id") == "S1" and con:
                con_h = '<a class=ck href="%s">%s</a>' % (key, E(con))
            else:
                con_h = E(con)

            def rb_html(p):
                rb, rrefs = p[3]
                if rb:
                    return ('<a class=ck href="%s">%s</a>' % (key, E(rb))) if p[2].get("source_id") == "S1" else E(rb)
                return " ".join('<span class=rbi><a href="%s">%s</a>%s</span>' % (h(ref_path(i)), E(R.ref_label(i)), "," if j < len(rrefs) - 1 else "") for j, i in enumerate(rrefs))
            ps = x["pieces"]
            rbh = rb_html(ps[0]) if len(ps) == 1 else "".join('<span class=sub>%s</span>%s' % (
                "k = " + format(p[0], ",") if p[0] == p[1] else "k = %s to %s" % (format(p[0], ","), format(p[1], ",")), rb_html(p)) for p in ps)
            if x["sha"]:
                arr += '<span class=sub>%s</span>' % E(array_by_text(R, x["row"]))
            cf = x["cert"]
            if cf and x["sha"]:
                arr += '<span class=sub>family: <a href="%s">%s</a></span>' % (h("cphf/t%d/q%d/" % (cf["t"], cf["q"])), E(cf["family"]))
            elif cf:
                arr = '<a href="%s">%s</a><span class=sub>family on file</span>%s' % (
                    h("cphf/t%d/q%d/" % (cf["t"], cf["q"])), E(cf["family"]), ('<span class=sub>%s</span>' % E(array_by_text(R, x["cert_row"]))) if R.credit_of(x["cert_row"]) else "")
            trs.append('<tr id="k%d" class="%s" data-f="%s"><td class=n>%s</td><td class="n big">%s</td><td class=n>%s</td><td class=n>%s</td><td>%s</td>'
                       '<td class=rb>%s</td><td>%s%s</td><td class=a>%s</td></tr>' % (
                           x["k1"], "closed" if x["closed"] else "", " ".join(["all"] + (["arr"] if (x["sha"] or x["cert"] or x["ccert"]) else []) + (["ver"] if x["verified"] else []) + (["opt"] if x["opt_from"] is not None else [])), kr, format(x["N"], ","), lbt,
                           gpt, status, rbh,
                           con_h, ('<span class=sub>builds on %s</span>' % bo) if bo else "", arr))
        body = ('<div class=pageh><div class=in><div><p class=crumb><a href="%s">Table</a> / t=%d v=%d</p><h1>t=%d v=%d</h1>'
                '<p>Strength %d covering arrays on %d symbols. The smallest known number of rows N for every k up to %s, with the proven lower bound beside it.</p>%s</div>'
                '<div class=btns><a href="%s">JSON</a><a href="%s">CSV</a><a class=d href="https://doi.org/%s">Cite</a></div></div></div>'
                '<div class=stats><div><b class=num>%d</b><span>sizes</span></div><div><b class=num>%d</b><span>verified</span></div>'
                '<div><b class=num>%d</b><span>optimal</span></div><div><b class=num>%d</b><span><a href="%s">new since the first release</a></span></div>'
                '<div><b class=num>%s</b><span>last change</span></div></div>'
                '<main class=wrapw><div class=chips role=group aria-label="Show"><span class=l>Show</span><button type=button data-f=all aria-pressed=true>All sizes</button><button type=button data-f=arr aria-pressed=false>With an array on file</button><button type=button data-f=ver aria-pressed=false>Verified</button><button type=button data-f=opt aria-pressed=false>Optimal</button><span class=mute id=fn aria-live=polite></span></div>'
                '<table class=lg><thead><tr><th class=n>k</th><th class=n>best N</th><th class=n>lower bound</th><th class=n>gap</th><th>status</th>'
                '<th>first reached by</th><th>construction</th><th>array</th></tr></thead><tbody>%s</tbody></table></main>') % (
            h(""), t, v, t, v, t, v, format(c["kmax"], ","), rule_p(t, v, c, h), h("t%d/v%d.json" % (t, v)), h("t%d/v%d.csv" % (t, v)), DOI,
            len(c["rungs"]), c["nver"], c["nopt"], c["nnew"], h("learn/") + "#new-since-the-first-release", c["last"], "".join(trs))
        cld = json.dumps({"@context": "https://schema.org", "@type": "Dataset",
                          "name": "CAN(t, k, v) best known covering array sizes, t=%d v=%d" % (t, v),
                          "description": "Best known sizes N of covering arrays CA(N; %d, k, %d) for k up to %s, with proven lower bounds, credit, construction and the sha256 of each stored array." % (t, v, format(c["kmax"], ",")),
                          "url": BASE + path[:-len("index.html")], "identifier": "https://doi.org/" + DOI,
                          "license": "https://creativecommons.org/licenses/by/4.0/", "isAccessibleForFree": True,
                          "creator": {"@type": "Person", "name": "Christopher Smolen"}, "dateModified": c["last"][:10],
                          "isPartOf": {"@id": BASE + "#dataset"},
                          "distribution": [{"@type": "DataDownload", "encodingFormat": "application/json", "contentUrl": BASE + "t%d/v%d.json" % (t, v)},
                                           {"@type": "DataDownload", "encodingFormat": "text/csv", "contentUrl": BASE + "t%d/v%d.csv" % (t, v)}]}, ensure_ascii=False)
        site.page(path, "CAN(%d, k, %d): strength %d covering arrays on %d symbols" % (t, v, t, v),
                  "Best known covering array sizes CA(N; %d, k, %d) for k up to %s, with lower bounds, credit and arrays." % (t, v, format(c["kmax"], ",")), body, "Table", cld, KHASH)
        recs = [dict(k_from=x["k0"], k_to=x["k1"], N=x["N"], floor=x["floor"], floor_k_to=x["floor_k_to"], optimal_from=x["opt_from"],
                     status="optimal" if x["closed"] else ("verified" if x["verified"] else "cited"),
                     credit=x["credit"], construction=x["construction"], builds_on=x["builds_on"], array_sha256=x["sha"],
                     array_page=(BASE + array_path[x["sha"]]) if x["sha"] else "",
                     first_reached_by="; ".join(((("k = %d: " % p[0] if p[0] == p[1] else "k = %d to %d: " % (p[0], p[1])) if len(x["pieces"]) > 1 else "") + (p[3][0] or ", ".join(R.ref_label(i) for i in p[3][1]))) for p in x["pieces"]),
                     builds_on_names=[R.ref_label(i) for i in x["builds_on"]],
                     disputed=x["disputed"],
                     array_by=array_by_text(R, x["row"]) if x["sha"] else ((array_by_text(R, x["cert_row"]) if R.credit_of(x["cert_row"]) else "") if x["cert"] else ""),
                     family=x["cert"]["family"] if x["cert"] else "", family_page=("cphf/t%d/q%d/" % (x["cert"]["t"], x["cert"]["q"])) if x["cert"] else "") for x in c["rungs"]]
        site.write("t%d/v%d.json" % (t, v), json.dumps(dict(t=t, v=v, source=REPO_URL, doi=DOI, counting_rule="Colbourn rule, table/CONVENTIONS.md section 4: CITED and VERIFIED rows count", rungs=recs), ensure_ascii=False, indent=1), False)
        with open(os.path.join(a.out, "t%d/v%d.csv" % (t, v)), "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["t", "v", "k_from", "k_to", "N", "floor", "floor_k_to", "optimal_from", "status", "credit", "construction", "builds_on", "array_sha256", "first_reached_by"])
            for x in recs:
                w.writerow([t, v, x["k_from"], x["k_to"], x["N"], x["floor"] if x["floor"] is not None else "", x["floor_k_to"] if x["floor_k_to"] is not None else "", x["optimal_from"] or "", x["status"], x["credit"], x["construction"], ";".join(x["builds_on"]), x["array_sha256"], x["first_reached_by"]])

    for sha, path in array_path.items():
        m = man[sha]
        t, v, k, n = int(m["t"]), int(m["v"]), int(m["k"]), int(m["N"])
        rs = sorted(by_sha.get(sha, []), key=lambda r: r["source_id"] != "S8")
        r = rs[0] if rs else None
        d = path.count("/")
        h = lambda p, d=d: site.href(d, p)
        f = R.floor_at(t, v, k)
        lbk = lower_bounds.lower_bound(t, k, v)
        closed = lbk[0] == n
        con = pub(R.page_text(R.construction_of(r))) if r else ""
        bo = [i for i in ((r.get("builds_on") or "").split(";") if r else []) if i in R.REFS]
        fn = m["file"]
        loc = (m.get("location") or "").strip()
        if loc.startswith("http") and m.get("member"):
            dl = loc.split("::")[0]
            dll = "Download the deposit archive"
        elif loc.startswith("http"):
            dl = loc.split("::")[0]
            dll = "Download " + fn
        elif sha in ext:
            dl = ext[sha].split("::")[0]
            dll = "Download from the deposit"
        else:
            dl = RAW + "table/arrays/" + fn
            dll = "Download " + fn
        preview = ""
        fp = os.path.join(tdir, "arrays", fn)
        if previewable(m) and os.path.exists(fp):
            lines = [l.rstrip("\n") for l in open(fp, encoding="utf-8")][:80]
            preview = "\n".join("%3d  %s" % (i + 1, l if len(l) < 160 else l[:158] + " …") for i, l in enumerate(lines))
            if n > 80:
                preview += "\n     %d more rows in the file" % (n - 80)
        refs = "".join('<li><a href="%s">%s</a>%s</li>' % (h(ref_path(i)), E(R.REFS[i]["reference"]),
                                                         ((' <a href="https://arxiv.org/abs/%s">%s</a>' % (R.REFS[i]["doi"][6:], R.REFS[i]["doi"])) if R.REFS[i]["doi"].lower().startswith("arxiv:") else (' <a href="https://doi.org/%s">doi:%s</a>' % (R.REFS[i]["doi"], R.REFS[i]["doi"]))) if R.REFS[i].get("doi") else "") for i in bo)
        tag = '<span class="tag opt">optimal</span>' if closed else '<span class="tag ver">verified</span>'
        rung = next((x for x in cells[(t, v)]["rungs"] if x["k0"] <= k <= x["k1"]), None) if (t, v) in cells else None
        if rung is None:
            stxt = "beyond the table's range for t=%d v=%d" % (t, v)
        elif n <= rung["N"]:
            stxt = "best known" if rung["sha"] == sha or n < rung["N"] else "ties best known"
        else:
            stxt = 'above best known (best is %s, <a href="%s">see the table row</a>)' % (format(rung["N"], ","), h(row_path(t, v, k)))
        stc[stxt.split(" (")[0]] += 1
        bb = array_by_text(R, r) if r else ""
        full = (pub(R.credit_of(r)) or source_name(r)) if r else ""
        if bb.startswith("built by "):
            by_dd = "<dt>built by</dt><dd>%s</dd>" % E(bb[9:]) + ("<dt>credit</dt><dd>%s</dd>" % E(full) if full != bb[9:] else "")
        else:
            by_dd = "<dt>%s</dt><dd>%s</dd>" % ("credit" if R.credit_of(r) else "from", E(full)) if r else ""
        fr_dd = ""
        cf = cert_of(r)
        if cf:
            fr_dd += '<dt>family</dt><dd><a href="%s">%s</a>, <a href="%s">certificate</a></dd>' % (h("cphf/t%d/q%d/" % (cf["t"], cf["q"])), E(cf["family"]), RAW + "table/certificates/" + cf["file"])
        if rung is not None and n == rung["N"]:
            rb, rrefs = next(p for p in rung["pieces"] if p[0] <= k <= p[1])[3]
            fr_dd += "<dt>size first reached by</dt><dd>%s</dd>" % (E(rb) if rb else " ".join('<span class=rbi><a href="%s">%s</a>%s</span>' % (h(ref_path(i)), E(R.ref_label(i)), "," if j < len(rrefs) - 1 else "") for j, i in enumerate(rrefs)))
        body = ('<main class=wrapw><div class=arr><section><p class=crumb><a href="%s">Table</a> / <a href="%s">t=%d v=%d</a> / k = %s</p>'
                '<h1 style="font-size:2rem;margin:0 0 4px">%s %s</h1><p class=mute style="margin:0 0 20px">An array of %s rows and %s columns on %d symbols in which every %d columns show all %s combinations.</p>'
                '<dl>%s%s<dt>entered</dt><dd>%s</dd><dt>construction</dt><dd>%s</dd><dt>lower bound</dt><dd>%s</dd>'
                '<dt>verify stamp</dt><dd>%s</dd><dt>status</dt><dd>%s</dd></dl>%s</section>'
                '<aside><a class=dlb href="%s">%s</a><div class=dls><a href="%s">Table row</a><a href="%s">Verify it</a></div>'
                '<div class=sha>sha256 %s</div>%s</aside></div>%s</main>') % (
            h(""), h(cell_path(t, v)), t, v, format(k, ","), ca(n, t, k, v), tag, format(n, ","), format(k, ","), v, t, format(v ** t, ","),
            by_dd, fr_dd, r["entered"] if r else "", E(con), (format(f[4], ",") + ", " + E(pub(f[6]))) if f else format(lbk[0], ","),
            E(m["verify_stamp"]), stxt, ('<h2>Builds on</h2><ol>%s</ol>' % refs) if refs else "",
            dl, E(dll), h(row_path(t, v, k)), "#check", sha,
            ('<h2 style="font-size:.75rem;letter-spacing:.06em;text-transform:uppercase;color:var(--mute);margin:24px 0 8px">The array</h2><div class=grid tabindex=0 role=region aria-label="The array, first rows">%s</div>' % E(preview)) if preview else "",
            ('<section class=chk id=check><div><h2>Verify this array</h2><p>Download the array and the checker <a href="%sca_verify.py">ca_verify.py</a>, which needs only Python. '
             'It looks at every set of %d columns and confirms each one shows all %s combinations of the %d symbols.</p></div>'
             '<div><div class=code>%spython3 ca_verify.py %s %d %d</div><p class=mute>A correct array prints <span class=mono>VERIFIED: CA(N=%d; t=%d, k=%d, v=%d)</span>. '
             'Anything missing is listed by column and value. For large arrays the faster C checker <a href="%sca_verify.c">ca_verify.c</a> gives the same answer.</p></div></section>') % (
                RAW, t, format(v ** t, ","), v, ("unzip %s %s\n" % (E(os.path.basename(loc.split("::")[0])), E(m["member"]))) if m.get("member") else ("gunzip %s\n" % E(fn)) if fn.endswith(".gz") else "", E(m["member"] if m.get("member") else fn[:-3] if fn.endswith(".gz") else fn), t, v, n, t, k, v, RAW))
        site.page(path + "index.html", "%s covering array" % ca(n, t, k, v),
                  "A verified covering array %s: %s rows, strength %d, %s columns, %d symbols, with credit, construction and download." % (ca(n, t, k, v), format(n, ","), t, format(k, ","), v),
                  body, "Table")

    use = collections.defaultdict(list)
    for r in rows:
        for i in (r.get("builds_on") or "").split(";"):
            if i in R.REFS:
                use[i].append(r)
    flo = collections.defaultdict(list)
    for r in lb:
        for i in set(filter(None, r[7].split(";"))):
            if i in R.REFS:
                flo[i].append(r)
    cards = []
    for rid in sorted(R.REFS, key=lambda i: (-len(use[i]), -len(flo[i]))):
        ref = R.REFS[rid]["reference"]
        au, rest = split_ref(ref)
        ti = title_of(rest)
        j = rest[len(ti) + 2:]
        jh = "Web page" if rid.startswith("web-") else "In proceedings" if j.startswith(("in:", "Proc. ")) else (re.split(r"\s\(\d{4}\)|:\d|\s\d+(?:-\d+)?(?:\(\d+\))?(?=[\s,(]|$)", j)[0].rstrip(" ,") or j)
        u = use[rid]
        na = len({x["array_sha256"] for x in u if x["array_sha256"]})
        cap = ", ".join(s for s in [("%s %s" % (format(len(u), ","), "entry" if len(u) == 1 else "entries")) if u else "", ("%d array%s" % (na, "" if na == 1 else "s")) if na else "",
                                     ("%d lower bound%s" % (len(flo[rid]), "" if len(flo[rid]) == 1 else "s")) if flo[rid] else ""] if s)
        doi = R.REFS[rid].get("doi") or ""
        cards.append(('<div data-s="%s">' % E(fold(" ".join([ti, au, jh, year_of(ref, rid), doi, rid])).lower(), quote=True)) + '<a class=pg href="%s"><div class=j>%s</div><h2>%s</h2><p class=au>%s</p><div class=ln>%s</div><div class=y><span>%s</span><span style="overflow:hidden;text-overflow:ellipsis">%s</span></div></a><p class=cap>%s</p></div>' % (
            site.href(1, ref_path(rid)), E(jh), E(ti), E(au), "<i></i>" * 7, year_of(ref, rid), E(("doi:" + doi) if doi and not doi.lower().startswith("arxiv") else doi), cap))
        d = 2
        h = lambda p, d=d: site.href(d, p)
        prs = []
        for x in sorted(u, key=lambda r: (r["t"], r["v"], r["k"], r["N"]))[:400]:
            link = h(array_path[x["array_sha256"]]) if x["array_sha256"] in array_path else h(row_path(x["t"], x["v"], x["k"]))
            c2 = pub(R.page_text(R.construction_of(x) or ""))
            prs.append('<div class=pr><span><a href="%s">%s</a><span class=k>%s</span></span><span>%s</span><span class=c>%s</span></div>' % (
                link, ca(x["N"], x["t"], x["k"], x["v"]), TIER_WORD.get(x["tier"], x["tier"].lower()), E(c2), E(row_who(R, x))))
        more = ('<p class=lede>%s more entries build on it. The full list is in the table data.</p>' % format(len(u) - 400, ",")) if len(u) > 400 else ""
        fls = "".join('<div class=fl>CAN(%d, %s, %d) &ge; %s</div>' % (r[0], (format(r[2], ",") if r[2] == r[3] else "%s to %s" % (format(r[2], ","), format(r[3], ","))), r[1], format(r[4], ",")) for r in flo[rid])
        body = ('<main class=wrapw><div class=paper><p class=crumb><a href="%s">Library</a> / %s</p><div class=hd><div class=j>%s</div><h1>%s</h1><p class=au>%s</p>'
                '<div class=btns>%s</div></div>%s%s</div></main>') % (
            h("library/"), E(R.ref_label(rid)), E(j), E(ti), E(au),
            ('<a class=d href="https://doi.org/%s">doi:%s</a>' % (doi, doi)) if doi and not doi.lower().startswith("arxiv") else ('<a class=d href="https://arxiv.org/abs/%s">%s</a>' % (doi.split(":", 1)[-1], doi) if doi else ""),
            ('<h2>In the table</h2><p class=lede>%s %s build on this paper.</p>%s%s' % (format(len(u), ","), "row" if len(u) == 1 else "rows", "".join(prs), more)) if u else "",
            ('<h2>Lower bounds that cite it</h2>%s' % fls) if fls else "")
        site.page(ref_path(rid) + "index.html", "%s, %s" % (ti, R.ref_label(rid)), "%s. What in the covering array table builds on it." % ref[:150], body, "Library")
    lib = ('<div class="pageh serifh"><div class=in><div><h1>Library</h1><p>Every paper the table rests on. Most entries link the paper, and the rest give the full reference. Each says what in the table is built on it. Open one to see those arrays and lower bounds.</p></div>'
           '<div class=lfind><label for=lq class=vh>Search the library</label><svg width="17" height="17" viewBox="0 0 17 17" aria-hidden="true"><circle cx="7" cy="7" r="5.5" fill="none" stroke="currentColor" stroke-width="1.9"/><path d="M11.2 11.2l4.3 4.3" stroke="currentColor" stroke-width="1.9" stroke-linecap="round"/></svg>'
           '<input id=lq type=search autocomplete=off spellcheck=false placeholder="Title, author, journal or year"><span id=ln class=mute aria-live=polite>%d papers</span></div></div></div>'
           '<main class=wrapw><div class=lib id=lib>%s</div><p class=lnone id=lnone hidden>No paper in the library matches that. If one is missing, <a href="mailto:%s">tell us</a>.</p></main>') % (len(cards), "".join(cards), CONTACT)
    lscript = ("<script>(function(){var q=document.getElementById('lq'),cs=document.querySelectorAll('#lib>div'),n=document.getElementById('ln'),z=document.getElementById('lnone'),all=cs.length;"
               "function f(){var t=q.value.normalize('NFD').replace(/[\\u0300-\\u036f]/g,'').toLowerCase().split(/\\s+/).filter(Boolean),k=0;"
               "cs.forEach(function(c){var s=c.getAttribute('data-s'),on=t.every(function(w){return s.indexOf(w)>=0});c.hidden=!on;if(on)k++});"
               "n.textContent=t.length?k+' of '+all+' papers':all+' papers';z.hidden=k>0}q.addEventListener('input',f)})()</script>")
    site.page("library/index.html", "Library: the papers behind the covering array table", "Every paper the covering array table rests on, with the arrays and lower bounds built on each.", lib, "Library", None, lscript)

    people = {}

    def person(key, shown):
        p = people.get(key)
        if p is None:
            p = people[key] = dict(key=key, names=set(), rows=[], held=[], papers=[], floors=set())
        p["names"].add(shown)
        return p

    for rid in R.REFS:
        au, _ = split_ref(R.REFS[rid]["reference"])
        for n in filter(None, (x.strip() for x in re.split(r", | and ", au))):
            p = person(person_key(*name_parts(n)), n)
            if rid not in p["papers"]:
                p["papers"].append(rid)
    by_sur = collections.defaultdict(set)

    def index_names():
        by_sur.clear()
        for k in people:
            by_sur[k[0]].add(k)

    def resolve(n):
        f = fold(n).lower()
        if len(by_sur.get(f, ())) == 1:
            return people[next(iter(by_sur[f]))]
        sur, given = name_parts(n)
        k = person_key(sur, given)
        if not given and len(by_sur.get(k[0], ())) == 1:
            return people[next(iter(by_sur[k[0]]))]
        p = person(k, n)
        by_sur[k[0]].add(k)
        return p

    index_names()
    credited = collections.defaultdict(list)
    roles = collections.defaultdict(dict)
    for r in rows:
        if r["tier"] not in ("VERIFIED", "CITED"):
            continue
        c = R.credit_of(r)
        if c:
            segs = segments(c)
            bset = {id(x) for x in builder_segs(segs)}
            for sg in segs:
                role = "built" if id(sg) in bset else "own" if sg["kind"] in ("size", "author", "plain", "method") else "used"
                for n in credit_names(sg["name"]):
                    p = resolve(n)
                    old = roles[id(p)].get(id(r))
                    if old is None or ("built", "own", "used").index(role) < ("built", "own", "used").index(old):
                        roles[id(p)][id(r)] = role
                    credited[id(p)].append(r)
        else:
            for n in source_people(r):
                p = resolve(n)
                roles[id(p)].setdefault(id(r), "built")
                credited[id(p)].append(r)
    for p in people.values():
        seen = set()
        p["rows"] = [r for r in credited.get(id(p), []) if not (id(r) in seen or seen.add(id(r)))]
        p["role"] = roles.get(id(p), {})
        p["kept"] = 0
    for src, n in KEEPERS.items():
        resolve(n)["kept"] = sum(1 for r in rows if r["source_id"] == src and r["tier"] == "VERIFIED")
    for c in cells.values():
        for x in c["rungs"]:
            got = {}
            for pc in x["pieces"]:
                w = pc[2]
                cr = R.credit_of(w)
                refs = [] if cr else reached_by(R, w)[1]
                ns = [n for sg in reach_segs(cr) for n in credit_names(sg["name"])] if cr else ([] if refs else source_people(w))
                for n in ns:
                    q = resolve(n)
                    got[id(q)] = q
                for q in people.values():
                    if any(rid in q["papers"] for rid in refs):
                        got[id(q)] = q
            for q in got.values():
                q["held"].append(x)
    for p in people.values():
        for rid in p["papers"]:
            p["floors"].update(id(r) for r in flo[rid])

    def shown_name(p):
        return max(p["names"], key=lambda n: (len(re.sub(r"[^A-Za-z]", "", name_parts(n)[1])), sum(1 for ch in n if ord(ch) > 127), len(n)))

    ppl = [p for p in people.values() if p["rows"] or p["papers"] or p["kept"]]
    for p in ppl:
        p["name"] = shown_name(p)
        p["sur"], p["given"] = name_parts(p["name"])
        p["ver"] = sum(1 for r in p["rows"] if r["tier"] == "VERIFIED" and p["role"].get(id(r)) == "built")
        p["cit"] = sum(1 for r in p["rows"] if p["role"].get(id(r)) == "own" or (r["tier"] == "CITED" and p["role"].get(id(r)) == "built"))
        p["used"] = sum(1 for r in p["rows"] if p["role"].get(id(r)) == "used")
        p["built"] = len({id(r) for rid in p["papers"] for r in use[rid]})
        p["cells"] = sorted({(x["row"]["t"], x["row"]["v"]) for x in p["held"]} | {(r["t"], r["v"]) for r in p["rows"]})
    ppl.sort(key=lambda p: (fold(p["sur"]).lower(), fold(p["given"]).lower()))
    slugs = collections.Counter(re.sub(r"[^a-z0-9]+", "-", fold(p["sur"]).lower()).strip("-") for p in ppl)
    for p in ppl:
        b = re.sub(r"[^a-z0-9]+", "-", fold(p["sur"]).lower()).strip("-")
        p["slug"] = b if slugs[b] == 1 else b + "-" + re.sub(r"[^a-z]", "", fold(p["given"]).lower())[:3]
        p["path"] = "contributors/%s/" % p["slug"]

    def plural(n, one, many=None):
        return "%s %s" % (format(n, ","), one if n == 1 else (many or one + "s"))

    def summary(p):
        return ", ".join(s for s in [plural(p["ver"], "array built", "arrays built") if p["ver"] else "",
                                     plural(p["kept"], "array from their collection", "arrays from their collection") if p["kept"] else "", plural(p["cit"], "credited size") if p["cit"] else "",
                                     plural(len(p["held"]), "best known size first reached", "best known sizes first reached") if p["held"] else "",
                                     plural(p["used"], "entry uses their work", "entries use their work") if p["used"] and not (p["ver"] or p["cit"] or p["papers"]) else "",
                                     plural(len(p["papers"]), "paper") if p["papers"] else "", plural(len(p["floors"]), "lower bound") if p["floors"] else ""] if s)

    def initials(p):
        w = [x for x in re.split(r"[\s.]+", p["name"]) if x[:1].isalpha()]
        return (w[0][0] + w[-1][0]).upper() if len(w) > 1 else w[0][0].upper()

    h1 = lambda q: site.href(1, q)
    letters = {}
    cards = []
    for p in ppl:
        L = fold(p["sur"])[0].upper()
        cards.append('<a class=pc href="%s" data-l="%s" data-n="%s"><i aria-hidden="true">%s</i><span><b>%s</b><span>%s</span></span></a>' % (
            h1(p["path"]), L, E(fold(p["name"]).lower()), initials(p), E(p["name"]), summary(p)))
        letters.setdefault(L, p)
    az = '<button type=button data-l="" aria-pressed="true">All</button>' + "".join(
        ('<button type=button data-l="%s" aria-pressed="false">%s</button>' % (L, L)) if L in letters else '<span aria-hidden="true">%s</span>' % L for L in "ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    body = ('<div class=pageh><div class=in><div><h1>Contributors</h1><p>Everyone whose arrays, constructions, papers or proofs the table rests on, with what each contributed. '
            'Built from the table\'s own credits and its library.</p>'
            '<p class=mute style="font-size:.9rem">How the counts are made, from each entry\'s credit. Arrays built: verified arrays whose credit names the person as builder, and two collections whose arrays carry no credit: the binary arrays of Torres-Jimenez and the CA Extender arrays of Torres-Jimenez, Acevedo-Juarez and Avila-George, both kept in the CAs package. Arrays from their collection: arrays the table took from a collection the person keeps (Aaron Dwyer\'s CA_Database), credited to their builders. '
            'Credited sizes: entries whose credit names their construction, method or result. Entries that use their work: their array or method was an ingredient or a tool. '
            'Best known sizes first reached: the people the credit of the first row to reach the size names for the size; when it names no one for the size, its builder; when it names no builder, the authors of its method or result. An entry with no credit counts for the authors of the papers it builds on, as on the table pages, and otherwise for the collections above.</p></div></div></div>'
            '<main class=wrapw><div class=pf><label for=pq class=vh>Find a contributor by name</label><input id=pq type=search placeholder="Find a name" autocomplete=off></div>'
            '<div class=az role=group aria-label="Show surnames starting with">%s</div><p class=pn id=pn aria-live=polite>%s</p>'
            '<div class=pp id=pp>%s</div></main>') % (az, plural(len(cards), "contributor"), "".join(cards))
    pscript = ("<script>(function(){var q=document.getElementById('pq'),n=document.getElementById('pn'),bs=document.querySelectorAll('.az button'),"
               "cs=document.querySelectorAll('#pp .pc'),L='';function run(){var t=q.value.trim().toLowerCase().normalize('NFKD').replace(/[\u0300-\u036f]/g,''),c=0;"
               "cs.forEach(function(e){var s=(!L||e.dataset.l===L)&&(!t||e.dataset.n.indexOf(t)>=0);e.hidden=!s;if(s)c++});"
               "n.textContent=(c===1?'1 contributor':c.toLocaleString('en-US')+' contributors')+(L?' with surnames starting '+L:'')+(t?' matching \u201c'+q.value.trim()+'\u201d':'')}"
               "bs.forEach(function(b){b.addEventListener('click',function(){L=b.dataset.l;bs.forEach(function(x){x.setAttribute('aria-pressed',x===b?'true':'false')});run()})});"
               "q.addEventListener('input',run)})()</script>")
    site.page("contributors/index.html", "Contributors to the covering array table", "Everyone whose arrays, published sizes, papers or proofs the covering array table rests on, with what each contributed.", body, "Contributors", script=pscript)

    for p in ppl:
        h = lambda q: site.href(2, q)
        st = [(p["ver"], "array built", "arrays built"), (p["kept"], "array from their collection", "arrays from their collection"), (p["cit"], "credited size", "credited sizes"), (p["used"], "entry uses their work", "entries use their work"), (len(p["held"]), "best known size first reached", "best known sizes first reached"),
              (len(p["papers"]), "paper in the library", "papers in the library"), (p["built"], "entry builds on their papers", "entries build on their papers"),
              (len(p["floors"]), "lower bound from their papers", "lower bounds from their papers")]
        stats = "".join('<div><b class=num>%s</b><span>%s</span></div>' % (format(n, ","), one if n == 1 else many) for n, one, many in st if n)
        held = collections.Counter((x["row"]["t"], x["row"]["v"]) for x in p["held"])
        left = ""
        if held:
            left += '<h2>Best known sizes first reached</h2><ul class=cnt>%s</ul>' % "".join(
                '<li><a href="%s">t=%d v=%d</a><span class=num>%s</span></li>' % (h(cell_path(t, v)), t, v, plural(n, "size")) for (t, v), n in sorted(held.items()))
        if p["rows"]:
            rs = sorted(p["rows"], key=lambda r: (r["entered"], r["t"], r["v"], r["k"]), reverse=True)
            items = "".join('<li><span class=d>%s</span><a href="%s">%s</a><span class="tag %s">%s</span></li>' % (
                r["entered"], h(array_path[r["array_sha256"]]) if r["array_sha256"] in array_path else h(row_path(r["t"], r["v"], r["k"])),
                ca(r["N"], r["t"], r["k"], r["v"]), "ver" if r["tier"] == "VERIFIED" else "dis" if r["tier"] == "DISPUTED" else "lit", TIER_WORD.get(r["tier"], r["tier"].lower())) for r in rs[:15])
            more = ('<p class=mute>%s more in the <a href="%s">table data</a>.</p>' % (format(len(rs) - 15, ","), RAW + "table/ca_table.csv")) if len(rs) > 15 else ""
            left += '<h2>Latest entries</h2><ul class=ent>%s</ul>%s' % (items, more)
        right = ""
        if p["papers"]:
            pl = []
            for rid in sorted(p["papers"], key=lambda i: (-len(use[i]), -len(flo[i]), year_of(R.REFS[i]["reference"], i))):
                au, rest = split_ref(R.REFS[rid]["reference"])
                what = ", ".join(s for s in [plural(len(use[rid]), "entry builds", "entries build") + " on it" if use[rid] else "",
                                             plural(len(flo[rid]), "lower bound") if flo[rid] else ""] if s)
                pl.append('<li><a href="%s">%s</a><span>%s%s</span></li>' % (h(ref_path(rid)), E(title_of(rest)), year_of(R.REFS[rid]["reference"], rid), (", " + what) if what else ""))
            right += '<h2>Papers in the library</h2><ul class=pap>%s</ul>' % "".join(pl)
        if not left and not right:
            continue
        lede = []
        if p["rows"]:
            lede.append("Credited on %s in the table" % plural(len(p["rows"]), "entry", "entries"))
        if p["papers"]:
            lede.append(("author of " if lede else "Author of ") + plural(len(p["papers"]), "paper") + " in the library")
        pbody = ('<div class=pageh><div class=in><div class=ph><i aria-hidden="true">%s</i><div><p class=crumb><a href="%s">Contributors</a> / %s</p><h1>%s</h1><p>%s.</p></div></div></div></div>'
                 '<div class=stats>%s</div><main class=wrapw><div class=two3><div>%s</div><div>%s</div></div></main>') % (
            initials(p), h("contributors/"), E(p["sur"]), E(p["name"]), " and ".join(lede), stats, left, right)
        site.page(p["path"] + "index.html", "%s: contributor to the covering array table" % p["name"],
                  "%s in the covering array table: %s." % (p["name"], summary(p) or "credited entries"), pbody, "Contributors")

    about = ('<div class=pageh><div class=in><div><h1>About</h1><p>Covering Array Tools is an open table of the best known covering arrays: every size, the proof of its lower bound, who built it, and the checked array to download.</p></div></div></div>'
             '<main class=wrapw><div class=ab>'
             '<section><h2>Who keeps it</h2><p>Kept by Christopher Smolen (<a href="https://orcid.org/0009-0002-9537-7961">ORCID</a>), first released on %s. It starts from Charles J. Colbourn\'s covering array tables as of November 2024, '
             'preserved in Ulrike Groemping\'s <a href="https://github.com/ugroempi/CAs">CAs R package</a>, and adds every array submitted and checked here and published bounds from the literature.</p></section>'
             '<section><h2>How arrays are checked</h2><p>Every array is checked before it is entered: every set of t columns must show every combination of symbols. A size marked verified has an array checked exactly. '
             'An array whose file is in the pull request and is too large for the exact check in the time the public check has enters as screened, checked on random column windows, and counts only once its exact check passes. '
             'Arrays kept in public deposits and covering perfect hash family certificates are checked exactly after the merge, in parts that together cover every set of columns once when they are large; one too large even for that enters as screened. A size marked cited is traceable to a dated table or a publication, with no array checked here yet.</p></section>'
             '<section><h2>How it changes</h2><p>Anyone can submit an array, a published size or a correction to a credit. The checks run in public on GitHub, and the site rebuilds itself after every change. '
             'The literature is checked every month, starting November 2026. Each submission is listed on <a href="%s">Updates</a>.</p></section>'
             '<section><h2>Licence and citation</h2><p>The data compiled here is <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a> and the code is MIT, except r/cafast and r/countkernel, which follow code of the CAs package closely and are GPL (&gt;= 3). Data from other sources keeps its own terms, and each row names its source. '
             'Cite the table with <a href="https://doi.org/%s">doi:%s</a>, and cite the authors of the rows you use.</p></section>'
             '<section><h2>Contact</h2><p><a href="mailto:%s">%s</a> for corrections, missing papers or anything else. A problem with a row can also be raised as a <a href="%s/issues">GitHub issue</a>. The site counts page views, downloads and searches with <a href="https://www.goatcounter.com/">GoatCounter</a>, which sets no cookies and keeps nothing about who you are.</p></section>'
             '<section><h2>Credit</h2><p>Arrays come from many builders and papers. Each size names who first reached it and who built the array on file, which are not always the same, and <a href="%s">Contributors</a> gathers everyone named, with what each contributed.</p></section>'
             '</div></main>') % (datetime.date.fromisoformat(SNAPSHOT_DATE).strftime("%-d %B %Y"), site.href(1, "changelog/"), DOI, DOI, CONTACT, CONTACT, REPO_URL, site.href(1, "contributors/"))
    site.page("about/index.html", "About Covering Array Tools", "Who keeps the covering array table, how arrays are checked, how it changes, and how to cite it.", about, "About")

    lab2id = {R.ref_label(i): i for i in R.REFS}

    def rl(lab):
        return ('<a href="%s">%s</a>' % (site.href(1, ref_path(lab2id[lab])), E(lab))) if lab in lab2id else E(lab)

    def colbourn_key():
        return [("Power CTq^s", "The power construction of %s. A hash family is made from the Bush orthogonal array over q symbols with strength s, so it has q^s columns, and each of its rows is replaced by a small covering array. Power CT11^3 reaches 1,331 columns." % rl("Colbourn and Torres-Jimenez 2010")),
                ("T followed by a number", "Levels removed from one row of that hash family: T7 removes seven. Each T after the first acts on another row. A row with fewer levels needs a smaller covering array, so the result has fewer rows and fewer columns."),
                ("c", "The small covering array put in for a row has constant rows, rows with one symbol throughout, and the construction uses them to save rows. Gr\u00f6mping reads the c this way, and so does the size law worked out for this table: read so, all 38 rows with a c come out at the size Colbourn gives."),
                ("+1, +2", "That many columns added to the hash family, so its rows have q plus that many levels. All 191 rows with a plus sign come out at the size Colbourn gives."),
                ("S followed by a number", "That many rows of the hash family each lose one level. Most S entries are on q^3, where the levels removed are planes through one point. All 50 rows with an S come out at the size Colbourn gives. Gr\u00f6mping reached the same meaning, the spike of Lemma 3.6 of %s, and has built it into powerCA in her %s (<a href=\"https://github.com/ugroempi/CAs/issues/23\">issue 23</a>)." % (rl("Colbourn and Torres-Jimenez 2010"), '<a href="https://github.com/ugroempi/CAs">CAs package</a>')),
                ("Arc", "Arc(a) on q^2: a rows of the hash family each lose one level, the levels removed being lines that meet pairwise, as in an arc of the plane over q. 501 of the 563 rows with an Arc come out at the size Colbourn gives. The other 62 have an Arc on every row followed by a T, which the law cannot yet express. In Arc(a):x twos,y ones, x rows lose two levels and y rows lose one; what the a means there is not known."),
                ("Power N-CT", "The same construction with a hash family whose number of rows no published theory gives. That number was solved from the table instead: one whole number for each of 39 settings of strength, levels and q gives 2,033 of the 2,093 N-CT rows exactly, and one more or one fewer fits none of them. For 32 of the 39 settings a hash family of that size was found and checked exactly, a set of directions of the plane over q. For 4, exhaustive search shows no such set exists, and 3 are still open."),
                ("Where these readings come from", "The readings of c, +, S, Arc and the N-CT row counts were worked out for this table by Christopher Smolen from the recorded sizes, and every one is checked against all the power entries; the method and counts are in the %s. They explain the sizes. No array has yet been built here from the S or Arc readings and checked, so these entries stay cited as Colbourn gives them." % ('<a href="%s/blob/main/r/livingtable/README.md">ca-tools living table notes</a>' % REPO_URL)),
                ("Power CZ", "The power construction of %s, which uses quilted arrays in place of covering arrays." % rl("Colbourn and Zhou 2012")),
                ("Derive from strength t + 1", "Take an array of strength one higher, keep the rows with one symbol in one column, and delete that column. The result has strength one lower and at most one v-th of the rows, by choosing the symbol that appears least."),
                ("Add a factor", "Adds a column to a known array at the cost of more rows."),
                ("Author codes", "A code in parentheses names who found the array or hash family: " + ", ".join("%s is %s" % (E(c), rl(l)) for c, l in (
                    ("TJ-RT", "Torres-Jimenez and Rodriguez-Tello 2012"), ("TJ-AG-I", "Torres-Jimenez et al. 2017"), ("LCDST", "Lobb et al. 2012"), ("CKRS", "Colbourn et al. 2010"),
                    ("CCL", "Cohen et al. 2008"), ("Nurmela", "Nurmela 2004"), ("Zekaoui", "Zekaoui 2006"))) +
                 ". Younis is presumably %s, as Gr\u00f6mping writes. TJ-AG is Torres-Jimenez and Avila-George: Gr\u00f6mping gives their 2016 work, and the rows here link the closest paper in the library, %s. "
                 "Other codes, such as CL, CLS, WCS, TJ-IM, TJ-RC, C and TATA, are kept as Colbourn wrote them. Their rows link the paper of the construction they use where it is known; the TATA row names none." % (rl("Younis and Zamli 2011"), rl("Torres-Jimenez et al. 2018")))]

    import lexicon
    fams, pats = lexicon.load()
    famd = {f["family"]: f for f in fams}
    famcache = {}

    def fam_of(r):
        txt = r.get("construction") or ""
        if txt not in famcache:
            famcache[txt] = lexicon.family(txt, pats) or "other"
        return famcache[txt] or "other"

    M = {f["family"]: dict(f=f, head=[], first=[], rows=0, ver=0, refs=collections.Counter()) for f in fams}
    for r in rows:
        if r["tier"] not in ("VERIFIED", "CITED"):
            continue
        m = M[fam_of(r)]
        m["rows"] += 1
        if r["tier"] == "VERIFIED" and r["array_sha256"] in array_path:
            m["ver"] += 1
        for i in (r.get("builds_on") or "").split(";"):
            if i in R.REFS:
                m["refs"][i] += 1
    for c in cells.values():
        for x in c["rungs"]:
            M[fam_of(x["row"])]["head"].append(x)
            M[fam_of(x["first"])]["first"].append(x)
    KIND = [("direct", "Direct constructions", "Arrays written down from an algebraic or combinatorial object."),
            ("recursive", "Built from smaller arrays", "Arrays made by combining, extending or cutting down arrays already known."),
            ("search", "Computer search", "Arrays found by a search program."),
            ("data", "Collections", "Published sets of arrays, credited to their collection when the method of each array is not recorded."),
            ("", "Other", "Rows with a name and no description.")]
    mlist = [m for m in M.values() if m["rows"]]
    for m in mlist:
        fid = m["f"]["family"]
        m["title"] = METHOD_TITLES.get(fid, fid)
        m["slug"] = "-".join(re.sub(r"[^a-z0-9]+", " ", fold(m["title"]).lower().replace("'s", "")).split())
        m["path"] = "methods/%s/" % m["slug"]
        m["opt"] = sum(1 for x in m["head"] if x["opt_from"] is not None)
        m["cells"] = collections.Counter((x["row"]["t"], x["row"]["v"]) for x in m["head"])
        m["fcells"] = collections.Counter((x["row"]["t"], x["row"]["v"]) for x in m["first"])

    def mline(m):
        return ", ".join(s for s in [plural(len(m["first"]), "size first reached", "sizes first reached") if m["first"] else "",
                                     plural(len(m["head"]), "best known size", "best known sizes") if m["head"] else "",
                                     plural(m["ver"], "array on file", "arrays on file") if m["ver"] else ""] if s) or plural(m["rows"], "entry", "entries")

    GSLUG = {"direct": "direct-constructions", "recursive": "built-from-smaller-arrays", "search": "computer-search", "data": "collections"}
    tiles = []
    cert_n = len({c["file"] for c in certs.values()})
    if cert_n:
        tiles.append('<a class=mopt href="%s"><b>Covering perfect hash families</b><p>Families on file, each checked, and the arrays they give.</p><div class=ft><span class=ct>%s</span><span class=go>Open &rarr;</span></div></a>' % (
            site.href(1, "cphf/"), plural(cert_n, "family", "families")))
    other = [m for m in mlist if m["f"]["kind"] not in GSLUG]
    for kid, kname, kdesc in KIND:
        ms = sorted((m for m in mlist if m["f"]["kind"] == kid), key=lambda m: (-len(m["first"]), -len(m["head"]), -m["rows"], m["title"]))
        if not ms or kid not in GSLUG:
            continue
        gp = "methods/%s/" % GSLUG[kid]
        tiles.append('<a class=mopt href="%s"><b>%s</b><p>%s</p><div class=ft><span class=ct>%s</span><span class=go>Open &rarr;</span></div></a>' % (
            site.href(1, gp), E(kname), E(kdesc), plural(len(ms), "method", "methods")))
        grows = "".join('<tr><td><a href="%s">%s</a><span>%s</span></td><td class=n data-l="first reached">%s</td><td class=n data-l="best known">%s</td><td class=n data-l="arrays">%s</td></tr>' % (
            site.href(2, m["path"]), E(m["title"]), E(m["f"]["meaning"]), format(len(m["first"]), ","), format(len(m["head"]), ","), format(m["ver"], ","))
            for m in ms)
        gbody = ('<div class=pageh><div class=in><div><p class=crumb><a href="%s">Methods</a> / %s</p><h1>%s</h1><p>%s %s.</p></div></div></div>'
                 '<main class=wrapw><div class=gmw><table class=gm><thead><tr><th>method</th><th class=n>sizes first reached</th><th class=n>best known sizes</th><th class=n>arrays on file</th></tr></thead><tbody>%s</tbody></table></div></main>') % (
            site.href(2, "methods/"), E(kname), E(kname), E(kdesc), plural(len(ms), "method", "methods"), grows)
        site.page(gp + "index.html", "%s: covering array methods" % kname, "%s %s." % (kdesc, plural(len(ms), "method", "methods")), gbody, "Methods")
    body = ('<div class=pageh><div class=in><div><h1>Methods</h1><p>Every way the sizes in the table were made. Choose a kind of method to see each one, the papers it rests on and where it gives a best known size.</p></div></div></div>'
            '<main class=wrapw><nav class=mopts aria-label="Kinds of method">%s</nav>%s<p class=mute style="margin-top:26px;font-size:.88rem">Each entry is placed in a method by its construction text, using the list in <a href="%s">table/lexicon.csv</a>. Corrections are welcome by issue or email.</p></main>') % (
        "".join(tiles), "".join('<p class=mute style="margin-top:22px;font-size:.88rem">%s: <a href="%s">%s</a>, %s.</p>' % (
            "Entries with a name and no description", site.href(1, m["path"]), E(m["title"]), plural(m["rows"], "entry", "entries")) for m in other),
        REPO_URL + "/blob/main/table/lexicon.csv")
    site.page("methods/index.html", "Methods: how the covering arrays in the table are made", "Every construction behind the best known covering array sizes, grouped by kind, with its papers and where it is used.", body, "Methods")

    for m in mlist:
        h = lambda q: site.href(2, q)
        kname = next(n for k, n, _ in KIND if k == m["f"]["kind"])
        st = [(len(m["first"]), "size first reached", "sizes first reached"), (len(m["head"]), "best known size", "best known sizes"),
              (m["ver"], "array on file", "arrays on file"), (m["opt"], "optimal size", "optimal sizes"), (len(m["cells"] | m["fcells"]), "cell", "cells")]
        stats = "".join('<div><b class=num>%s</b><span>%s</span></div>' % (format(n, ","), one if n == 1 else many) for n, one, many in st if n)
        refs = "".join('<li><a href="%s">%s</a><span>%s</span></li>' % (h(ref_path(i)), E(R.ref_label(i)), plural(n, "entry builds", "entries build") + " on it")
                       for i, n in m["refs"].most_common(8))
        keys = sorted(set(m["cells"]) | set(m["fcells"]))
        trs = "".join('<tr><td><a href="%s">t=%d v=%d</a></td><td class=n>%s</td><td class=n>%s</td></tr>' % (
            h(cell_path(t, v)), t, v, format(m["fcells"][(t, v)], ",") if m["fcells"][(t, v)] else "", format(m["cells"][(t, v)], ",") if m["cells"][(t, v)] else "")
            for t, v in keys)
        cas = ('<p class=mute>In the CAs R package this is %s.</p>' % E(m["f"]["cas_label"])) if m["f"]["cas_label"] else ""
        if m["f"]["family"] in ("cphfCA", "scphfCA"):
            cas += '<p><a href="%s">The covering perfect hash families on file</a></p>' % h("cphf/")
        kcrumb = ('<a href="%s">%s</a>' % (h("methods/%s/" % GSLUG[m["f"]["kind"]]), E(kname))) if m["f"]["kind"] in GSLUG else E(kname)
        pbody = ('<div class=pageh><div class=in><div><p class=crumb><a href="%s">Methods</a> / %s</p><h1>%s</h1><p>%s</p>%s</div></div></div>'
                 '<div class=stats>%s</div><main class=wrapw><div class=two3><div><h2>Where it gives a best known size</h2>%s</div><div>%s</div></div></main>') % (
            h("methods/"), kcrumb, E(m["title"]), E(m["f"]["meaning"]), cas, stats,
            ('<table class=mt><thead><tr><th>cell</th><th class=n>sizes first reached</th><th class=n>best known sizes</th></tr></thead><tbody>%s</tbody></table>' % trs) if trs else '<p class=mute>No best known size in the table uses it at present.</p>',
            ('<h2>Papers it rests on</h2><ul class=pap>%s</ul>' % refs) if refs else '<h2>Papers it rests on</h2><p class=mute>No paper is linked to these entries yet.</p>')
        site.page(m["path"] + "index.html", "%s: covering array method" % m["title"], "%s. %s" % (m["title"], m["f"]["meaning"]), pbody, "Methods")

    cph = []
    cfile = os.path.join(tdir, "certificates", "CERTIFICATES.csv")
    if os.path.exists(cfile):
        by_arr = {}
        by_fam = {}
        for r in rows:
            if r["tier"] == "VERIFIED":
                if r["array_sha256"]:
                    by_arr.setdefault(r["array_sha256"], r)
                if r.get("family_sha256"):
                    by_fam.setdefault(r["family_sha256"], r)
        seenf = {}
        for x in csv.DictReader(open(cfile, newline="", encoding="utf-8")):
            if x["file"] in seenf:
                seenf[x["file"]]["checks"].append(x["check"].split(":")[0])
                continue
            m = re.match(r"CPHF\((\d+); (\d+), (\d+), (\d+)\)(.*)", x["family"])
            if not m:
                continue
            n, k, q, t = map(int, m.groups()[:4])
            r = by_arr.get(x["array_sha256"]) or by_fam.get(x["family_sha256"])
            N = int(x["N"])
            rung = next((y for y in cells[(t, q)]["rungs"] if y["k0"] <= k <= y["k1"]), None) if (t, q) in cells else None
            cph.append(dict(n=n, k=k, q=q, t=t, N=N, extra=m.group(5).strip(" ,"), file=x["file"], exp=x["expansion"], checks=[x["check"].split(":")[0]], row=r,
                            best=bool(rung and rung["N"] == N), credit=row_who(R, r) if r else ""))
            seenf[x["file"]] = cph[-1]
    cgroups = collections.defaultdict(list)
    for x in cph:
        cgroups[(x["t"], x["q"])].append(x)
    for g in cgroups.values():
        for x in g:
            x["top"] = not any(y is not x and y["n"] <= x["n"] and y["k"] >= x["k"] and (y["n"], -y["k"]) < (x["n"], -x["k"]) for y in g)
    if cph:
        qs = sorted({x["q"] for x in cph})
        ts = sorted({x["t"] for x in cph})
        h1 = lambda p: site.href(1, p)
        head = "".join('<th scope=col>q=%d</th>' % q for q in qs)
        body_rows = []
        for t in ts:
            tds = []
            for q in qs:
                g = cgroups.get((t, q))
                if g:
                    tds.append('<td><a class=ct href="%s"><b>%d</b><span>%s</span><span>%s</span></a></td>' % (
                        h1("cphf/t%d/q%d/" % (t, q)), len(g), "family" if len(g) == 1 else "families",
                        (lambda a, b: "n = %d" % a if a == b else "n %d to %d" % (a, b))(min(x["n"] for x in g), max(x["n"] for x in g))))
                else:
                    tds.append("<td></td>")
            body_rows.append('<tr><th scope=row>t=%d</th>%s</tr>' % (t, "".join(tds)))
        cbody = ('<div class=pageh><div class=in><div><h1>Covering perfect hash families</h1><p>A covering perfect hash family CPHF(n; k, q, t) is an n by k array of vectors over the field with q elements, '
                 'chosen so that for every t columns some row has t independent vectors in them. Covering perfect hash families were introduced by '
                 '<a href="%s">Sherwood, Martirosyan and Colbourn 2006</a>. Each one gives a covering array CA(n(q^t - 1) + 1; t, k, q). A Sherwood family (SCPHF), a covering perfect hash family of a restricted kind, gives CA(n(q^t - q) + q; t, k, q). '
                 '%s of the best known sizes in the table come from covering perfect hash families.</p></div></div></div>'
                 '<div class=stats><div><b class=num>%s</b><span>families on file</span></div><div><b class=num>%s</b><span>give a best known size</span></div>'
                 '<div><b class=num>%s</b><span>strengths</span></div><div><b class=num>%s</b><span>field sizes</span></div></div>'
                 '<main class=wrapw><p>Every family here is stored as a certificate, checked exactly over all sets of t columns, and expands to an array in the table. '
                 'Sizes cited from Colbourn\'s tables come without their families, so only those sizes are in the table.</p>'
                 '<div class=ctw><table class=ctg><thead><tr><th scope=col>t \\ q</th>%s</tr></thead><tbody>%s</tbody></table></div>'
                 '<p class=mute style="font-size:.88rem">All families: <a href="%s">table/certificates/CERTIFICATES.csv</a>. How to rebuild and recheck them: <a href="%s">tools/cphf/README.md</a>.</p></main>') % (
            h1(ref_path("cphf-smc2006")) if "cphf-smc2006" in R.REFS else REPO_URL, format(sum(len(M[f]["head"]) for f in ("cphfCA", "scphfCA") if f in M), ","), format(len(cph), ","), format(sum(1 for x in cph if x["best"]), ","), len(ts), len(qs), head, "".join(body_rows),
            REPO_URL + "/blob/main/table/certificates/CERTIFICATES.csv", REPO_URL + "/blob/main/tools/cphf/README.md")
        site.page("cphf/index.html", "Covering perfect hash families: certificates on file", "Covering perfect hash families CPHF(n; k, q, t) behind the covering array table, each checked exactly, with the array it gives.", cbody, "Methods")
        for (t, q), g in sorted(cgroups.items()):
            h = lambda p: site.href(3, p)
            trs = []
            for x in sorted(g, key=lambda x: (x["n"], -x["k"])):
                ca_h = ca(x["N"], t, x["k"], q)
                if x["row"] is not None and x["row"]["array_sha256"] in array_path:
                    ca_l = '<a href="%s">%s</a>' % (h(array_path[x["row"]["array_sha256"]]), ca_h)
                else:
                    ca_l = '<a href="%s">%s</a>' % (h(row_path(t, q, x["k"])), ca_h)
                tags = ('<span class="tag opt">best on file</span>' if x["top"] else "") + (' <span class="tag ver">best known size</span>' if x["best"] else "")
                trs.append('<tr><td class=n>%d</td><td class=n>%s</td><td class=a>%s</td><td>%s</td><td>%s</td><td><a href="%s">%s</a><span class=sub>%s</span></td></tr>' % (
                    x["n"], format(x["k"], ","), ca_l, tags, E(x["credit"]), RAW + "table/certificates/" + x["file"], E(x["file"]),
                    E(("Sherwood form, " if "affine" in x["exp"] else "") + "; ".join(x["checks"]))))
            pb = ('<div class=pageh><div class=in><div><p class=crumb><a href="%s">CPHFs</a> / t=%d q=%d</p><h1>CPHF(n; k, %d, %d)</h1>'
                  '<p>Covering perfect hash families of strength %d over the field with %d elements on file, smallest n first. Best on file marks the families no other here beats: none has n as small with k as large.</p></div></div></div>'
                  '<main class=wrapw><table class=lg><thead><tr><th class=n>n</th><th class=n>k</th><th>gives</th><th>status</th><th>built by</th><th>certificate</th></tr></thead><tbody>%s</tbody></table></main>') % (
                h("cphf/"), t, q, q, t, t, q, "".join(trs))
            site.page("cphf/t%d/q%d/index.html" % (t, q), "CPHF(n; k, %d, %d): covering perfect hash families" % (q, t),
                      "Covering perfect hash families of strength %d over GF(%d) on file, with the covering arrays they give." % (t, q), pb, "Methods")

    board_rows = ["000", "011", "101", "110"]
    btns = "".join('<button class="%s" data-r=%d data-c=%d aria-label="row %d, column %d: %s">%s</button>' % ("o" if ch == "1" else "z", i, j, i + 1, j + 1, ch, ch) for i, r in enumerate(board_rows) for j, ch in enumerate(r))
    gl = [("t, strength", "How many columns at a time must show every combination."), ("v, symbols", "How many values a cell can take. On and off is v = 2."),
          ("k, columns", "How many factors, settings or parameters the array covers."), ("N, rows", "How many rows, or tests, the array uses. Smaller is better."),
          ("Size", "A stretch of k where the smallest known N stays the same. Each cell of the table is a staircase of sizes, one per row of its table."),
          ("Lower bound", "A proven bound on N: no array can have fewer rows. Sometimes called the floor."),
          ("First reached by", "Who first reached that size, from the earliest entry, paper or table that reaches it. Rows from Colbourn's tables name the papers they build on, or Colbourn's tables with his label when they name none. When an earlier entry reached the same N over part of a size's range of k, each part is named with its own range."),
          ("Array", "The array file kept for that size and who built it. It can be a later array of the same size: the builder of the file is not always the first to reach the size."),
          ("Verified", "An explicit array of that size was checked here exactly: every set of t columns, or, for a construction certificate, every step of the recipe that builds it. The size says where the array is: a file to download, a public deposit, or the family or construction certificate that builds it. Six verified best known sizes rest on arrays checked in August 2026 whose files are no longer stored, because their only public source is the CAs package; their rows keep the size, the hash and the check."),
          ("Cited", "The size is traceable to a dated table or a publication. No array for it has been checked here yet."),
          ("Optimal", "The best known size equals the proven lower bound, so nothing smaller exists, and the size is verified. A cited size at its lower bound is shown as cited."),
          ("Disputed", "A cited size whose recorded construction, built and checked here, did not give a covering array at that size. The cited size stays as recorded and still counts; the dispute says what failed and how it was checked, not that the size cannot be reached."),
          ("Screened", "An array too large for the public exact check, checked on random column windows only. It is listed but does not count as best known until its exact check passes."),
          ("Failed, pending recheck", "Three rows of 23 August 2026, kept as history. Each was explained and replaced by a verified row at the true size."),
          ("Counting rule", "Best known sizes follow the table's Colbourn rule: cited and verified rows count; screened rows, disputed rows and sizes derived by rule do not. The frame file ca_frame.csv also counts proven derived sizes, so at some k it has a smaller value than the page."),
          ("New since the first release", "The table was first published on 23 August 2026, built from the 2024 snapshot of Colbourn's tables and the other sources it names. A size is new when every entry that sets it was entered after that date.")]
    learn = ('<main><div class=hero><div class=in><div><p class=crumb>Learn</p><h1 style="font-family:%s;font-weight:400">What is a covering array?</h1>'
             '<p style="font-family:%s;font-size:1.1rem;line-height:1.55">A grid of symbols, chosen so that any few columns, looked at together, show every possible combination somewhere in their rows.</p>'
             '<p style="font-family:%s;font-size:1.1rem;line-height:1.55;margin-top:10px">Here are three on and off switches. Every pair of switches is seen in all four combinations, 00, 01, 10 and 11, using only four rows instead of eight. '
             'That is a covering array of strength 2, written CA(4; 2, 3, 2).</p></div>'
             '<div><div class=board><div class=bg><span class=h>col 1</span><span class=h>col 2</span><span class=h>col 3</span>%s</div><div class=pairs id=pairs aria-live=polite></div></div>'
             '<p class=cap>Tap a cell to change it and watch a combination go missing.</p></div></div></div>'
             '<div class=prose><h2>Why they matter</h2><div class=two><div><p>Studies of real software failures found most were triggered by one or two settings, fewer by three or more, and nearly all by six or fewer (<a href="https://doi.org/10.1109/TSE.2004.24">Kuhn, Wallace and Gallo 2004</a>, and later NIST studies). Testing every combination of settings is out of reach. Ten on and off switches already give 1,024 cases.</p>'
             '<p>A covering array of strength 2 tests every pair of those ten switches in 6 rows. Strength 3 catches every triple. The smaller the array, the fewer tests to run, which is why the race for the smallest N has gone on for decades.</p></div>'
             '<div class=statc><div><b>1,024</b><span>tests for every combination of 10 switches</span></div><div><b>6</b><span>tests for every pair, CA(6; 2, 10, 2)</span></div></div></div>'
             '<h2>See it in the table</h2><div class=lv><div><b><a href="%s">t=2 v=2</a></b><span>on and off, every pair</span></div><div><b><a href="%s">t=3 v=2</a></b><span>on and off, every triple</span></div>'
             '<div><b><a href="%s">t=2 v=3</a></b><span>three values, every pair</span></div><div><b><a href="%s">t=3 v=3</a></b><span>three values, every triple</span></div></div>'
             '<h2>How to read the table</h2><dl class=gl>%s</dl>'
             '<h2 id=colbourn-labels tabindex=-1>Reading Colbourn\'s labels</h2><p>Sizes taken from Colbourn\'s tables keep his label for how each was made. The labels are short, and some parts of them have never been published. '
             'This key says what is known, and where it is not. The main written account is <a href="https://www1.bht-berlin.de/FB_II/reports/Report-2026-001.pdf">Gr\u00f6mping 2026</a>: Section 5.2 for the derive step and Appendices A and B for the author codes.</p><dl class=gl>%s</dl></div></main>') % (
        SERIF, SERIF, SERIF, btns, site.href(1, "t2/v2/"), site.href(1, "t3/v2/"), site.href(1, "t2/v3/"), site.href(1, "t3/v3/"),
        "".join('<div id="%s"><dt>%s</dt><dd>%s</dd></div>' % (re.sub(r"[^a-z0-9]+", "-", x.lower()).strip("-"), E(x), E(y)) for x, y in gl),
        "".join('<div><dt>%s</dt><dd>%s</dd></div>' % (E(x), y) for x, y in colbourn_key()))
    lscript = ("<script>function upd(){var b=[].slice.call(document.querySelectorAll('.bg button'));var g=[[],[],[],[]];b.forEach(function(x){g[+x.dataset.r][+x.dataset.c]=x.textContent});"
               "var out='';[[0,1],[0,2],[1,2]].forEach(function(p){var s={};g.forEach(function(r){s[r[p[0]]+r[p[1]]]=1});var seen=Object.keys(s).sort();"
               "var all=seen.length==4,miss=['00','01','10','11'].filter(function(z){return !s[z]});out+='<div><span>columns '+(p[0]+1)+' and '+(p[1]+1)+'</span><b>'+seen.join(' ')+'</b><span class='+(all?'ok':'miss')+'>'+(all?'all 4':'missing: '+miss.join(' '))+'</span></div>'});"
               "document.getElementById('pairs').innerHTML=out}"
               "document.querySelectorAll('.bg button').forEach(function(x){x.addEventListener('click',function(){x.textContent=x.textContent=='1'?'0':'1';x.className=x.textContent=='1'?'o':'z';x.setAttribute('aria-label','row '+(+x.dataset.r+1)+', column '+(+x.dataset.c+1)+': '+x.textContent);upd()})});upd();</script>")
    site.page("learn/index.html", "What is a covering array? Learn to read the table", "What a covering array is, why it matters for testing, and how to read the covering array table.", learn, "Learn", None, lscript)

    def ftile(fmt, name, url, what):
        return '<a class=ftl href="%s"><span class=fmt>%s</span><b>%s</b><span>%s</span></a>' % (url, fmt, name, what)
    forai = ('<div class=pageh><div class=in><div><h1>For AI agents</h1><p>Everything an agent needs to read the table, choose an open size, build an array, check it and submit it. A named person answers for every submission.</p></div>'
             '<div class=btns><a class=d href="%s">llms.txt</a></div></div></div>'
             '<main class=wrapw><div class=flow>'
             '<a class="fl4 f4" href="#data"><span class=no>1</span><b>Read the data</b><span>Plain CSV and JSON, rebuilt on every merge</span></a>'
             '<a class="fl4 f3" href="%stable/wanted.csv"><span class=no>2</span><b>Pick a target</b><span>wanted.csv lists every open size</span></a>'
             '<a class="fl4 f2" href="#check"><span class=no>3</span><b>Check locally</b><span>The same exact check the pull request runs</span></a>'
             '<a class="fl4 f1" href="%s"><span class=no>4</span><b>Submit</b><span>One folder in a pull request</span></a></div>'
             '<div class=grid2><div><p class=sech id=data style="margin-top:0">Data</p><div class=ft>%s%s%s%s%s%s</div></div>'
             '<div><p class=sech id=check style="margin-top:0">Check and submit</p>'
             '<div class=code tabindex=0 role=region aria-label="Commands to check and test a submission"><span class=c># check one array exactly</span>\npython3 ca_verify.py CA_33_3_6_3.txt 3 3\n<span class=c># run the pull request check locally</span>\npython3 tools/check_submission.py submissions/your-name</div>'
             '<div class=code tabindex=0 role=region aria-label="Layout of a submission folder"><span class=c># one new folder, nothing else changed</span>\nsubmissions/your-name/\n  claims.csv   t,v,k,N,file,source_detail,construction,builds_on,credit,notes\n  HOW.md       how the arrays were built\n  CA_33_3_6_3.txt</div>'
             '<p class=mute style="font-size:.88rem">Full guide: <a href="%s/blob/main/submissions/README.md">submissions/README.md</a></p></div></div>'
             '<p class=sech>Rules</p><div class=rules>'
             '<div><b>Checked or cited</b>A size enters as verified only with an array or a certificate the table can check. A size from a paper enters as cited, with credit to its authors.</div>'
             '<div><b>Say how</b>HOW.md is required, with the line <span class=mono>AI tools used: yes</span> or <span class=mono>no</span>. Naming the AI system is welcome.</div>'
             '<div><b>A person answers</b>A named person with an email and affiliation, never an AI alone.</div>'
             '<div><b>Credit the builder</b>Submit only arrays the named person built or may submit, and credit whoever actually built each one.</div>'
             '<div><b>Not your result</b>Sizes and arrays from the table belong to the authors their rows name. Never present them as new.</div>'
             '<div><b>Read the tiers</b>A cited size has no array here. A screened array is not yet proven. Optimal means the best known size equals its proven floor, with a checked array on file.</div>'
             '<div><b>Use the files</b>Read the CSV and JSON files above rather than the pages. They hold the same data and are updated on every merge.</div>'
             '<div><b>Withdrawn arrays</b>Never submitted or used as a start or ingredient. The check compares against them.</div>'
             '<div><b>Licence</b>Opening a pull request licenses the arrays under CC BY 4.0.</div></div>'
             '<div class=citebox id=cite><div><p class=sech style="margin:0 0 6px">Cite</p><h2>Any use of this data cites the DOI</h2>'
             '<p>When an agent or a paper uses sizes, arrays or lower bounds from this table, cite the table by its DOI and cite the authors of the rows used. Each row names its source.</p>'
             '<p style="margin-top:10px">The data compiled here is licensed <a href="https://creativecommons.org/licenses/by/4.0/">CC BY 4.0</a>, which requires this credit. '
             'Rows taken from other sources keep their own terms, and each row names its source. See <a href="%s/blob/main/LICENSE-DATA">LICENSE-DATA</a>.</p></div>'
             '<div><div class=code>C. Smolen, ca-tools: a maintained table of covering arrays,\ndoi:%s</div><a class=doil href="https://doi.org/%s">https://doi.org/%s</a></div></div></main>') % (
        site.href(1, "llms.txt"), RAW, site.href(1, "submit/"),
        ftile("CSV", "ca_table.csv", RAW + "table/ca_table.csv", "Every row, with tier, credit and construction"),
        ftile("CSV", "wanted.csv", RAW + "table/wanted.csv", "Open sizes: no_array, array_above_best, beat_best"),
        ftile("CSV", "lower_bounds.csv", RAW + "table/lower_bounds.csv", "Proven lower bounds with theorem and references"),
        ftile("CSV", "MANIFEST.csv", RAW + "table/MANIFEST.csv", "Every stored array: file name, t, v, k, N and sha256"),
        ftile("JSON CSV", "t3/v3.json", site.href(1, "t3/v3.json"), "Any one cell, same pattern for every t and v"),
        ftile("CSV", "references.csv", RAW + "table/references.csv", "The papers the table rests on"),
        REPO_URL, REPO_URL, DOI, DOI, DOI)
    site.page("for-ai/index.html", "For AI agents: read, check and submit covering arrays", "Data files, open targets, the local check and the submission format for agents working on the covering array table.", forai, "For AI")

    pri = sorted(csv.DictReader(open(os.path.join(tdir, "priority.csv"), newline="", encoding="utf-8")), key=lambda p: p["date"], reverse=True)
    bysub = collections.defaultdict(list)
    for r in rows:
        m = re.search(r"submission ([A-Za-z0-9._-]+)", r.get("notes") or "")
        if m:
            bysub[m.group(1)].append(r)
        else:
            m2 = re.search(r"from submissions/([A-Za-z0-9._-]+)", r.get("notes") or "")
            if m2:
                bysub[m2.group(1)].append(r)
    trs = []
    for p in pri:
        rs = bysub.get(p["slug"], [])
        new, tie, other = [], 0, 0
        for x in rs:
            n = x.get("notes") or ""
            mm = re.search(r"previous best (\d+)", n)
            if re.search(r";\s*equals table", n):
                tie += 1
            elif mm and x["N"] < int(mm.group(1)):
                new.append((x, int(mm.group(1))))
            else:
                other += 1
        parts = ['<a href="%s">t%d v%d k%s</a> <s>%s</s> &rarr; <b>%s</b>' % (
            site.href(1, row_path(x["t"], x["v"], x["k"])), x["t"], x["v"], format(x["k"], ","), format(old, ","), format(x["N"], ",")) for x, old in new[:3]]
        if len(new) > 3:
            parts.append('<span class=mute>and %d more</span>' % (len(new) - 3))
        if tie:
            parts.append('<span class=mute>%d tie%s</span>' % (tie, "" if tie == 1 else "s"))
        if other:
            parts.append('<span class=mute>%d entered</span>' % other)
        who = (R.credit_of(rs[0]) if rs else "") or p["slug"].split("-20")[0]
        ev = ('<a href="%s">pull request %s</a>' % (p["evidence"], p["evidence"].rsplit("/", 1)[-1])) if p["basis"] == "pull_request" else '<span class=mono>%s</span>' % E(p["evidence"])
        trs.append('<tr><td class=d>%s</td><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (p["date"][:10], E(who.split(" (")[0]), '<a href="%s/tree/main/submissions/%s">files</a>' % (REPO_URL, E(p["slug"])), "<br>".join(parts) or '<span class=mute>recorded</span>', ev))
    cl = ('<div class=pageh><div class=in><div><h1>Updates</h1><p>Every submission to the table, newest first, with who submitted it, when, and the sizes that fell.</p></div></div></div>'
          '<main class=wrapw><table class=cl><thead><tr><th>date</th><th>submitter</th><th>submission</th><th>sizes that fell</th><th>evidence</th></tr></thead><tbody>%s</tbody></table></main>') % "".join(trs)
    site.page("changelog/index.html", "Updates: records in the covering array table", "Every submission to the covering array table with submitter, date and the sizes that fell.", cl, "Updates")

    groups = [("Every combination must appear", "A covering array needs at least v<sup>t</sup> rows, one for each combination.", ["R0"]),
              ("Fixing a symbol", "Fix one column to one symbol and the rows left over form a smaller array, so the lower bound for strength t comes from the lower bound for t minus 1.", ["R2"]),
              ("Published exact values", "Sizes proven optimal in published work, by search or by proof.", ["R5"]),
              ("Kleitman and Spencer", "The classical bounds for binary arrays, exact at strength 2.", ["R3", "R7", "R8"]),
              ("Counting set systems", "Bounds from how many columns a given number of rows can support.", ["R10", "R16", "R17"]),
              ("Strength 2 above v squared", "Strength 2 arrays on v &ge; 4 symbols need at least v<sup>2</sup>+3 rows once k is past v+1.", ["R12"]),
              ("No orthogonal array of index one", "When no perfect array exists at a size, the lower bound rises above it.", ["R13", "R14", "R15"]),
              ("Binary strength 3 stretches", "Extra rows forced at the ends of stretches of binary strength 3.", ["R6"])]
    byrule = collections.defaultdict(list)
    for r in lb:
        byrule[r[5]].append(r)
    known = {x for _, _, rs in groups for x in rs}
    extra = sorted(set(byrule) - known)
    if extra:
        groups.append(("Other", "Further published bounds.", extra))
    rl = ""
    for name, desc, rs in groups:
        n = sum(len(byrule[x]) for x in rs)
        if not n:
            continue
        cnt = collections.Counter()
        for x in rs:
            for r in byrule[x]:
                for i in filter(None, r[7].split(";")):
                    if i in R.REFS:
                        cnt[i] += 1
        refs = ", ".join('<a href="%s">%s</a>' % (site.href(1, ref_path(i)), E(R.ref_label(i))) for i, _ in cnt.most_common(3))
        rl += '<div class=rule><div><h2>%s</h2><p>%s</p></div><span class=cnt><b>%s</b> lower bounds</span><span class=refs>%s</span></div>' % (
            name, desc, format(n, ","), '<span class=mute>a general step, applied to bounds from the other rules</span>' if rs == ["R2"] else (refs or '<span class=mute>definition</span>'))
    tot_r = sum(len(c["rungs"]) for c in cells.values())
    tot_o = sum(c["nopt"] for c in cells.values())
    bd = ('<div class=pageh><div class=in><div><h1>Lower bounds</h1><p>A lower bound is the fewest rows any covering array could possibly have, proven by a theorem. '
          'When the best known size reaches its lower bound, nothing smaller exists and the question is closed. The table marks such a size optimal once it is verified; a cited size at its bound stays marked cited. The gap between the two is how much room is left.</p></div>'
          '<div class=btns><a href="%stable/lower_bounds.csv">CSV</a></div></div></div>'
          '<div class=stats><div><b class=num>%s</b><span>lower bounds on record</span></div><div><b class=num>%s</b><span>optimal sizes</span></div>'
          '<div><b class=num>%s</b><span>sizes still open</span></div><div><b class=num>%d</b><span>kinds of proof</span></div></div>'
          '<main class=wrapw><p class=sech>How the lower bounds are proven</p>%s'
          '<p class=mute style="margin-top:22px;font-size:.88rem">Each size on a t and v page shows its lower bound and the gap to it. The full list of lower bounds is in the CSV.</p></main>') % (
        RAW, format(len(lb), ","), format(tot_o, ","), format(tot_r - tot_o, ","), sum(1 for g in groups if sum(len(byrule[x]) for x in g[2])), rl)
    site.page("bounds/index.html", "Lower bounds for covering array numbers", "Proven lower bounds on CAN(t, k, v) with the theorem and references for each.", bd, "Lower bounds")

    sub = ('<div class=pageh><div class=in><div><h1>Submit</h1><p>The table grows by submission. Every array is checked before it goes in, exactly or, when it is too large for the time the public check has, on random column windows until its exact check passes. Every entry is credited to the people who built it.</p></div></div></div>'
           '<main class=wrapw><div class=two2>'
           '<div class=card><span class=lab>Arrays</span><h2>I have arrays</h2><p class=lead>An array that ties or beats the best known size enters the table under your name.</p>'
           '<div class=step><span class=no>1</span><div><b>Describe them</b><span>Write t, v, k, N, how you built them and what they build on in claims.csv, and how they were built in HOW.md.</span></div></div>'
           '<div class=step><span class=no>2</span><div><b>Open a pull request</b><span>Add the folder on GitHub in your browser. No command line needed.</span></div></div>'
           '<div class=step><span class=no>3</span><div><b>The check runs</b><span>Every array is checked, and the report usually appears on the pull request within a few minutes.</span></div></div>'
           '<div class=cta><a href="%s/blob/main/submissions/README.md">Start a submission</a><span class=s>Large arrays go in a Zenodo deposit</span></div></div>'
           '<div class=card><span class=lab>Papers</span><h2>I published a size</h2><p class=lead>A size from a paper needs no array. It enters as a cited row with credit to its authors.</p>'
           '<div class=step><span class=no>1</span><div><b>Give the paper</b><span>The DOI or arXiv link, and the theorem or table the size comes from.</span></div></div>'
           '<div class=step><span class=no>2</span><div><b>List the sizes</b><span>As CA(N; t, k, v). The same form corrects a credit that is wrong.</span></div></div>'
           '<div class=step><span class=no>3</span><div><b>It is reviewed</b><span>The maintainer checks the paper and enters it, and the paper joins the library.</span></div></div>'
           '<div class=cta><a href="%s/issues/new?template=published-bound.md">Report a published size</a><span class=s>Opens a form on GitHub</span></div></div></div>'
           '<div class=strip><div><b>No GitHub account, or something else?</b><br><span class=mute>Write and it will be entered by hand.</span></div><a href="mailto:%s">%s</a></div></main>') % (REPO_URL, REPO_URL, CONTACT, CONTACT)
    site.page("submit/index.html", "Submit covering arrays or published sizes", "How to submit covering arrays, published sizes or credit corrections to the table.", sub, "Submit")


    nf = ('<main><div class=nf><div class=tumble>%s</div><h1>Not found</h1><p class=mute>This page fell out of the table. Try the <a href="/">grid</a> or the <a href="/library/">library</a>.</p></div></main>') % ("<i></i>" * 9)
    nf_root = "/" if not a.preview else site.href(0, "")
    nf_lib = "/library/" if not a.preview else site.href(0, "library/")
    site.page("404.html", "Page not found", "Page not found.", nf.replace('href="/"', 'href="%s"' % nf_root).replace('href="/library/"', 'href="%s"' % nf_lib), "")
    site.urls.remove("404.html")
    open(os.path.join(a.out, "assets", "search.js"), "w").write(SEARCH_JS)
    def nk(*parts):
        return re.sub(r"[^a-z0-9]+", " ", " ".join(str(p) for p in parts).lower()).strip()
    si = []
    for (t, v), c in sorted(cells.items()):
        si.append(["c", "t=%d v=%d" % (t, v), "%d sizes, k to %s, %d verified, %d optimal" % (len(c["rungs"]), format(c["kmax"], ","), c["nver"], c["nopt"]),
                   cell_path(t, v), nk("t%d v%d t %d v %d" % (t, v, t, v), "strength", t, v, "symbols", "can", t, v)])
    for sha, path in array_path.items():
        m = man[sha]
        t, v, k, n = int(m["t"]), int(m["v"]), int(m["k"]), int(m["N"])
        rs = sorted(by_sha.get(sha, []), key=lambda r: r["source_id"] != "S8")
        cr = row_who(R, rs[0]) if rs else ""
        con = pub(R.page_text(R.construction_of(rs[0]))) if rs else ""
        si.append(["a", ca(n, t, k, v), E(cr + ((" , " + con[:70]) if con else "")).replace(" , ", ", "), path,
                   nk("ca", n, t, k, v, "can", t, k, v, cr, con, "t%d v%d k%d" % (t, v, k))])
    for rid in R.REFS:
        ref = R.REFS[rid]["reference"]
        au, rest = split_ref(ref)
        si.append(["p", E(title_of(rest)), E(au + " " + year_of(ref, rid)), ref_path(rid), nk(ref, R.REFS[rid].get("doi", ""))])
    for (t, q), g in sorted(cgroups.items()):
        si.append(["m", "CPHF t=%d q=%d" % (t, q), plural(len(g), "family on file", "families on file"), "cphf/t%d/q%d/" % (t, q), nk("cphf", "CPHF(n; k, %d, %d)" % (q, t), "hash family")])
    for m in mlist:
        si.append(["m", E(m["title"]), mline(m), m["path"], nk(m["title"], m["f"]["meaning"], m["f"]["family"], m["f"]["cas_label"])])
    for p in ppl:
        si.append(["u", E(p["name"]), summary(p), p["path"], nk(p["name"], fold(p["name"]), " ".join(p["names"]), fold(" ".join(p["names"])))])
    open(os.path.join(a.out, "assets", "sindex.js"), "w").write("var SI=" + json.dumps(si, ensure_ascii=False, separators=(",", ":")) + ";")

    der = os.path.join(a.repo, "docs", "derived.html")
    if os.path.exists(der):
        open(os.path.join(a.out, "derived.html"), "w", encoding="utf-8").write(open(der, encoding="utf-8").read())
    llms = os.path.join(a.repo, "docs", "llms.txt")
    if os.path.exists(llms):
        open(os.path.join(a.out, "llms.txt"), "w").write(open(llms, encoding="utf-8").read())
    open(os.path.join(a.out, "robots.txt"), "w").write("User-agent: *\nAllow: /\nSitemap: %ssitemap.xml\n" % BASE)
    with open(os.path.join(a.out, "sitemap.xml"), "w") as f:
        f.write('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n')
        for u in sorted(site.urls):
            f.write("<url><loc>%s%s</loc><lastmod>%s</lastmod></url>\n" % (BASE, u, site.date))
        f.write("</urlset>\n")
    print("pages %d, cells %d, arrays %d, papers %d, commit %s, date %s" % (len(site.urls), len(cells), len(array_path), len(R.REFS), site.commit, site.date))
    print("array status: %s" % ", ".join("%s %d" % kv for kv in sorted(stc.items())))


if __name__ == "__main__":
    main()
