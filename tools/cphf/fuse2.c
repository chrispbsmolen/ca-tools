/* fuse2.c - CKRS 2010 Lemma 3.1 with two rows: from a CA(N; t, k, v+1) read on stdin (canonical text), build a
 * CA(N-2; t, k, v) in memory:
 *   1. row Z := the first row; relabel each column by the transposition (Z[c] <-> v), so Z becomes all v; delete Z;
 *   2. row R := the next row; in every other row replace each v in column c by R[c] (by 0 where R[c] = v); delete R.
 * Prints N, k and the SHA-256 of the result in canonical form (0-based, single spaces, LF), and spot-checks it on S
 * random t-sets (every one of the v^t tuples must occur). Optional: write the result to OUT.
 * usage: fuse2 v t S seed [OUT] < expanded.txt          (v = the new number of symbols) */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
/* --- sha256 (public domain style) --- */
typedef struct{uint32_t s[8];uint64_t n;uint8_t b[64];int bl;}H;
static const uint32_t K[64]={0x428a2f98,0x71374491,0xb5c0fbcf,0xe9b5dba5,0x3956c25b,0x59f111f1,0x923f82a4,0xab1c5ed5,0xd807aa98,0x12835b01,0x243185be,0x550c7dc3,0x72be5d74,0x80deb1fe,0x9bdc06a7,0xc19bf174,0xe49b69c1,0xefbe4786,0x0fc19dc6,0x240ca1cc,0x2de92c6f,0x4a7484aa,0x5cb0a9dc,0x76f988da,0x983e5152,0xa831c66d,0xb00327c8,0xbf597fc7,0xc6e00bf3,0xd5a79147,0x06ca6351,0x14292967,0x27b70a85,0x2e1b2138,0x4d2c6dfc,0x53380d13,0x650a7354,0x766a0abb,0x81c2c92e,0x92722c85,0xa2bfe8a1,0xa81a664b,0xc24b8b70,0xc76c51a3,0xd192e819,0xd6990624,0xf40e3585,0x106aa070,0x19a4c116,0x1e376c08,0x2748774c,0x34b0bcb5,0x391c0cb3,0x4ed8aa4a,0x5b9cca4f,0x682e6ff3,0x748f82ee,0x78a5636f,0x84c87814,0x8cc70208,0x90befffa,0xa4506ceb,0xbef9a3f7,0xc67178f2};
#define R(x,n) (((x)>>(n))|((x)<<(32-(n))))
static void blk(H*h,const uint8_t*p){uint32_t w[64],a,b,c,d,e,f,g,hh;for(int i=0;i<16;i++)w[i]=(uint32_t)p[4*i]<<24|p[4*i+1]<<16|p[4*i+2]<<8|p[4*i+3];
 for(int i=16;i<64;i++){uint32_t s0=R(w[i-15],7)^R(w[i-15],18)^(w[i-15]>>3),s1=R(w[i-2],17)^R(w[i-2],19)^(w[i-2]>>10);w[i]=w[i-16]+s0+w[i-7]+s1;}
 a=h->s[0];b=h->s[1];c=h->s[2];d=h->s[3];e=h->s[4];f=h->s[5];g=h->s[6];hh=h->s[7];
 for(int i=0;i<64;i++){uint32_t S1=R(e,6)^R(e,11)^R(e,25),ch=(e&f)^(~e&g),t1=hh+S1+ch+K[i]+w[i],S0=R(a,2)^R(a,13)^R(a,22),mj=(a&b)^(a&c)^(b&c),t2=S0+mj;hh=g;g=f;f=e;e=d+t1;d=c;c=b;b=a;a=t1+t2;}
 h->s[0]+=a;h->s[1]+=b;h->s[2]+=c;h->s[3]+=d;h->s[4]+=e;h->s[5]+=f;h->s[6]+=g;h->s[7]+=hh;}
