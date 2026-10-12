#pragma once
#include "Ast.h"
#include "SourceView.h"
#include <memory>
#include <optional>
#include <vector>

namespace nift::detail {
// Internal carrier only: source dispatch and body execution remain unchanged.
// A logical location owns a root SLOT, not a pointer into a vector. Its path
// must be resolved from that slot when used, including after root replacement.
template<class PathComponent>
struct EvaluatedOperand {
    using RootSlot = std::shared_ptr<std::shared_ptr<RuntimeValue>>;
    enum class Provenance { Untouched, Value, LocationCandidate, Location, ValueFromPath, Failed };
    Provenance provenance = Provenance::Untouched;
    std::optional<RuntimeValue> snapshot;
    RootSlot root;
    std::vector<PathComponent> path;
    struct ComponentSource {
        SourceView source;
        std::string token;
        bool quoted = false;
        bool member = false;
    };
    std::vector<ComponentSource> components;
    bool quoted_literal = false;
    bool spread_element = false;
    int binding_type = 0;
    bool mutable_binding = true;
    bool deep_readonly = false;
    SourceView source;
    ast::SourceSpan span{};
    // Optional owner for an expression that must outlive synchronous formation.
    std::shared_ptr<const ast::Expr> expression;
    RootSlot returned_root;
    std::vector<PathComponent> returned_path;
};

// Extract only the common structural walk. Caller adapters retain their
// historical lookup/sync, index conversion and diagnostic policies. Each Index
// is evaluated once per helper invocation; F1C deliberately does not share the
// result between old call sites yet. Location validity remains caller-owned.
template<class Operand, class ResolveBinding, class EvaluateIndex, class AppendIndex>
bool form_location_path(const ast::Expr& expression, Operand& operand,
                        ResolveBinding&& resolve_binding,
                        EvaluateIndex&& evaluate_index,
                        AppendIndex&& append_index) {
    auto walk = [&](auto&& self, const ast::Expr& node) -> bool {
        if(node.kind==ast::Kind::Binding) return resolve_binding(node,operand);
        if(node.kind==ast::Kind::Member) {
            if(!node.left||!self(self,*node.left))return false;
            using Component=typename decltype(operand.path)::value_type;
            operand.path.push_back(Component::member(node.name));
            return true;
        }
        if(node.kind==ast::Kind::Index) {
            if(!node.left||!node.right||!self(self,*node.left))return false;
            RuntimeValue index;
            if(!evaluate_index(*node.right,index))return false;
            return append_index(index,operand.path);
        }
        return false;
    };
    operand.span=expression.span;
    const bool ok=walk(walk,expression);
    operand.provenance=ok?Operand::Provenance::Location:Operand::Provenance::Failed;
    return ok;
}
} // namespace nift::detail
