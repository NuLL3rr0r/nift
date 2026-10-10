#include <stdatomic.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <errno.h>
extern void *__libc_malloc(size_t);
extern void *__libc_calloc(size_t,size_t);
extern void *__libc_realloc(void*,size_t);
extern void *__libc_memalign(size_t,size_t);
extern void __libc_free(void*);
static _Atomic unsigned long long m,c,r,a,f,b;
void *malloc(size_t n){atomic_fetch_add(&m,1);atomic_fetch_add(&b,n);return __libc_malloc(n);}
void *calloc(size_t n,size_t s){atomic_fetch_add(&c,1);atomic_fetch_add(&b,n*s);return __libc_calloc(n,s);}
void *realloc(void *p,size_t n){atomic_fetch_add(&r,1);atomic_fetch_add(&b,n);return __libc_realloc(p,n);}
void free(void *p){atomic_fetch_add(&f,1);__libc_free(p);}
void *aligned_alloc(size_t align,size_t n){atomic_fetch_add(&a,1);atomic_fetch_add(&b,n);return __libc_memalign(align,n);}
int posix_memalign(void **p,size_t align,size_t n){if(align<sizeof(void*)||(align&(align-1)))return EINVAL;void *v=__libc_memalign(align,n);if(!v)return ENOMEM;atomic_fetch_add(&a,1);atomic_fetch_add(&b,n);*p=v;return 0;}
__attribute__((destructor)) static void done(void){const char *path=getenv("NIFT_ALLOC_FILE");if(!path)return;unsigned long long mm=m,cc=c,rr=r,aa=a,ff=f,bb=b;FILE *out=fopen(path,"w");if(out){fprintf(out,"{\"malloc\":%llu,\"calloc\":%llu,\"realloc\":%llu,\"aligned\":%llu,\"free\":%llu,\"requested_bytes\":%llu}\n",mm,cc,rr,aa,ff,bb);fclose(out);}}
