#include "Ast.h"
#include <iostream>
#include <stdexcept>
#include <type_traits>
using namespace nift::ast;
void require(bool ok,const char* msg){if(!ok)throw std::runtime_error(msg);}
int main(){
static_assert(!std::is_copy_constructible_v<Expr>, "unique-owner AST must not become copyable");
static_assert(std::is_move_constructible_v<Expr>);
static_assert(sizeof(Expr)==S0_BASE_SIZE);
static_assert(offsetof(Expr,span)==S0_BASE_SPAN && offsetof(Expr,op)==S0_BASE_OP);
for(auto s:{"+","-","*","/","%","==","!=","<","<=",">",">="}){
 auto p=parse_expression(std::string("left ")+s+" right");require(p.supported&&p.expr&&p.expr->kind==Kind::Binary,"parser Binary");
 auto code=p.expr->prepared_numeric_operator();require(code!=NumericBinaryOp::Unknown,"prepared code");
 Expr moved(std::move(*p.expr));require(moved.op==s&&moved.prepared_numeric_operator()==code,"moved code/spelling");
 // No production clone API exists. A field-copy reconstruction is guarded exactly as internal manual nodes are.
 Expr reconstructed;reconstructed.kind=Kind::Binary;reconstructed.op=moved.op;reconstructed.numeric_op=moved.numeric_op;
 require(reconstructed.prepared_numeric_operator()==code,"reconstructed code/spelling");
 moved.op="**";require(moved.prepared_numeric_operator()==NumericBinaryOp::Unknown,"stale unknown spelling");
 moved.op=(std::string(s)=="+"?"-":"+");require(moved.prepared_numeric_operator()==NumericBinaryOp::Unknown,"stale recognized spelling");
 Expr manual;manual.kind=Kind::Binary;manual.op=s;require(manual.prepared_numeric_operator()==NumericBinaryOp::Unknown,"manual initialized fallback");
 manual.op="unknown";manual.prepare_numeric_operator();require(manual.prepared_numeric_operator()==NumericBinaryOp::Unknown,"unknown preparation fallback");
}
auto folded=parse_expression("2 * (3 + 4)");require(folded.expr!=nullptr,"fold input");fold_constants(*folded.expr);require(folded.expr->kind==Kind::Literal&&folded.expr->literal.num==14,"fold exact result");require(folded.expr->op.empty()&&folded.expr->prepared_numeric_operator()==NumericBinaryOp::Unknown,"fold discarded spelling guarded");
std::cout<<"PASS layout, preparation, move/reconstruction, folding, manual, unknown and stale-spelling contracts\n";
}
