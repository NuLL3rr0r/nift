#pragma once
#include "IdentityCatalogue.h"
#include "FileSystem.h"
#include <algorithm>
#include <cstdlib>
#include <set>
#include <unordered_map>
#include <cerrno>
#ifdef _WIN32
#include <windows.h>
#else
#include <fcntl.h>
#include <unistd.h>
#endif

namespace niftid {
namespace publication {
inline void u32(std::string& bytes, uint32_t value) {
    for(unsigned i=0;i<4;++i)bytes+=static_cast<char>(value>>(8*i));
}
inline void u64(std::string& bytes, uint64_t value) {
    u32(bytes,static_cast<uint32_t>(value));u32(bytes,static_cast<uint32_t>(value>>32));
}
inline bool checkpoint(const char* phase) {
#ifdef NIFT_TEST_IDENTITY_PUBLICATION
    const char* fail=std::getenv("NIFT_TEST_IDENTITY_FAIL");
    if(fail&&std::string_view(fail)==phase)return false;
    const char* interrupt=std::getenv("NIFT_TEST_IDENTITY_INTERRUPT");
    if(interrupt&&std::string_view(interrupt)==phase)std::_Exit(86);
#else
    (void)phase;
#endif
    return true;
}
// Exclusive new files. Never truncate a shard, even one left unpublished by a
// failed attempt. Flush before a manifest can reference the new generation.
inline bool write_new(const fs::path& path, std::string_view bytes) {
#ifdef _WIN32
    HANDLE file=::CreateFileW(path.c_str(),GENERIC_WRITE,FILE_SHARE_READ,nullptr,
                             CREATE_NEW,FILE_ATTRIBUTE_NORMAL,nullptr);
    if(file==INVALID_HANDLE_VALUE)return false;
    DWORD written=0;
    bool ok=bytes.size()<=MAXDWORD && ::WriteFile(file,bytes.data(),static_cast<DWORD>(bytes.size()),&written,nullptr)
        && written==bytes.size() && ::FlushFileBuffers(file);
    if(!::CloseHandle(file))ok=false;
    return ok;
#else
    int file=::open(path.c_str(),O_WRONLY|O_CREAT|O_EXCL
#ifdef O_NOFOLLOW
                    |O_NOFOLLOW
#endif
                    ,0666);
    if(file<0)return false;
    size_t offset=0;bool ok=true;
    while(offset<bytes.size()) {
        const auto written=::write(file,bytes.data()+offset,bytes.size()-offset);
        if(written<0&&errno==EINTR)continue;
        if(written<=0){ok=false;break;}
        offset+=static_cast<size_t>(written);
    }
    if(ok)ok=::fsync(file)==0;
    if(::close(file)!=0)ok=false;
    return ok;
#endif
}
inline bool sync_directory(const fs::path& path) {
#ifdef _WIN32
    // New files are FlushFileBuffers'd; manifest replacement uses the existing
    // MoveFileExW WRITE_THROUGH helper. Windows does not expose portable dir fsync.
    (void)path;return true;
#else
    const int directory=::open(path.c_str(),O_RDONLY
#ifdef O_DIRECTORY
                                |O_DIRECTORY
#endif
    );
    if(directory<0)return false;
    bool ok=::fsync(directory)==0;
    if(::close(directory)!=0)ok=false;
    return ok;
#endif
}
inline bool alias_immutable(const fs::path& source,const fs::path& destination) {
    std::error_code error;
    if(!fs::is_regular_file(fs::symlink_status(source,error))||error)return false;
    fs::create_hard_link(source,destination,error);
    if(!error)return true;
    // An optional cache may live on a filesystem without hard links. Copy into
    // an exclusive new file; old shard bytes and IDs remain unchanged.
    const auto bytes=read(source);
    return !bytes.empty()&&write_new(destination,bytes);
}
// Keep current and previous complete generations. An old reader whose files
// are retired while it is loading simply fails validation and uses E3B. Only
// regular files with exact Nift filenames and matching format magic are owned.
inline void retire_generations(const fs::path& directory,uint64_t current,uint64_t previous) noexcept {
    try {
        std::error_code error;
        for(const auto& entry:fs::directory_iterator(directory,error)) {
            if(error)break;
            if(!fs::is_regular_file(entry.symlink_status(error))||error){error.clear();continue;}
            const auto name=entry.path().filename().string();
            const bool shard=name.compare(0,6,"shard-")==0;
            const bool manifest=name.compare(0,9,"manifest-")==0;
            if(!shard&&!manifest)continue;
            size_t position=shard?6:9;const size_t begin=position;uint64_t generation=0;
            while(position<name.size()&&name[position]>='0'&&name[position]<='9') {
                const unsigned digit=static_cast<unsigned>(name[position++]-'0');
                if(generation>(UINT64_MAX-digit)/10){position=begin;break;}
                generation=generation*10+digit;
            }
            if(position==begin||!generation||generation==current||generation==previous)continue;
            if(shard) {
                if(position==name.size()||name[position++]!='-')continue;
                const size_t number=position;
                while(position<name.size()&&name[position]>='0'&&name[position]<='9')++position;
                if(position==number||name.substr(position)!=".bin")continue;
            } else if(name.substr(position)!=".bin"&&name.substr(position)!=".tmp")continue;
            std::ifstream file(entry.path(),std::ios::binary);char magic[8]{};file.read(magic,8);
            if(!file||std::string_view(magic,8)!=(shard?std::string_view("NIDSH1\0\0",8):std::string_view("NIFTID1\0",8)))continue;
            file.close();fs::remove(entry.path(),error);error.clear();
        }
    } catch (...) { /* Best-effort hygiene cannot change build success. */ }
}
inline fs::path shard_path(const fs::path& directory,uint64_t generation,size_t index) {
    return directory/("shard-"+std::to_string(generation)+"-"+std::to_string(index)+".bin");
}
}

// Called only by the build coordinator, after worker join, while the existing
// project ownership lock is held. The active catalogue remains read-only for
// its entire scan. Discovery vectors are per job; no hot-edge publication lock.
// Return true only when a new manifest was committed. Every failure is optional.
inline bool publish(const fs::path& root,const Catalogue* active,
                    const std::vector<std::vector<std::string>>& discoveries) noexcept {
    try {
        std::set<std::string> additions;
        for(const auto& paths:discoveries)for(const auto& key:paths) {
            if(!canonical_relative(key))continue;
            std::string_view component=key;
            while(!component.empty()) {
                if(active&&active->find(component)!=invalid)break;
                if(!additions.emplace(component).second)break;
                const auto slash=component.rfind('/');
                if(slash==component.npos)break;
                component=component.substr(0,slash);
                if(additions.size()>1000000)return false;
            }
        }
        if(additions.empty())return false; // Zero catalogue writes for known paths.
        const uint32_t old_total=active?static_cast<uint32_t>(active->records.size()):0;
        if(uint64_t(old_total)+additions.size()+(!active)>1000000)return false;
#ifdef _WIN32
        const auto drive=root.root_name().native();
        if(!root.is_absolute()||drive.size()!=2||drive[1]!=L':'||
           !((drive[0]>=L'A'&&drive[0]<=L'Z')||(drive[0]>=L'a'&&drive[0]<=L'z')))return false;
#endif
        const auto directory=root/".nift/identity-stage1";
        if(!filesystem::path_within(root,directory))return false;
        std::error_code error;
        fs::create_directories(directory,error);if(error)return false;
        const auto manifest_path=directory/"manifest.bin";
        const auto manifest_status=fs::symlink_status(manifest_path,error);
        if(!error && fs::is_symlink(manifest_status))return false;
        if(error && error!=std::errc::no_such_file_or_directory)return false;
        const auto previous=active?read(manifest_path):std::string{};
        // Protect against an external catalogue change after activation. Existing
        // project ownership excludes other coordinators, not outside editors.
        if(active) {
            Reader reader{previous};
            if(!reader.magic(std::string_view("NIFTID1\0",8))||reader.u32()!=1||reader.u32()!=platform||reader.u64()!=active->generation||hash(previous)!=active->manifest_hash)return false;
        }
        uint64_t generation=active?active->generation:0;
        // Generation filenames encode the manifest's single generation number.
        // Choose one with no stale/orphan files, then alias prior immutable shards.
        bool available=false;
        for(unsigned attempt=0;attempt<1024&&!available;++attempt) {
            if(generation==UINT64_MAX)return false;
            ++generation;available=true;
            // Directory enumeration avoids O(existing IDs) negative path probes.
            const auto prefix="shard-"+std::to_string(generation)+"-";
            for(const auto& entry:fs::directory_iterator(directory,error)) {
                const auto name=entry.path().filename().string();
                if(name.compare(0,prefix.size(),prefix)==0 ||
                   name=="manifest-"+std::to_string(generation)+".tmp" ||
                   name=="manifest-"+std::to_string(generation)+".bin") {available=false;break;}
            }
            if(error)return false;
        }
        if(!available)return false;
        std::string descriptors;
        uint32_t previous_shards=0;
        if(active) {
            Reader reader{previous};reader.p=28;previous_shards=reader.u32();
            descriptors=previous.substr(32);
            for(uint32_t index=0;index<previous_shards;++index)
                if(!publication::alias_immutable(publication::shard_path(directory,active->generation,index),
                                                 publication::shard_path(directory,generation,index)))return false;
        }
        if(!publication::checkpoint("aliases"))return false;
        std::unordered_map<std::string,uint32_t> ids;
        ids.reserve(additions.size()+1);
        uint32_t next=old_total;
        std::vector<std::string> keys;
        if(!active){ids.emplace("",0);keys.emplace_back();next=1;}
        for(const auto& key:additions){ids.emplace(key,next++);keys.push_back(key);}
        uint32_t first=old_total;
        size_t cursor=0;
        uint32_t shard_count=previous_shards;
        while(cursor<keys.size()) {
            std::string arena,rows;
            const auto begin=cursor;
            while(cursor<keys.size()&&cursor-begin<256) {
                const auto& key=keys[cursor];
                if(20+rows.size()+16+arena.size()+key.size()+1>4*1024*1024)break;
                uint32_t parent=invalid;
                if(!key.empty()) {
                    const auto slash=key.rfind('/');const auto parent_key=slash==key.npos?std::string{}:key.substr(0,slash);
                    if(parent_key.empty())parent=0;
                    else {auto found=ids.find(parent_key);parent=found==ids.end()?(active?active->find(parent_key):invalid):found->second;}
                    if(parent==invalid)return false;
                }
                publication::u32(rows,static_cast<uint32_t>(arena.size()));
                publication::u32(rows,static_cast<uint32_t>(key.size()));
                publication::u32(rows,parent);publication::u32(rows,key.empty()?1:0);
                arena+=key;arena+='\0';++cursor;
            }
            if(cursor==begin)return false;
            std::string shard("NIDSH1\0\0",8);
            const auto count=static_cast<uint32_t>(cursor-begin);
            publication::u32(shard,first);publication::u32(shard,count);publication::u32(shard,static_cast<uint32_t>(arena.size()));
            shard+=rows;shard+=arena;
            if(!publication::write_new(publication::shard_path(directory,generation,shard_count),shard))return false;
            publication::u32(descriptors,first);publication::u32(descriptors,count);
            publication::u32(descriptors,static_cast<uint32_t>(shard.size()));publication::u64(descriptors,hash(shard));
            first+=count;++shard_count;
        }
        if(!publication::sync_directory(directory)||!publication::checkpoint("shards"))return false;
        std::string manifest("NIFTID1\0",8);
        publication::u32(manifest,1);publication::u32(manifest,platform);publication::u64(manifest,generation);
        publication::u32(manifest,next);publication::u32(manifest,shard_count);manifest+=descriptors;
        if(manifest.size()>4*1024*1024)return false;
        Catalogue validated;
        if(!validated.load_manifest(root,manifest)||!publication::checkpoint("validated"))return false;
        if(active) {
            auto saved=directory/("manifest-"+std::to_string(active->generation)+".bin");
            if(!fs::exists(saved,error)) {
                if(error||!publication::alias_immutable(manifest_path,saved))return false;
            } else if(error||read(saved)!=previous)return false;
        }
        const auto temporary=directory/("manifest-"+std::to_string(generation)+".tmp");
        if(!publication::write_new(temporary,manifest)||!publication::sync_directory(directory)||!publication::checkpoint("manifest-ready"))return false;
        if(!filesystem::replace_file_atomic(temporary,manifest_path))return false;
        // Once switched, an fsync failure still leaves a validated cache; it
        // cannot alter consumer success. The previous manifest/shards remain.
        (void)publication::sync_directory(directory);
        (void)publication::checkpoint("committed");
        publication::retire_generations(directory,generation,active?active->generation:0);
        return true;
    } catch (...) { return false; }
}
}
