#include "Ast.h"
#include <iostream>
#include <iomanip>
#include <cstring>
#include <limits>
#include <cmath>
using namespace nift;using namespace nift::ast;
std::string repr(const RuntimeValue& v){std::uint64_t bits;std::memcpy(&bits,&v.num,8);return std::to_string((int)v.type)+":"+std::to_string(bits)+":"+v.string+":"+std::to_string(v.boolean)+":"+std::to_string(v.array.size())+":"+std::to_string(v.object.size());}
std::unique_ptr<Expr> binding(std::string name){auto e=std::make_unique<Expr>();e->kind=Kind::Binding;e->name=name;e->span={name=="left"?0u:7u,name=="left"?4u:12u};return e;}
int main(){std::cout<<"SIZE "<<sizeof(Expr)<<" "<<offsetof(Expr,span)<<" "<<offsetof(Expr,op)<<"\n";
std::vector<RuntimeValue> vs={RuntimeValue(0.0),RuntimeValue(-0.0),RuntimeValue(1.0),RuntimeValue(-1.0),RuntimeValue(3.5),RuntimeValue(-2.25),RuntimeValue(9007199254740992.0),RuntimeValue(std::numeric_limits<double>::max()),RuntimeValue(-std::numeric_limits<double>::max()),RuntimeValue(std::numeric_limits<double>::denorm_min()),RuntimeValue(std::numeric_limits<double>::quiet_NaN()),RuntimeValue(std::numeric_limits<double>::infinity()),RuntimeValue(-std::numeric_limits<double>::infinity()),RuntimeValue("text"),RuntimeValue(true),RuntimeValue(),RuntimeValue::make_array(),RuntimeValue::make_object(),RuntimeValue(RuntimeBytes{1,2})};
for(auto s:{"9007199254740993","9007199254740992","1.25","1e309","-0","-9223372036854775809"}){RuntimeValue v(std::strtod(s,nullptr));v.type=RuntimeType::StrNumber;v.string=s;vs.push_back(std::move(v));}
std::vector<std::string> ops={"+","-","*","/","%","==","!=","<","<=",">",">=","**","","<<","&&"};
for(std::size_t a=0;a<vs.size();++a)for(std::size_t b=0;b<vs.size();++b)for(auto& op:ops)for(int mode=0;mode<4;++mode){
std::unique_ptr<Expr> e;if(mode==0||mode==1){auto r=parse_expression("left "+op+" right");e=std::move(r.expr);if(!e){std::cout<<a<<","<<b<<","<<op<<","<<mode<<":UNSUPPORTED:"<<r.error<<"\n";continue;}
#ifdef S0
if(mode==1)e->numeric_op=NumericBinaryOp::Unknown;
#endif
}else if(mode==2){e=parse_expression("left + right").expr;e->op=op;}else{e=std::make_unique<Expr>();e->kind=Kind::Binary;e->op=op;e->span={0,12};e->left=binding("left");e->right=binding("right");}
Context c;std::string trace,error;SourceSpan failure{999,999};c.resolve=[&](const std::string& name,RuntimeValue& out,std::string& err){trace+=name+";";if(name=="left")out=vs[a];else if(name=="right")out=vs[b];else{err="missing: "+name;return false;}return true;};c.failure_origin=[&](SourceSpan s){failure=s;};c.render=[](const RuntimeValue& v){return v.dump();};RuntimeValue out;bool ok=evaluate(*e,c,out,error);
std::cout<<a<<","<<b<<","<<op<<","<<mode<<":"<<ok<<":"<<repr(out)<<":"<<error<<":"<<trace<<":"<<failure.begin<<","<<failure.end<<"\n";
}
for(auto src:{"left * (right + left)","left / (right - right)","left && right","left || right","left ?? right","left + absent","absent * right","left < (right % left)"})for(std::size_t a=0;a<vs.size();++a){auto r=parse_expression(src);if(!r.supported){std::cout<<"N:"<<src<<":"<<r.error<<"\n";continue;}Context c;std::string error,trace;SourceSpan fail{999,999};c.resolve=[&](const std::string& n,RuntimeValue& v,std::string& err){trace+=n+";";if(n=="left")v=vs[a];else if(n=="right")v=RuntimeValue(2.0);else{err="missing binding";return false;}return true;};c.failure_origin=[&](SourceSpan s){fail=s;};c.render=[](const RuntimeValue& v){return v.dump();};RuntimeValue out;bool ok=evaluate(*r.expr,c,out,error);std::cout<<"N:"<<src<<":"<<a<<":"<<ok<<":"<<repr(out)<<":"<<error<<":"<<trace<<":"<<fail.begin<<","<<fail.end<<"\n";}
}
