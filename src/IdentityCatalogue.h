#include "IdentitySpelling.h"
#pragma once
#include <filesystem>
#include <vector>
#include <string>
#include <string_view>
#include <memory>
#include <fstream>
#include <limits>
#include <chrono>
#include <iostream>
namespace niftid {
namespace fs=std::filesystem;
constexpr uint32_t invalid=UINT32_MAX;
inline uint64_t hash(std::string_view s){uint64_t h=14695981039346656037ull;for(unsigned char c:s){h^=c;h*=1099511628211ull;}return h;}
inline std::string read(const fs::path&p){std::ifstream f(p,std::ios::binary|std::ios::ate);if(!f)return {};auto n=f.tellg();if(n<=0||n>4*1024*1024)return {};std::string b(static_cast<size_t>(n),'\0');f.seekg(0);f.read(b.data(),b.size());return f?b:std::string{};}
struct Reader{std::string_view b;size_t p=0;bool ok=true;uint32_t u32(){if(p+4>b.size()){ok=false;return 0;}uint32_t x=0;for(int i=0;i<4;i++)x|=uint32_t(static_cast<unsigned char>(b[p++]))<<(8*i);return x;}uint64_t u64(){auto a=u32();return uint64_t(a)|(uint64_t(u32())<<32);}bool magic(std::string_view s){if(b.substr(p,s.size())!=s){ok=false;return false;}p+=s.size();return true;}};
struct Record{uint32_t off,len,parent,flags,native;};
struct Catalogue{
 fs::path root;std::string arena;std::basic_string<fs::path::value_type> native;std::vector<Record> records;std::vector<uint32_t> slots;std::vector<std::string> parent_keys;std::vector<fs::path> parent_paths;std::vector<uint32_t> parent_slots;uint64_t generation=0,manifest_hash=0;
 std::string_view key(uint32_t id)const{const auto&r=records[id];return {arena.data()+r.off,r.len};}
 const fs::path::value_type* path(uint32_t id)const{return native.data()+records[id].native;}
 uint32_t find(std::string_view k)const{if(k.empty()||slots.empty())return invalid;size_t pos=hash(k)&(slots.size()-1);for(size_t i=0;i<slots.size();i++,pos=(pos+1)&(slots.size()-1)){auto id=slots[pos];if(id==invalid)return invalid;if(key(id)==k)return id;}return invalid;}
 bool load(const fs::path&project){return load_manifest(project,read(project/".nift/identity-stage1/manifest.bin"));}
 bool load_manifest(const fs::path&project,const std::string&manifest){
  root=project.lexically_normal();
#ifdef _WIN32
  // Ordinary absolute drive roots only; UNC/extended/device roots stay legacy.
  const auto drive=root.root_name().native();
  if(!root.is_absolute()||drive.size()!=2||drive[1]!=L':'||
     !((drive[0]>=L'A'&&drive[0]<=L'Z')||(drive[0]>=L'a'&&drive[0]<=L'z')))return false;
#endif
  const auto directory=root/".nift/identity-stage1";const auto& m=manifest;Reader v{m};if(!v.magic(std::string_view("NIFTID1\0",8))||v.u32()!=1||v.u32()!=platform)return false;generation=v.u64();manifest_hash=hash(m);auto total=v.u32(), shards=v.u32();if(!v.ok||!generation||!total||total>1000000||!shards||shards>total||m.size()!=32+size_t(shards)*20)return false;
  records.reserve(total);arena.reserve(total*32);uint32_t next=0;
  for(uint32_t s=0;s<shards;s++){
   auto first=v.u32(),count=v.u32(),bytes=v.u32();auto checksum=v.u64();if(!v.ok||first!=next||!count||count>256||uint64_t(first)+count>total||bytes>4*1024*1024)return false;
   auto b=read(directory/("shard-"+std::to_string(generation)+"-"+std::to_string(s)+".bin"));if(b.size()!=bytes||hash(b)!=checksum)return false;Reader q{b};if(!q.magic(std::string_view("NIDSH1\0\0",8))||q.u32()!=first||q.u32()!=count)return false;auto length=q.u32();if(b.size()!=20+size_t(count)*16+length||uint64_t(arena.size())+length>UINT32_MAX)return false;
   auto base=static_cast<uint32_t>(arena.size());uint32_t off=0;
   for(uint32_t i=0;i<count;i++){Record r{q.u32(),q.u32(),q.u32(),q.u32(),0};if(!q.ok||r.off!=off||uint64_t(r.off)+r.len+1>length||r.len>65536||r.flags!=(first+i==0?1u:0u))return false;off+=r.len+1;r.off+=base;records.push_back(r);}if(off!=length)return false;arena.append(b.data()+q.p,length);next+=count;
  }
  if(!v.ok||next!=total||records[0].len!=0||records[0].parent!=invalid||arena[0]!=0)return false;
  size_t capacity=1;while(capacity<total*2)capacity*=2;slots.assign(capacity,invalid);
  for(uint32_t id=0;id<total;id++){
   const auto&r=records[id];auto k=key(id);if(arena[r.off+r.len]!=0||k.find('\0')!=std::string_view::npos)return false;
   if(id){if(!canonical_relative(k)||r.parent>=total)return false;}
   size_t pos=hash(k)&(capacity-1);while(slots[pos]!=invalid){if(key(slots[pos])==k)return false;pos=(pos+1)&(capacity-1);}slots[pos]=id;
  }
  auto prefix=root.native();size_t bytes=0;for(auto&r:records)bytes+=prefix.size()+1+r.len+1;if(bytes>UINT32_MAX)return false;native.reserve(bytes);
  for(uint32_t id=0;id<total;id++){
   auto&r=records[id];auto k=key(id);if(id){auto slash=k.rfind('/');auto parent=slash==k.npos?std::string_view{}:k.substr(0,slash);if(key(r.parent)!=parent)return false;}
   r.native=static_cast<uint32_t>(native.size());native+=prefix;if(id){if(native.back()!=fs::path::value_type('/'))native+=fs::path::value_type('/');
#ifdef _WIN32
    for(unsigned char ch:k)native+=static_cast<wchar_t>(ch);
#else
    native.append(k);
#endif
    }native+='\0';
  }
  parent_slots.assign(total,invalid);
  for(auto&r:records)if(r.parent!=invalid&&parent_slots[r.parent]==invalid){parent_slots[r.parent]=parent_keys.size();parent_paths.emplace_back(path(r.parent));parent_keys.emplace_back(parent_paths.back().generic_string());}
  return true;
 }
};
}
