from pathlib import Path
import subprocess,shlex,shutil,sys,re
p=Path('/tmp/nift-sidecar-experiment/counters');r=Path('/home/nick/Repositories/nift/nift');shutil.copy2(r/'nift',p/'nift-e2')
(p/'Diag.h').write_text(r'''#pragma once
#include <chrono>
#include <map>
#include <mutex>
#include <fstream>
#include <cstdlib>
#include <filesystem>
namespace diag {
struct E {unsigned long long calls=0,bytes=0;double ms=0;std::map<std::string,unsigned long long> paths;};
struct Global {std::mutex m;std::map<std::string,E> d;~Global(){auto f=std::getenv("NIFT_DIAG_FILE");if(!f)return;std::ofstream o(f);o<<"metric,calls,unique,bytes,inclusive_ms\n";for(auto& x:d){o<<x.first<<","<<x.second.calls<<","<<x.second.paths.size()<<","<<x.second.bytes<<","<<x.second.ms<<"\n";}std::ofstream q(std::string(f)+".paths");for(auto& x:d)for(auto& y:x.second.paths)q<<x.first<<"\t"<<y.second<<"\t"<<y.first<<"\n";}};
inline Global& global(){static Global g;return g;}
struct Local {std::map<std::string,E>d;Local(){global();}~Local(){auto&g=global();std::lock_guard<std::mutex>l(g.m);for(auto&x:d){auto&e=g.d[x.first];e.calls+=x.second.calls;e.bytes+=x.second.bytes;e.ms+=x.second.ms;for(auto&y:x.second.paths)e.paths[y.first]+=y.second;}}};
inline Local& local(){thread_local Local l;return l;}
inline void hit(const char*n,const std::filesystem::path&p={},unsigned long long b=0){auto&e=local().d[n];e.calls++;e.bytes+=b;if(!p.empty() && !std::getenv("NIFT_DIAG_NO_PATHS"))e.paths[p.generic_string()]++;}
struct Scope{const char*n;std::chrono::steady_clock::time_point s;Scope(const char*v):n(v),s(std::chrono::steady_clock::now()){hit(n);}~Scope(){local().d[n].ms+=std::chrono::duration<double,std::milli>(std::chrono::steady_clock::now()-s).count();}};
}
''')
spec={
'FileSystem.cpp': [('DependencyStatus dependency_status(const fs::path& path) {','diag::Scope z("following_status_time");diag::hit("following_status",path);'),('bool path_exists(const fs::path& path) {','diag::hit("path_exists",path);'),('bool file_readable(const fs::path& path) {','diag::Scope z("readable_time");diag::hit("file_readable",path);'),('std::optional<std::string> read_file_checked(const fs::path& path) {','diag::Scope z("checked_read_time");diag::hit("checked_read",path);'),('const std::streamoff size = file.tellg();','if(size>0)diag::hit("read_bytes",path,size);')],
'JsonFile.cpp':[('bool load_json_file(const std::filesystem::path& path, json::Document& document, std::string& error) {','diag::Scope z("json_load_time");diag::Scope role(path.extension()==".json" && path.filename().string().find(".info.json")!=std::string::npos ? "info_json_time" : path.filename().string().find(".deps.json")!=std::string::npos ? "deps_json_time" : "other_json_time");diag::hit("json_load",path);')],
'ProjectRead.cpp':[('std::string relative_of(const fs::path& root, const fs::path& path) {','diag::Scope z("relative_time");diag::hit("relative",path);')],
'ProjectInfo.cpp':[('std::vector<std::string> ProjectInfo::build_reasons(const TrackedInfo& info) const {','diag::Scope z("consumer_time");std::set<std::string> diag_saved;'),('bool ProjectInfo::load_user_dependencies(const TrackedInfo& info, std::set<std::string>& dependencies, BuildError* build_error, SidecarObservation* observation) const {','diag::Scope z("sidecar_time");'),('const fs::file_status status = fs::symlink_status(normalized, error);','diag::hit("nofollow_safety",normalized);'),('for (const auto& value : document["dependencies"].array) {','diag::Scope saved_scope("declaration_validation_time");'),('const fs::path dependency = (root / value.string).lexically_normal();','diag::hit("saved_edges",dependency);diag_saved.insert(value.string);'),('for (const auto& dependency_name : user_dependencies) {','diag::Scope second_scope("second_comparison_time");'),('const std::string reason = "dependency changed: " + dependency_name;','diag::hit("current_edges",root/dependency_name);if(diag_saved.count(dependency_name))diag::hit("overlap_edges",root/dependency_name);'),('const fs::path dependency = root / dependency_name;','if(diag_saved.count(dependency_name))diag::hit("clean_second_status",dependency);'),('bool ProjectInfo::dependency_changed(const fs::path& dependency, const filesystem::DependencyStatus& status, const filesystem::DependencyStatus& page_info_status, const json::Document& snapshots, const std::string& name) const {','diag::hit("dependency_comparison",dependency);')]
}
lines=subprocess.check_output(['make','-n','-W','src/ProjectInfo.cpp','all'],cwd=r,text=True).splitlines();base=shlex.split(next(x for x in lines if '-c src/ProjectInfo.cpp ' in x));link=shlex.split(next(x for x in reversed(lines) if x.endswith(' -o nift')))
for name,anchors in spec.items():
 s=(Path('/tmp/nift-sidecar-experiment')/name).read_text() if name=='ProjectInfo.cpp' else (r/'src'/name).read_text()
 for anchor,inject in anchors:
  assert anchor in s,(name,anchor);s=s.replace(anchor,anchor+'\n'+inject,1)
 
 if name=='ProjectInfo.cpp':
  s=s.replace('const bool parsed=readable&&nift_json::parse(parsed_bytes,document,error);', 'if(readable){diag::hit("sidecar_decode",path);diag::hit("json_parse_bytes",path,parsed_bytes.size());} const bool parsed=readable&&nift_json::parse(parsed_bytes,document,error);')
  s=s.replace('if(saved_edges_clean&&cached_user_dependencies_match(info,document))return reasons;', 'if(saved_edges_clean&&cached_user_dependencies_match(info,document)){diag::hit("sidecar_reuse");return reasons;}')
  anchor='    const fs::path normalized_root = root.lexically_normal();\n    for (const auto& value : document["dependencies"].array) {'
  assert anchor in s;s=s.replace(anchor,anchor+'\n diag::Scope saved_scope("saved_comparison_time");',1)
  s=s.replace('const fs::file_status status = fs::symlink_status(normalized, error);','const fs::file_status status = [&]{diag::Scope scope("nofollow_time");return fs::symlink_status(normalized,error);}();')
  s=s.replace('std::lock_guard<std::mutex> lock(metadata_path_mutex_);','const auto diag_wait=std::chrono::steady_clock::now(); std::lock_guard<std::mutex> lock(metadata_path_mutex_); diag::hit("metadata_lock_wait_ns",{},std::chrono::duration_cast<std::chrono::nanoseconds>(std::chrono::steady_clock::now()-diag_wait).count());')
 if name=='JsonFile.cpp':
  s=s.replace('return nift_json::parse(filesystem::read_file(path), document, error);','const auto diag_bytes=filesystem::read_file(path); diag::hit("json_parse_bytes",path,diag_bytes.size()); diag::Scope parse_scope("json_parse_time"); return nift_json::parse(diag_bytes, document, error);')

 if '--timing-only' in sys.argv:
  s=s.replace('std::set<std::string> diag_saved;','').replace('diag_saved.insert(value.string);','')
  s=re.sub(r'if\(diag_saved.count\(dependency_name\)\)diag::hit\([^;]+;','',s)
  s=re.sub(r'diag::hit\(\"(?!metadata_lock_wait_ns)[^;]+;','',s)
 (p/name).write_text('#include "Diag.h"\n'+s)
 cmd=[str(p/name) if x=='src/ProjectInfo.cpp' else str(p/Path(name).with_suffix('.o')) if x=='src/ProjectInfo.o' else x for x in base];subprocess.run(cmd,cwd=r,check=True)
for name in spec:link=[str(p/Path(name).with_suffix('.o')) if x=='src/'+str(Path(name).with_suffix('.o')) else x for x in link]
link=[str(p/('nift-timing' if '--timing-only' in sys.argv else 'nift-counters')) if x=='nift' else x for x in link];subprocess.run(link,cwd=r,check=True)
