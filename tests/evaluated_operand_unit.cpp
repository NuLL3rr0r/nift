#include "EvaluatedOperand.h"
#include <cassert>
#include <string>
struct Component {
    bool key=false;std::size_t index=0;std::string name;
    static Component at(std::size_t i){Component p;p.index=i;return p;}
    static Component member(std::string s){Component p;p.key=true;p.name=std::move(s);return p;}
};
using Operand=nift::detail::EvaluatedOperand<Component>;
int main(){
    auto root=std::make_shared<nift::RuntimeValue>(nift::RuntimeValue::make_array());
    root->array.push_back(nift::RuntimeValue::make_array());root->array[0].array.emplace_back(7);
    auto slot=std::make_shared<std::shared_ptr<nift::RuntimeValue>>(root);
    Operand retained;
    auto parsed=nift::ast::parse_expression("a[index()].member[other()]");assert(parsed.supported);
    retained.source=nift::detail::SourceView::identity("original.f","a[index()].member[other()]");
    retained.expression=std::shared_ptr<const nift::ast::Expr>(std::move(parsed.expr));
    int indices=0,bindings=0;
    const bool formed=nift::detail::form_location_path(*retained.expression,retained,
        [&](const nift::ast::Expr& node,Operand& out){assert(node.name=="a");++bindings;out.root=slot;out.binding_type=12;out.mutable_binding=false;out.deep_readonly=true;return true;},
        [&](const nift::ast::Expr& node,nift::RuntimeValue& value){++indices;value=nift::RuntimeValue(node.name=="index"?0:1);return true;},
        [&](const nift::RuntimeValue& value,std::vector<Component>& path){path.push_back(Component::at(static_cast<std::size_t>(value.num)));return true;});
    assert(formed&&indices==2&&bindings==1);assert(retained.path.size()==3);
    assert(retained.root==slot&&retained.path[0].index==0&&retained.path[1].name=="member"&&retained.path[2].index==1);
    assert(retained.binding_type==12&&!retained.mutable_binding&&retained.deep_readonly);
    auto copy=retained;retained.path.clear();assert(copy.path.size()==3&&copy.root==slot);
    // The root slot survives both reallocation and replacement of the root.
    for(int i=0;i<1000;++i)root->array.emplace_back(i);
    auto replacement=std::make_shared<nift::RuntimeValue>(nift::RuntimeValue::make_array());*slot=replacement;
    assert(*copy.root==replacement);root.reset();slot.reset();assert(copy.root&&*copy.root==replacement);
    auto origin=copy.source.locate(2);assert(origin.source=="original.f"&&origin.line==1&&origin.column==3);
    copy.snapshot=nift::RuntimeValue::make_array();copy.snapshot->array.emplace_back(3);auto value_copy=copy;value_copy.snapshot->array[0]=nift::RuntimeValue(4);assert(copy.snapshot->array[0].num==3);
    copy.returned_root=copy.root;copy.returned_path=copy.path;auto returned=copy;copy.returned_path.clear();assert(returned.returned_root==returned.root&&returned.returned_path.size()==3);
    Operand failed;int effects=0;
    assert(!nift::detail::form_location_path(*returned.expression,failed,
        [&](const nift::ast::Expr&,Operand& out){out.root=returned.root;return true;},
        [&](const nift::ast::Expr&,nift::RuntimeValue&){++effects;return false;},
        [&](const nift::RuntimeValue&,std::vector<Component>&){assert(false);return true;}));
    assert(effects==1&&failed.provenance==Operand::Provenance::Failed);
    // Each separately formed descriptor deliberately repeats its own indices.
    auto direct=nift::ast::parse_expression("a");Operand binding;
    assert(nift::detail::form_location_path(*direct.expr,binding,
        [&](const nift::ast::Expr&,Operand& out){out.root=returned.root;return true;},
        [&](const nift::ast::Expr&,nift::RuntimeValue&){assert(false);return false;},
        [&](const nift::RuntimeValue&,std::vector<Component>&){assert(false);return false;}));
    assert(binding.root==returned.root&&binding.path.empty());
}