static void hinit(H*h){uint32_t i0[8]={0x6a09e667,0xbb67ae85,0x3c6ef372,0xa54ff53a,0x510e527f,0x9b05688c,0x1f83d9ab,0x5be0cd19};memcpy(h->s,i0,32);h->n=0;h->bl=0;}
static void hup(H*h,const uint8_t*p,size_t n){h->n+=n;while(n){int c=64-h->bl;if((size_t)c>n)c=n;memcpy(h->b+h->bl,p,c);h->bl+=c;p+=c;n-=c;if(h->bl==64){blk(h,h->b);h->bl=0;}}}
static void hfin(H*h,char*out){uint64_t bits=h->n*8;uint8_t z=0x80;hup(h,&z,1);z=0;while(h->bl!=56)hup(h,&z,1);uint8_t L[8];for(int i=0;i<8;i++)L[i]=bits>>(56-8*i);hup(h,L,8);for(int i=0;i<8;i++)sprintf(out+8*i,"%08x",h->s[i]);}
int main(int argc,char**argv){int v=atoi(argv[1]),t=atoi(argv[2]);long S=atol(argv[3]);srand48(atol(argv[4]));
 size_t cap=1<<20; uint8_t *A=malloc(cap); long n=0; int k=-1; uint8_t row[100000]; int col=0,val=-1,ch;
 uint8_t Z[100000],Rw[100000]; int stage=0;
 while((ch=getchar())!=EOF){ if(ch>='0'&&ch<='9'){val=(val<0?0:val*10)+(ch-'0');continue;}
   if(val>=0){row[col++]=(uint8_t)val;val=-1;}
   if(ch=='\n'&&col){ if(k<0)k=col; else if(col!=k){fprintf(stderr,"ragged row\n");return 2;}
     if(stage==0){memcpy(Z,row,k);stage=1;}
     else{ for(int c=0;c<k;c++){uint8_t x=row[c]; if(x==Z[c])x=(uint8_t)v; else if(x==v)x=Z[c]; row[c]=x;}   /* transposition Z[c] <-> v */
       if(stage==1){memcpy(Rw,row,k);stage=2;}
       else{ for(int c=0;c<k;c++) if(row[c]==v) row[c]= Rw[c]==v?0:Rw[c];
         if((size_t)(n+1)*k>cap){cap*=2;A=realloc(A,cap);} memcpy(A+(size_t)n*k,row,k); n++; } }
     col=0; } }
 /* check symbols, hash canonical form */
 H h; hinit(&h); char line[400000]; FILE*o=argc>5?fopen(argv[5],"w"):NULL;
 for(long r=0;r<n;r++){ int p=0; for(int c=0;c<k;c++){ if(A[(size_t)r*k+c]>=v){fprintf(stderr,"symbol %d left at row %ld\n",A[(size_t)r*k+c],r);return 2;} p+=sprintf(line+p,c?" %d":"%d",A[(size_t)r*k+c]);} line[p++]='\n'; hup(&h,(uint8_t*)line,p); if(o)fwrite(line,1,p,o);}
 if(o)fclose(o); char hex[65]; hfin(&h,hex);
 printf("CA(%ld; %d, %d, %d) sha256 %s\n",n,t,k,v,hex); fflush(stdout);
 long vt=1;for(int i=0;i<t;i++)vt*=v; uint8_t*seen=malloc(vt); long bad=0;
 for(long s=0;s<S;s++){int cs[16];for(int i=0;i<t;i++){int ok;do{cs[i]=(int)(drand48()*k);ok=1;for(int j=0;j<i;j++)if(cs[j]==cs[i])ok=0;}while(!ok);}
   memset(seen,0,vt);long cnt=0; for(long i=0;i<n&&cnt<vt;i++){long idx=0;for(int j=0;j<t;j++)idx=idx*v+A[(size_t)i*k+cs[j]];if(!seen[idx]){seen[idx]=1;cnt++;}}
   if(cnt<vt){bad++; if(bad<=5)fprintf(stderr,"uncovered set (%ld of %ld)\n",cnt,vt);} }
 printf("spot check: %ld random %d-sets, uncovered %ld\n",S,t,bad); return bad?1:0;}
