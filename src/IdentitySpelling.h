#pragma once
#include <string_view>
#include <initializer_list>
namespace niftid {
// Eligible POSIX relative spellings only. Unsupported spellings disable the
// optional catalogue; authoritative dependencies continue through legacy paths.
inline bool canonical_relative_posix(std::string_view key) {
    if(key.empty() || key.size()>65536)return false;
    size_t start=0;
    for(size_t i=0;i<=key.size();++i) {
        if(i<key.size() && key[i]=='\0')return false;
        if(i==key.size() || key[i]=='/') {
            const size_t length=i-start;
            if(!length || (length==1 && key[start]=='.') ||
                (length==2 && key[start]=='.' && key[start+1]=='.'))return false;
            start=i+1;
        }
    }
    return true;
}
}

namespace niftid {
// Deliberately narrower than POSIX. Keys stay byte/case exact; non-ASCII,
// backslashes, drive/root syntax, device names and Win32 aliases use legacy.
inline bool canonical_relative_windows(std::string_view key) {
    if (!canonical_relative_posix(key)) return false;
    size_t start = 0;
    for (size_t i = 0; i <= key.size(); ++i) {
        if (i < key.size()) {
            const unsigned char c = static_cast<unsigned char>(key[i]);
            if (c < 32 || c >= 127 || c == '\\' || c == ':' || c == '*' ||
                c == '?' || c == '"' || c == '<' || c == '>' || c == '|') return false;
        }
        if (i == key.size() || key[i] == '/') {
            auto component = key.substr(start, i-start);
            if (component.back() == '.' || component.back() == ' ') return false;
            auto base = component.substr(0, component.find('.'));
            auto upper = [](char c) { return c >= 'a' && c <= 'z' ? char(c-'a'+'A') : c; };
            if (!base.empty() && base.back()==' ') return false;
            for (auto reserved : {std::string_view("CONIN$"),std::string_view("CONOUT$"),std::string_view("CLOCK$")}) {
                if (base.size()!=reserved.size()) continue;
                bool same=true;for(size_t j=0;j<base.size();++j)if(upper(base[j])!=reserved[j]){same=false;break;}
                if(same)return false;
            }
            if (base.size() == 3) {
                const char a=upper(base[0]), b=upper(base[1]), c=upper(base[2]);
                if ((a=='C'&&b=='O'&&c=='N') || (a=='P'&&b=='R'&&c=='N') ||
                    (a=='A'&&b=='U'&&c=='X') || (a=='N'&&b=='U'&&c=='L')) return false;
            }
            if (base.size() == 4) {
                const char a=upper(base[0]), b=upper(base[1]), c=upper(base[2]), d=base[3];
                if (d>='0'&&d<='9'&&((a=='C'&&b=='O'&&c=='M') || (a=='L'&&b=='P'&&c=='T'))) return false;
            }
            start=i+1;
        }
    }
    return true;
}
inline bool canonical_relative(std::string_view key) {
#ifdef _WIN32
    return canonical_relative_windows(key);
#else
    return canonical_relative_posix(key);
#endif
}
inline constexpr unsigned platform =
#ifdef _WIN32
    2;
#else
    1;
#endif
}
