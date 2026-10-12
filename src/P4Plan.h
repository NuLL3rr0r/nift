#pragma once
#include "Ast.h"
#include <unordered_map>
#include <unordered_set>
namespace nift::p4 {
using ast::Expr;using ast::Stmt;using ast::Kind;using ast::StmtKind;
using Body=std::vector<std::unique_ptr<Stmt>>;
inline bool binding(const Expr*e,const std::string&n){return e&&e->kind==Kind::Binding&&e->name==n;}
inline bool plain_string(const Expr*e){
 if(!e||e->kind!=Kind::Literal||!e->literal.is_string())return false;
 // Canonical source-literal semantics are not inferred from an AST's decoded
 // payload when its spelling contains escapes or control bytes.
 for(unsigned char c:e->literal.string)if(c<32||c>126||c=='\\'||c=='"')return false;
 return e->literal_token=="\""+e->literal.string+"\"";
}
inline bool text(const Expr*e,const std::string&s){return plain_string(e)&&e->literal.string==s;}
inline bool join(const Expr*e,const std::string&a,const std::string&b){return e&&e->kind==Kind::Binary&&e->op=="+"&&binding(e->right.get(),b)&&e->left&&e->left->kind==Kind::Binary&&e->left->op=="+"&&binding(e->left->left.get(),a)&&text(e->left->right.get(),"/");}
inline bool call(const Expr*e,const std::string&n,std::size_t argc){return e&&e->kind==Kind::Call&&e->name==n&&!e->left&&e->items.size()==argc;}
inline bool empty(const Stmt&s){return s.kind==StmtKind::Declaration&&s.expr&&s.expr->kind==Kind::Array&&s.expr->items.empty();}
inline bool push(const Stmt&s,const std::string&n){return s.kind==StmtKind::Expression&&s.name==n&&s.op=="push"&&s.call_args.size()==1;}
struct Walker {const Expr* ls=nullptr;const Expr* predicate=nullptr;const Expr* recurse=nullptr;};
inline bool walker(const Body&body,const std::vector<std::string>&params,const std::string&self,Walker&plan){
 if(params.size()!=2||body.size()!=3||!empty(*body[0])||body[1]->kind!=StmtKind::For||body[2]->kind!=StmtKind::Return)return false;
 const auto&f=*body[1];const auto&o=body[0]->name;
 if(!binding(body[2]->expr.get(),o)||!call(f.iterable.get(),"ls",1)||!join(f.iterable->items[0].get(),params[0],params[1])||f.body.size()!=5||f.bindings.size()>1)return false;
 const auto&r=*f.body[0];const auto&cond=*f.body[1];const auto&d=*f.body[2];const auto&append=*f.body[3];const auto&rec=*f.body[4];
 if(r.kind!=StmtKind::Declaration||!binding(r.expr.get(),f.name)||cond.kind!=StmtKind::If||!cond.condition||cond.condition->kind!=Kind::Binary||cond.condition->op!="!="||!binding(cond.condition->left.get(),params[1])||!text(cond.condition->right.get(),"")||cond.body.size()!=1||!cond.else_body.empty())return false;
 const auto&assign=*cond.body[0];if(assign.kind!=StmtKind::Assignment||assign.name!=r.name||assign.target||!join(assign.expr.get(),params[1],f.name))return false;
 if(d.kind!=StmtKind::Declaration||!call(d.expr.get(),"is_dir",1)||!join(d.expr->items[0].get(),params[0],r.name)||!push(append,o))return false;
 const auto&arr=*append.call_args[0];if(arr.kind!=Kind::Array||arr.items.size()!=2||!binding(arr.items[0].get(),r.name)||!binding(arr.items[1].get(),d.name))return false;
 if(rec.kind!=StmtKind::If||!binding(rec.condition.get(),d.name)||rec.body.size()!=1||!rec.else_body.empty())return false;
 const auto&inner=*rec.body[0];if(inner.kind!=StmtKind::For||inner.bindings.size()>1||inner.body.size()!=1||!call(inner.iterable.get(),self,2)||!binding(inner.iterable->items[0].get(),params[0])||!binding(inner.iterable->items[1].get(),r.name)||!push(*inner.body[0],o)||!binding(inner.body[0]->call_args[0].get(),inner.name))return false;
 std::unordered_set<std::string> names{params[0],params[1],o,f.name,r.name,d.name,inner.name,self};if(names.size()!=8||names.count("loop"))return false;
 plan={f.iterable.get(),d.expr.get(),inner.iterable.get()};return true;
}
inline std::optional<bool> known(const Expr*e,const std::string&name,const std::string&value){
 if(!e)return {};
 if(e->kind==Kind::Literal&&e->literal.is_bool())return e->literal.boolean;
 if(e->kind==Kind::Binary&&(e->op=="=="||e->op=="!=")){
  const Expr* literal=nullptr;if(binding(e->left.get(),name))literal=e->right.get();else if(binding(e->right.get(),name))literal=e->left.get();
  if(plain_string(literal)){bool equal=literal->literal.string==value;return e->op=="=="?equal:!equal;}
 }
 if(e->kind==Kind::Logical){auto left=known(e->left.get(),name,value);if(!left)return {};if(e->op=="&&"&&!*left)return false;if(e->op=="||"&&*left)return true;return known(e->right.get(),name,value);}
 return {};
}
struct Consumer {std::string walker;std::unordered_map<const Stmt*,bool> conditions;};
// Bounded proof for a private rows/entries consumer. No calls or assignments to
// captures are admitted; mode facts apply only during this invocation.
inline bool consumer(const Body&body,const std::vector<std::string>&params,const std::string&mode,Consumer&plan){
 if(params.size()!=5||body.size()<5||!empty(*body[0])||!empty(*body[1])||body[2]->kind!=StmtKind::Declaration||!body[2]->expr||!call(body[2]->expr.get(),body[2]->expr->name,2)||!binding(body[2]->expr->items[0].get(),params[1])||!text(body[2]->expr->items[1].get(),"")||body.back()->kind!=StmtKind::Return||!binding(body.back()->expr.get(),body[0]->name))return false;
 plan.walker=body[2]->expr->name;
 std::unordered_set<std::string> locals(params.begin(),params.end());if(locals.size()!=5||locals.count("loop"))return false;
 std::function<bool(const Expr*)> pure=[&](const Expr*e){if(!e)return false;switch(e->kind){case Kind::Literal:return !e->literal.is_timer();case Kind::Binding:return e->name!="loop"&&locals.count(e->name);case Kind::Array:for(const auto&i:e->items)if(!pure(i.get()))return false;return true;case Kind::Unary:return pure(e->right?e->right.get():e->left.get());case Kind::Binary:case Kind::Logical:case Kind::Index:return pure(e->left.get())&&pure(e->right.get());case Kind::Member:return e->name=="size"&&call(e->left.get(),"stat",1)&&pure(e->left->items[0].get());default:return false;}};
 bool saw_loop=false;
 std::function<bool(const Body&)> scan=[&](const Body&items){for(const auto&sp:items){const auto&s=*sp;if(s.kind==StmtKind::If){auto v=known(s.condition.get(),params[0],mode);if(v){plan.conditions[&s]=*v;if(!scan(*v?s.body:s.else_body))return false;}else if(!pure(s.condition.get())||!scan(s.body)||!scan(s.else_body))return false;}
 else if(s.kind==StmtKind::Declaration){if(&s!=body[2].get()&&!pure(s.expr.get()))return false;if(!locals.insert(s.name).second||s.name=="loop")return false;}
 else if(s.kind==StmtKind::For){if(saw_loop||!binding(s.iterable.get(),body[2]->name)||s.bindings.size()>1||!locals.insert(s.name).second)return false;saw_loop=true;if(!scan(s.body))return false;}
 else if(s.kind==StmtKind::Expression){if(!push(s,body[0]->name)||!pure(s.call_args[0].get()))return false;}
 else if(s.kind==StmtKind::Continue||s.kind==StmtKind::Break){break;}
 else if(s.kind==StmtKind::Return){if(!pure(s.expr.get()))return false;break;}
 else return false;}
 return true;};
 return scan(body)&&saw_loop;
}
}
