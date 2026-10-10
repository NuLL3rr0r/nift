#include "IdentityPublication.h"
#include "identity_status_reference.h"
#include <iostream>
#include <cassert>
#include <string>
namespace fs=std::filesystem;
static std::string hex(std::string_view bytes) {
    static constexpr char digits[]="0123456789abcdef";std::string out;
    for(unsigned char ch:bytes){out+=digits[ch>>4];out+=digits[ch&15];}return out;
}
static int run_probe(int argc,char** argv) {
    if(argc<3)return 64;
    const std::string command=argv[1];const fs::path root=fs::absolute(fs::u8path(argv[2])).lexically_normal();
    niftid::Catalogue catalogue;const bool loaded=catalogue.load(root);
    if(command=="publish") {
        std::vector<std::vector<std::string>> paths(1);
        for(int i=3;i<argc;++i)paths[0].push_back(argv[i]);
        const bool changed=niftid::publish(root,loaded?&catalogue:nullptr,paths);
        std::cout<<"{\"changed\":"<<(changed?"true":"false")<<"}\n";return 0;
    }
    if(command=="load") {
        if(!loaded){std::cout<<"{\"loaded\":false}\n";return 2;}
        std::cout<<"{\"loaded\":true,\"generation\":"<<catalogue.generation<<",\"total\":"<<catalogue.records.size()<<",\"keys\":[";
        for(size_t i=0;i<catalogue.records.size();++i){if(i)std::cout<<',';std::cout<<'"'<<hex(catalogue.key(static_cast<uint32_t>(i)))<<'"';}
        std::cout<<"]}\n";return 0;
    }
    if(command=="native") {
        for(int i=3;i<argc;++i) {
            const fs::path path=(root/fs::u8path(argv[i])).lexically_normal();
            const auto ordinary=legacy_dependency_status(path);
            const auto id=loaded?catalogue.find(argv[i]):niftid::invalid;
            const auto* prepared=id==niftid::invalid?path.c_str():catalogue.path(id);
            const auto native=filesystem::dependency_status_native(prepared);
            assert(ordinary.exists==native.exists&&ordinary.error==native.error);
            assert(ordinary.mtime.seconds==native.mtime.seconds&&ordinary.mtime.nanoseconds==native.mtime.nanoseconds);
            std::error_code error;auto status=fs::symlink_status(path,error);
            const auto leaf=filesystem::dependency_leaf_native(prepared);
            if(leaf==filesystem::NativeLeafState::Plain)assert(!error&&!fs::is_symlink(status));
            if(leaf==filesystem::NativeLeafState::Missing)assert(error==std::errc::no_such_file_or_directory||status.type()==fs::file_type::not_found);
            if(leaf==filesystem::NativeLeafState::Error)assert(error&&error!=std::errc::no_such_file_or_directory);
            if(leaf==filesystem::NativeLeafState::Symlink)assert(!error&&fs::is_symlink(status));
            // Reparse invokes the original safety helper at the actual call site.
        }
        std::cout<<"{\"native_observations\":true}\n";return 0;
    }
    return 64;
}

#ifdef _WIN32
// Native wide argv preserves Unicode project roots without depending on the
// host ANSI code page. Eligible catalogue keys are independently ASCII only.
int wmain(int argc,wchar_t** wide) {
    std::vector<std::string> strings;strings.reserve(argc);
    for(int i=0;i<argc;++i) {
        const int length=::WideCharToMultiByte(CP_UTF8,0,wide[i],-1,nullptr,0,nullptr,nullptr);
        if(length<=0)return 64;
        std::string text(static_cast<size_t>(length),'\0');
        if(!::WideCharToMultiByte(CP_UTF8,0,wide[i],-1,text.data(),length,nullptr,nullptr))return 64;
        text.pop_back();strings.push_back(std::move(text));
    }
    std::vector<char*> argv;for(auto& text:strings)argv.push_back(text.data());
    return run_probe(argc,argv.data());
}
#else
int main(int argc,char** argv) {return run_probe(argc,argv);}
#endif
