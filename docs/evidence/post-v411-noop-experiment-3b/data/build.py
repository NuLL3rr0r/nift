from pathlib import Path
import subprocess,shlex,shutil
p=Path('/tmp/nift-sidecar-experiment');r=Path('/home/nick/Repositories/nift/nift')
for h in (r/'src').glob('*.h'):shutil.copy2(h,p/h.name)
if not (p.parent/'jsonic').exists():(p.parent/'jsonic').symlink_to(r/'jsonic')
h=(r/'src/ProjectInfo.h').read_text();h=h.replace('    bool load_user_dependencies(', '    struct SidecarObservation;\n    bool cached_user_dependencies_match(const TrackedInfo& info, const json::Document& document) const;\n    bool load_user_dependencies(',1).replace('BuildError* error = nullptr) const;', 'BuildError* error = nullptr, SidecarObservation* observation = nullptr) const;',1).replace('const std::map<std::string,std::string>& snapshots) const;', 'const std::map<std::string,std::string>& snapshots, const SidecarObservation* observation = nullptr) const;',1);(p/'ProjectInfo.h').write_text(h)
s=(r/'src/ProjectInfo.cpp').read_text()
a='bool ProjectInfo::load_user_dependencies(const TrackedInfo& info, std::set<std::string>& dependencies, BuildError* build_error) const {'
helpers=r'''
namespace {
const char* sidecar_platform() {
#ifdef _WIN32
    return "windows-lexical-v1";
#else
    return "posix-lexical-v1";
#endif
}
std::string sidecar_hex(const std::string& bytes) {
    static constexpr char digits[]="0123456789abcdef";
    std::string result;result.reserve(bytes.size()*2);
    for(unsigned char c:bytes){result.push_back(digits[c>>4]);result.push_back(digits[c&15]);}
    return result;
}
bool sidecar_unhex(const std::string& hex, std::string& bytes) {
    if(hex.size()%2)return false;
    auto digit=[](char c)->int {if(c>='0'&&c<='9')return c-'0';if(c>='a'&&c<='f')return c-'a'+10;return -1;};
    bytes.clear();bytes.reserve(hex.size()/2);
    for(std::size_t i=0;i<hex.size();i+=2){int a=digit(hex[i]),b=digit(hex[i+1]);if(a<0||b<0)return false;bytes.push_back(static_cast<char>((a<<4)|b));}
    return true;
}
}
struct ProjectInfo::SidecarObservation {
    bool present=false;
    std::string bytes;
    std::set<std::string> declarations;
};
bool ProjectInfo::cached_user_dependencies_match(const TrackedInfo& info, const json::Document& document) const {
    if(!document.has("sidecar-state"))return false;
    const auto& state=document["sidecar-state"];
    if(!state.is_object()||!state.has("version")||!state["version"].is_number()||state["version"].num!=1||
       !state.has("platform")||!state["platform"].is_string()||state["platform"].string!=sidecar_platform()||
       !state.has("present")||!state["present"].is_bool()||!state.has("bytes-hex")||!state["bytes-hex"].is_string()||
       !state.has("declaration-indices")||!state["declaration-indices"].is_array())return false;
    const auto& edges=document["dependencies"].array;
    std::size_t previous=0;bool first=true;
    for(const auto& value:state["declaration-indices"].array){
        if(!value.is_number()||!std::isfinite(value.num)||value.num<0||std::floor(value.num)!=value.num||value.num>=edges.size())return false;
        const auto index=static_cast<std::size_t>(value.num);
        if(!first&&index<=previous)return false;
        first=false;previous=index;
        if(!edges[index].is_string()||edges[index].string==".nift/project.fingerprint"||edges[index].string==".nift/hierarchy.fingerprint")return false;
    }
    fs::path path=content_path(info);path.replace_extension(".deps.json");
    if(!state["present"].boolean)
        return state["bytes-hex"].string.empty()&&state["declaration-indices"].array.empty()&&!filesystem::path_exists(path);
    // Do not replace the existing readable/type/error pipeline with a new reader.
    if(!filesystem::path_exists(path)||!filesystem::file_readable(path))return false;
    const auto current=filesystem::read_file_checked(path);if(!current)return false;
    std::string previous_bytes;if(!sidecar_unhex(state["bytes-hex"].string,previous_bytes)||previous_bytes!=*current)return false;
    // A present certificate must include the sidecar's exact saved dependency edge.
    const auto name=relative(path);
    return std::any_of(edges.begin(),edges.end(),[&](const auto& edge){return edge.is_string()&&edge.string==name;});
}
'''
assert a in s;s=s.replace(a,helpers+'\nbool ProjectInfo::load_user_dependencies(const TrackedInfo& info, std::set<std::string>& dependencies, BuildError* build_error, SidecarObservation* observation) const {',1)
s=s.replace('    fs::path path = content_path(info);\n    path.replace_extension(".deps.json");','    if(observation)*observation=SidecarObservation{};\n    fs::path path = content_path(info);\n    path.replace_extension(".deps.json");',1)
a='    if (!load_json_file(path, document, error) || !document.is_object()';b='''    std::string parsed_bytes;
    const bool exists=filesystem::path_exists(path);
    const bool readable=exists&&filesystem::file_readable(path);
    if(!exists)error="file does not exist";else if(!readable)error="file is not readable";
    if(readable)parsed_bytes=filesystem::read_file(path);
    const bool parsed=readable&&nift_json::parse(parsed_bytes,document,error);
    if (!parsed || !document.is_object()''';assert a in s;s=s.replace(a,b,1)
