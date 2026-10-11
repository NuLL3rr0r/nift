a:=[];i:=0;while(i<100000){a.push(100000-i);i+=1};a=a.sort_by(x=>x);i=0;while(i<100000){if(a[i]!=i+1){throw error("order")};i+=1};print(a[0]);print(a[99999])
