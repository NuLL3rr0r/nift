#include "IdentitySpelling.h"
#include <filesystem>
#include <iostream>
#include <random>
#include <vector>
#include <cassert>
namespace fs=std::filesystem;
uint64_t cases=0,accepted=0,fallback=0,older_accepts=0;
void test(const std::string&s) {
 ++cases;bool fast=niftid::canonical_relative(s);
#ifdef _WIN32
 if(!fast){++fallback;return;}
#endif
 fs::path p(s);
 bool original=!s.empty() && s.size()<=65536 && s.find('\0')==s.npos && s.front()!='/' && s.back()!='/' && !p.is_absolute() && p.lexically_normal().generic_string()==s;
 for(const auto&c:p)if(c=="..")original=false;
 if(original)++older_accepts;
 if(!fast){++fallback;return;}++accepted;
 assert(original);
#ifdef _WIN32
 const auto drive=fs::current_path().root_path().generic_string();
 const std::vector<std::string> roots={drive,drive+"ordinary",drive+"a b",drive+"one/../two",drive+"repeated//part"};
#else
 const std::vector<std::string> roots={"/", "/tmp/ordinary", "/tmp/a b/ü", "/tmp/one/../two", "/tmp/repeated//part"};
#endif
 for(const auto&name:roots) {
  fs::path root=fs::path(name).lexically_normal();fs::path full=root/p;
  assert(full.lexically_normal()==full);assert(full.lexically_relative(root).generic_string()==s);
  auto native=root.native();if(native.back()!=fs::path::value_type('/'))native+=fs::path::value_type('/');
#ifdef _WIN32
  for(unsigned char ch:s)native+=static_cast<wchar_t>(ch);
  assert(fs::path(native).lexically_normal()==full.lexically_normal());
#else
  native+=s;assert(native==full.native());
#endif
  auto slash=s.rfind('/');std::string parent=slash==s.npos?"":s.substr(0,slash);
  assert(full.parent_path()==(parent.empty()?root:(root/parent).lexically_normal()));
 }
}
void enumerate(std::string&s,int depth){test(s);if(!depth)return;for(char c:std::string("a./\\ \0",6)){s+=c;enumerate(s,depth-1);s.pop_back();}}
int main(){std::string s;enumerate(s,7);std::mt19937_64 gen(193731);
 std::vector<std::string> tokens={"a","b",".","..","","é","λ","x y","\t","\\","A",".hidden"};
 for(int i=0;i<200000;i++){std::string x;int count=1+gen()%12;for(int k=0;k<count;k++){if(k)x+='/';x+=tokens[gen()%tokens.size()];}if(gen()%10==0)x='/'+x;if(gen()%10==0)x+='/';test(x);}
 for(int i=0;i<100000;i++){std::string x;int count=gen()%150;for(int k=0;k<count;k++)x+=static_cast<char>(gen()%256);test(x);}
 for(size_t length:{size_t(1),size_t(255),size_t(256),size_t(4095),size_t(4096),size_t(65535),size_t(65536),size_t(65537)}) {test(std::string(length,'x'));test("a/"+std::string(length,'x'));test(std::string(length,'x')+"/..");test(std::string(length,'x')+"/.");}
 for(const auto&x:std::vector<std::string>{"",".","..","./a","a/.","a/../b","a//b","/a","a/","a\\b"," a b ","é/λ","a\tb","C:a","C:/a","CON","con.txt","COM1","COM0","LPT0","CONIN$","CONOUT$","CLOCK$","CON .txt","LPT9.x","foo.","foo ","a:b","a?b","//server/share/a"})test(x);
 std::cout<<"{\"cases\":"<<cases<<",\"accepted\":"<<accepted<<",\"fallback\":"<<fallback<<",\"legacy_eligible\":"<<older_accepts<<",\"root_bindings_per_accept\":5,\"failures\":0}\n";
}