s=s.replace('    dependencies.insert(relative(path));','    if(observation){observation->present=true;observation->bytes=parsed_bytes;}\n    dependencies.insert(relative(path));',1)
a='        dependencies.insert(relative((root / dependency_name).lexically_normal()));';assert a in s;s=s.replace(a,'        const auto normalized_name=relative((root / dependency_name).lexically_normal());\n        dependencies.insert(normalized_name);\n        if(observation)observation->declarations.insert(normalized_name);',1)
# Conservative reuse: every saved edge must have completed an ordinary clean check.
a=s.index('    const fs::path normalized_root = root.lexically_normal();',s.index('std::vector<std::string> ProjectInfo::build_reasons'));b=s.index('    for (const auto& value : document["reqs"].array)',a);part=s[a:b]
part=part.replace('    const fs::path normalized_root', '    bool saved_edges_clean=true;\n    const fs::path normalized_root',1)
part=part.replace('            reasons.push_back("page build metadata has an invalid dependency");','            saved_edges_clean=false;\n            reasons.push_back("page build metadata has an invalid dependency");')
for role in ['project','hierarchy']:part=part.replace('        if (value.string == ".nift/'+role+'.fingerprint") {','        if (value.string == ".nift/'+role+'.fingerprint") {\n            saved_edges_clean=false;')
part=part.replace('        if (!status.exists || status.error)\n            reasons.push_back("dependency removed: " + value.string);\n        else if (dependency_changed(dependency, status, page_info_status, document["dependency-hashes"], value.string))\n            reasons.push_back("dependency changed: " + value.string);','''        if (!status.exists || status.error) {
            saved_edges_clean=false;reasons.push_back("dependency removed: " + value.string);
        } else if (dependency_changed(dependency, status, page_info_status, document["dependency-hashes"], value.string)) {
            saved_edges_clean=false;reasons.push_back("dependency changed: " + value.string);
        }''');s=s[:a]+part+s[b:]
a='    std::set<std::string> user_dependencies;';s=s.replace(a,'    if(saved_edges_clean&&cached_user_dependencies_match(info,document))return reasons;\n'+a,1)
s=s.replace('const std::map<std::string,std::string>& snapshots) const {','const std::map<std::string,std::string>& snapshots, const SidecarObservation* observation) const {',1)
a='    output += "\\n  }\\n}\\n";';assert a in s
b=r'''    output += "\n  }";
    if(observation){
        output += ",\n  \"sidecar-state\": {\"version\":1,\"platform\":\"";
        output += sidecar_platform();
        output += "\",\"present\":";output += observation->present?"true":"false";
        output += ",\"bytes-hex\":\"";output += sidecar_hex(observation->bytes);
        output += "\",\"declaration-indices\":[";
        std::size_t position=0;bool first=true;
        for(const auto& dependency:dependencies){
            if(observation->declarations.count(dependency)){
                if(!first)output.push_back(',');
                first=false;output+=std::to_string(position);
            }
            ++position;
        }
        output += "]}";
    }
    output += "\n}\n";'''
s=s.replace(a,b,1)
a='    if (!load_user_dependencies(info, result.dependencies, &result.error))';assert a in s;s=s.replace(a,'    SidecarObservation authoritative_sidecar;\n    if (!load_user_dependencies(info, result.dependencies, &result.error, &authoritative_sidecar))',1)
a='    if (!write_page_info(info, result.dependencies, result.reqs, new_pagination_pages, snapshots)) {';assert a in s
b='''    fs::path sidecar_path=content_path(info);sidecar_path.replace_extension(".deps.json");
    bool certificate_valid=false;
    if(authoritative_sidecar.present){
        const auto current=filesystem::read_file_checked(sidecar_path);
        certificate_valid=current&&*current==authoritative_sidecar.bytes;
    }else certificate_valid=!filesystem::path_exists(sidecar_path);
    // Later hook changes suppress only the new certificate, preserving E2 behavior.
    if (!write_page_info(info, result.dependencies, result.reqs, new_pagination_pages, snapshots, certificate_valid?&authoritative_sidecar:nullptr)) {'''
s=s.replace(a,b,1);(p/'ProjectInfo.cpp').write_text(s)
lines=subprocess.check_output(['make','-n','-W','src/ProjectInfo.cpp','all'],cwd=r,text=True).splitlines();base=shlex.split(next(x for x in lines if '-c src/ProjectInfo.cpp ' in x));link=shlex.split(next(x for x in reversed(lines) if x.endswith(' -o nift')))
base=[str(p/'ProjectInfo.cpp') if x=='src/ProjectInfo.cpp' else str(p/'ProjectInfo.o') if x=='src/ProjectInfo.o' else x for x in base];subprocess.run(base,cwd=r,check=True)
link=[str(p/'ProjectInfo.o') if x=='src/ProjectInfo.o' else str(p/'nift-e3b') if x=='nift' else x for x in link];subprocess.run(link,cwd=r,check=True);shutil.copy2(r/'nift',p/'nift-e2')
